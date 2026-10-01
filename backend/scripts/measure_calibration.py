"""Measure enrichment-score calibration under the rewritten classifier prompt (Task 012).

Answers one question with numbers: does `prompts/classify_item.md` still score
`strategic_potential` as a near-copy of `relevance` (D-018: r = 0.842 across 246 items), or is the
`horizon_signal` quadrant now reachable?

What it does
------------
Re-runs the **classify prompt only** over a held-out sample of already-enriched Events, and
compares the new scores with the ones stored in SQLite. It is **read-only**: the corpus DB is
opened with `mode=ro` and nothing is written back. The summariser / weak-signal / graph prompts are
not run — they do not produce scores, and skipping them cuts the sample's cost by ~4x.

Template loading and the user-message block come from `app.enrichment.prompts`, i.e. the same code
path the enricher uses. Only the provider call is made directly, so per-call token usage (and
therefore cost) can be recorded.

Usage (repo root, PYTHONPATH=backend per D-006)::

    PYTHONPATH=backend python backend/scripts/measure_calibration.py --dry-run
    PYTHONPATH=backend python backend/scripts/measure_calibration.py --out docs/m8-calibration.json

COST GATE (Task 012): this is billable. The default sample is 45 items — one LLM call each. Do
NOT point it at the full corpus without a cost decision from Christo.
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.enrichment import prompts
from app.enrichment.parse import parse_classify
from app.scoring.priority import compute_priority_class

# Anthropic list price for the configured model, USD per million tokens. Recorded so the run's
# cost is reproducible from its own output; update if the model or pricing changes.
PRICE_USD_PER_MTOK = {"claude-opus-4-8": (5.00, 25.00)}

# Held-out sample, stratified over the *existing* relevance distribution. Deliberately overweights
# the top of that distribution: the acceptance criteria require relevance and actionability to
# reach >= 4 somewhere, and a flat random draw from a corpus whose mean relevance is 1.2 would
# rarely include a candidate. Widening the relevance range can only make r *harder* to drop, so
# this is the conservative choice for the r < 0.5 criterion.
STRATA = {4: 1, 3: 11, 2: 10, 1: 12, 0: 11}
SEED = 12  # task 012


@dataclass
class Item:
    """One sampled Event: its stored scores plus the facts the classifier prompt needs."""

    event_id: int
    enriched_id: int
    title: str
    source_name: str
    url: str
    published_at: datetime | None
    content: str
    old: dict[str, int]
    new: dict[str, int] | None = None
    method: str = "llm"
    errors: list[str] = field(default_factory=list)


def _as_datetime(value: str | None) -> datetime | None:
    """SQLite hands back the timestamp as text; the prompt renderer wants a datetime."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def load_sample(db_path: Path, strata: dict[int, int], seed: int) -> list[Item]:
    """Read a deterministic stratified sample of LLM-enriched Events. Read-only."""
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT e.id AS enriched_id, e.event_id, e.relevance, e.novelty, e.actionability,
               e.strategic_potential, e.hype,
               r.title, r.source_name, r.url, r.published_at, r.summary
        FROM enriched_item e
        JOIN raw_item r ON r.id = e.raw_item_id
        WHERE e.method = 'llm'
        ORDER BY e.id
        """
    ).fetchall()
    conn.close()

    rng = random.Random(seed)
    picked: list[sqlite3.Row] = []
    for relevance, want in sorted(strata.items(), reverse=True):
        bucket = [r for r in rows if r["relevance"] == relevance]
        picked.extend(bucket if len(bucket) <= want else rng.sample(bucket, want))

    picked.sort(key=lambda r: r["enriched_id"])
    return [
        Item(
            event_id=r["event_id"],
            enriched_id=r["enriched_id"],
            title=r["title"],
            source_name=r["source_name"],
            url=r["url"],
            published_at=_as_datetime(r["published_at"]),
            content=r["summary"] or "",
            old={
                "relevance": r["relevance"],
                "novelty": r["novelty"],
                "actionability": r["actionability"],
                "strategic_potential": r["strategic_potential"],
                "hype": r["hype"],
            },
        )
        for r in picked
    ]


class MeteredAnthropic:
    """The production provider plus token accounting (the app's provider returns text only)."""

    def __init__(self, model: str, api_key: str, max_tokens: int) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def complete(self, *, system: str, user: str) -> str:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": user}],
        )
        self.calls += 1
        self.input_tokens += resp.usage.input_tokens
        self.output_tokens += resp.usage.output_tokens
        return "".join(b.text for b in resp.content if b.type == "text")

    def cost_usd(self) -> float | None:
        price = PRICE_USD_PER_MTOK.get(self.model)
        if price is None:
            return None
        in_rate, out_rate = price
        return self.input_tokens / 1e6 * in_rate + self.output_tokens / 1e6 * out_rate


def classify(provider: MeteredAnthropic, item: Item, user_context: str) -> dict[str, int]:
    """Run the classify prompt for one item. One retry, mirroring the enricher (D-009)."""
    system = prompts.load_template(prompts.CLASSIFY)
    user = prompts.render_item_inputs(
        title=item.title,
        source_name=item.source_name,
        source_url=item.url,
        published_at=item.published_at,
        content=item.content,
        user_context=user_context,
    )

    last: Exception | None = None
    for _ in range(2):
        try:
            scores = parse_classify(provider.complete(system=system, user=user)).scores
            return scores.model_dump()
        except Exception as exc:  # noqa: BLE001 - fail-safe per item, same as the enricher
            last = exc
            item.errors.append(str(exc)[:200])
    raise RuntimeError(f"classify failed twice for event {item.event_id}: {last}")


def pearson(xs: list[int], ys: list[int]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** 0.5
    return None if den == 0 else cov / den


def summarise(items: list[Item], which: str) -> dict:
    """Per-axis min/max/mean, r(relevance, strategic_potential), and priority-class counts."""
    scored = [i for i in items if getattr(i, which)]
    axes = ("relevance", "novelty", "actionability", "strategic_potential", "hype")
    per_axis = {}
    for axis in axes:
        vals = [getattr(i, which)[axis] for i in scored]
        per_axis[axis] = {
            "min": min(vals), "max": max(vals),
            "mean": round(sum(vals) / len(vals), 3),
            "dist": {v: vals.count(v) for v in sorted(set(vals))},
        }

    rel = [getattr(i, which)["relevance"] for i in scored]
    sp = [getattr(i, which)["strategic_potential"] for i in scored]
    classes = [compute_priority_class(r, s) for r, s in zip(rel, sp)]

    return {
        "n": len(scored),
        "r_relevance_strategic_potential": (
            None if pearson(rel, sp) is None else round(pearson(rel, sp), 3)
        ),
        "per_axis": per_axis,
        "priority_classes": {c: classes.count(c) for c in sorted(set(classes))},
        "horizon_signal_n": classes.count("horizon_signal"),
        "quadrant_rel_le2_and_sp_ge4": sum(1 for r, s in zip(rel, sp) if r <= 2 and s >= 4),
        "relevance_ge4_n": sum(1 for v in rel if v >= 4),
        "actionability_ge4_n": sum(
            1 for i in scored if getattr(i, which)["actionability"] >= 4
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="data/dev_corpus.db", type=Path)
    ap.add_argument("--out", default="docs/m8-calibration.json", type=Path)
    ap.add_argument("--limit", type=int, default=None, help="cap the sample (cost gate)")
    ap.add_argument("--dry-run", action="store_true", help="show the sample, spend nothing")
    args = ap.parse_args()

    items = load_sample(args.db, STRATA, SEED)
    if args.limit:
        items = items[: args.limit]
    print(f"sample: {len(items)} items from {args.db} (seed={SEED}, strata={STRATA})")

    if args.dry_run:
        for i in items:
            print(f"  event {i.event_id:>4}  rel={i.old['relevance']} "
                  f"sp={i.old['strategic_potential']}  {i.title[:70]}")
        print("\ndry run — no LLM calls made, nothing spent.")
        return 0

    if settings.llm_provider.strip().lower() != "anthropic" or not settings.llm_api_key:
        print("LLM_PROVIDER must be 'anthropic' and an API key must be set.", file=sys.stderr)
        return 2

    provider = MeteredAnthropic(settings.llm_model, settings.llm_api_key, settings.llm_max_tokens)
    failed = 0
    for n, item in enumerate(items, 1):
        try:
            item.new = classify(provider, item, settings.user_context)
            print(f"[{n}/{len(items)}] event {item.event_id}: "
                  f"rel {item.old['relevance']}->{item.new['relevance']}  "
                  f"sp {item.old['strategic_potential']}->{item.new['strategic_potential']}")
        except Exception as exc:  # noqa: BLE001 - one bad item must not end the run
            failed += 1
            print(f"[{n}/{len(items)}] event {item.event_id}: FAILED {exc}", file=sys.stderr)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db": str(args.db),
        "model": provider.model,
        "seed": SEED,
        "strata": {str(k): v for k, v in STRATA.items()},
        "sample_size": len(items),
        "failed_items": failed,
        "user_context": settings.user_context,
        "usage": {
            "calls": provider.calls,
            "input_tokens": provider.input_tokens,
            "output_tokens": provider.output_tokens,
            "cost_usd": None if provider.cost_usd() is None else round(provider.cost_usd(), 4),
            "price_usd_per_mtok": PRICE_USD_PER_MTOK.get(provider.model),
        },
        "before": summarise(items, "old"),
        "after": summarise(items, "new"),
        "items": [
            {
                "event_id": i.event_id, "title": i.title, "url": i.url,
                "old": i.old, "new": i.new, "errors": i.errors,
            }
            for i in items
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    before, after = report["before"], report["after"]
    print("\n--- calibration ---")
    print(f"r(relevance, strategic_potential):  before {before['r_relevance_strategic_potential']}"
          f"  ->  after {after['r_relevance_strategic_potential']}   (target: < 0.5)")
    print(f"rel<=2 AND sp>=4 (the quadrant):    before {before['quadrant_rel_le2_and_sp_ge4']}"
          f"  ->  after {after['quadrant_rel_le2_and_sp_ge4']}   (target: >= 1)")
    print(f"horizon_signal items:               before {before['horizon_signal_n']}"
          f"  ->  after {after['horizon_signal_n']}")
    print(f"relevance >= 4:                     before {before['relevance_ge4_n']}"
          f"  ->  after {after['relevance_ge4_n']}   (target: >= 1)")
    print(f"actionability >= 4:                 before {before['actionability_ge4_n']}"
          f"  ->  after {after['actionability_ge4_n']}   (target: >= 1)")
    cost = report["usage"]["cost_usd"]
    print(f"\ncost: {provider.calls} calls, {provider.input_tokens} in / "
          f"{provider.output_tokens} out tokens"
          f"{'' if cost is None else f' = ${cost:.2f}'}")
    print(f"raw output: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

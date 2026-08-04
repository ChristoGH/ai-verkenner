"""The M7.5 post generator — one `DigestData` projected into publishable DRAFTS.

Pure and offline: given the structured `DigestData` (the same graph-grounded backbone the digest is
rendered from), produce two signature pieces — **Weak Signal of the Week** (from the convergence
quadrant) and the **Noise Report** (from the inverted-hype demotions) — across three surfaces (X,
LinkedIn, Medium). No LLM, no network, no posting: every function here just formats text.

Invariants honoured (they apply to outputs, not just internal data — CLAUDE.md):

- **Every source URL is preserved.** Each draft carries its items' links, and `Draft.source_urls`
  records them for a test to check.
- **FACT stays separate from INTERPRETATION.** Item summaries are labelled `FACT`; the model's
  reading is labelled `Why it matters`. They are never blended into one sentence.
- **The hype inversion is respected.** The Noise Report ranks *loudest-but-emptiest* first
  (high hype, low salience); nothing sums hype with the salient axes.
- **No false convergence.** A convergence is claimed only when the items share ONE driving entity
  (`sections.coherent_cluster`); otherwise the Weak-Signal piece degrades to an honest "quiet week"
  framing and never says "converging". The label, the "N independent sources" count and the
  interpretation are all scoped to that shared driver — never unioned across unrelated items.
- **Tier is disclosed.** When the piece is built from `archive`-tier items, it says so and claims no
  top-tier provenance (D-016 ruling D).

This module does not re-derive ranking or the priority rule — the selection already happened in
`app.digests.sections`; here we only present it.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.digests.sections import DigestData, DigestItem
from app.posts.model import (
    DRAFT_BANNER,
    FACT_LABEL,
    INTERP_LABEL,
    METHOD_LABEL,
    PIECE_NOISE_REPORT,
    PIECE_WEAK_SIGNAL,
    SURFACE_LINKEDIN,
    SURFACE_MEDIUM,
    SURFACE_X,
    VAULT_BACKLINK,
    X_CHAR_LIMIT,
    Draft,
    PostBundle,
)

# The default image reference when no rendered image path is supplied: a clearly-marked instruction
# rather than a broken embed. `image.py` (or the CLI) passes a real path when one was produced.
PLACEHOLDER_IMAGE_REF = (
    "[image: screenshot the **Cosmograph Network** view of this cluster and attach it here]"
)

_METHODOLOGY = (
    "Detected by AI Verkenner: an entity/topic whose edges grew across *distinct independent "
    "publishers* in a short window (hub-dampened, IDF-weighted, singletons suppressed). Scores are "
    "0–5 with hype INVERTED (0 = signal, 5 = noise); hype only ever demotes. Source facts are the "
    "publishers'; the interpretation is AI Verkenner's."
)


# ----------------------------------------------------------------------------------------------- #
# small formatting helpers
# ----------------------------------------------------------------------------------------------- #


def _clean(text: str) -> str:
    """Collapse whitespace so a summary drops cleanly into a hook / bullet."""
    return " ".join((text or "").split())


def _md_link(item: DigestItem) -> str:
    return f"[{item.source_name or 'source'}]({item.source_url})"


def _publishers(items: tuple[DigestItem, ...], driver: str = "") -> list[str]:
    """Distinct publishers **backing the claim** (falls back to the item source name).

    On the converged path only items sharing the cluster's driving entity contribute, so
    "N independent sources" is N sources behind *one* claim. Unioning across unrelated items — the
    M7.5 defect — produced a number that was arithmetically correct and rhetorically false.
    """
    contributing = [it for it in items if it.driver == driver] if driver else list(items)
    seen: list[str] = []
    for it in contributing:
        names = it.contributing_sources or ((it.source_name,) if it.source_name else ())
        for name in names:
            if name and name not in seen:
                seen.append(name)
    return seen


def _all_urls(items: tuple[DigestItem, ...]) -> tuple[str, ...]:
    """Every source URL across the items, de-duplicated, order preserved (URL invariant)."""
    seen: list[str] = []
    for it in items:
        if it.source_url and it.source_url not in seen:
            seen.append(it.source_url)
    return tuple(seen)


def _ellipsis(text: str, room: int) -> str:
    """`text` cut to `room` characters with a trailing ellipsis (empty when there is no room)."""
    if room <= 0:
        return ""
    if len(text) <= room:
        return text
    return text[: max(0, room - 1)].rstrip() + "…"


# The shortest a label may be trimmed to before the trimmer starts sacrificing the surrounding prose
# instead. Below this a hook degrades into noise — the M7.5 `Op…` (D-025), where a 162-character
# source URL left ~2 characters for a 6-character entity name. A post that lost its subject is not
# "fitted", it is broken.
_MIN_LABEL_CHARS = 24


def _fit_x(prefix: str, variable: str, prose: str = "", atomic: str = "",
           *, limit: int = X_CHAR_LIMIT) -> str:
    """Assemble one X post — `prefix + variable + prose + atomic` — within `limit`.

    The single trimming rule for **every** emitted X post (hook and thread item alike): a second rule
    would drift from this one. `atomic` is the evidence link (a bare URL or a markdown link) and is
    never trimmed — a truncated URL is a dead URL, and the URL invariant outranks tidy prose.

    Order of sacrifice:

    1. the `variable` middle (a theme, title or summary), down to `_MIN_LABEL_CHARS`;
    2. then the trimmable `prose` around it, so a long source URL starves the sentence rather than
       the subject (D-025);
    3. then the variable down to nothing, and only then a hard cut — which still keeps `atomic`.
    """
    budget = limit - len(prefix) - len(atomic)      # room shared by `variable` + `prose`
    if budget <= 0:
        # The link alone fills the post. Keep it whole: a link with no sentence is still usable, a
        # truncated link is not. Only reachable for a pathologically long URL.
        return atomic or (prefix + variable + prose)[:limit]
    var_room = min(len(variable), max(0, budget - len(prose)))
    if var_room < _MIN_LABEL_CHARS:
        var_room = min(len(variable), budget, _MIN_LABEL_CHARS)
    var = _ellipsis(variable, var_room)
    return (prefix + var + _ellipsis(prose, budget - len(var)) + atomic).rstrip()


def _thread(items: list[tuple[str, str, str, str]], *, start: int) -> list[str]:
    """Number `(label, variable, prose, atomic)` thread items and fit each one to `X_CHAR_LIMIT`.

    Every numbered post on the X surface goes through here, so none can be emitted unchecked — the
    M7.5 defect was thread items of 400–800 characters beside a carefully-fitted hook.
    """
    out: list[str] = []
    for n, (label, variable, prose, atomic) in enumerate(items, start=start):
        prefix = f"{n}/ {label}: " if label else f"{n}/ "
        out.append(_fit_x(prefix, variable, prose, atomic))
    return out


def _link_fits_in_hook(prefix: str, prose: str, url: str) -> bool:
    """Can the evidence link sit in the hook and still leave a readable label? (D-025.)

    A placement question, not a trimming one: when the answer is no the link leads the thread instead
    — idiomatic on X, and the URL stays in the draft, so nothing is lost but the inline placement.
    """
    return len(prefix) + len(prose) + len(url) + _MIN_LABEL_CHARS <= X_CHAR_LIMIT


def _banner_block(piece_label: str, surface_label: str) -> list[str]:
    """The DRAFT header every file carries (an HTML comment + a visible callout)."""
    return [
        f"<!-- {DRAFT_BANNER} -->",
        f"> **⚠️ {piece_label} · {surface_label} — DRAFT.** No auto-posting; review before you post.",
        "",
    ]


def _theme(items: tuple[DigestItem, ...], driver: str = "") -> str:
    """The cluster label: the shared **driving entity** when one exists, else the lead item's title.

    A headline is one publisher's framing of one item; it cannot label a cluster (it produced the
    ungrammatical M7.5 hook). The entity is what the items actually share, and it is short.
    """
    if driver.strip():
        return _clean(driver)
    return _clean(items[0].title) if items else "an emerging signal"


def _tier_note(items: tuple[DigestItem, ...]) -> str:
    """Honest provenance when the piece is built from `archive`-tier items (D-016 ruling D).

    An archive-sourced weak signal is permitted; an *undisclosed* one is not. Returns "" when no
    archive-tier item is involved, so the line only ever appears when it is true.
    """
    archived = [it for it in items if it.priority_class == "archive"]
    if not archived:
        return ""
    scope = ("All of these are" if len(archived) == len(items)
             else f"{len(archived)} of these {len(items)} are")
    return (f"Tier disclosure: {scope} **archive-tier** items — the lowest-salience bucket in the "
            f"corpus, not the horizon-signal tier. No top-tier provenance is claimed.")


def _lead_interpretation(items: tuple[DigestItem, ...]) -> str:
    """The lead item's `why_it_matters`, **attributed to that item** — never as the cluster's view.

    Presenting one item's interpretation as the whole cluster's is what made the M7.5 draft assert a
    thesis eight items did not support. Returns "" when the lead carries no interpretation.
    """
    if not items:
        return ""
    interp = _clean(items[0].why_it_matters)
    if not interp:
        return ""
    return (f"AI Verkenner's reading of the FIRST item above only — not a claim about the whole "
            f"cluster — {interp}")


# ----------------------------------------------------------------------------------------------- #
# Weak Signal of the Week
# ----------------------------------------------------------------------------------------------- #


def weak_cluster(data: DigestData) -> tuple[tuple[DigestItem, ...], bool]:
    """The items driving the weak-signal piece + whether a genuine convergence fired.

    The coherence decision is **not re-derived here** — `sections.coherent_cluster` already required
    a shared driving entity and recorded its name in `data.weak_driver`. A non-empty `weak_driver`
    means `weak_signals` *is* that cluster; empty means the quiet-week quadrant, which may not be
    called converging.
    """
    return data.weak_signals, bool(data.weak_driver)


def _weak_x(cluster: tuple[DigestItem, ...], driver: str, image_ref: str) -> Draft:
    urls = _all_urls(cluster)
    pubs = _publishers(cluster, driver)
    lead_url = cluster[0].source_url if cluster else ""
    tier = _tier_note(cluster)
    interp = _lead_interpretation(cluster)

    if driver:
        prefix = "🛰️ Weak signal of the week: "
        prose = (
            f" — {len(cluster)} items converging across {len(pubs)} independent sources, "
            f"before it's a headline. Evidence 👇 "
        )
        variable = _theme(cluster, driver)
    else:
        prefix = "🛰️ Quiet week on the radar — no strong cross-source convergence yet. Watching: "
        prose = ". " if lead_url else "."
        variable = _theme(cluster)
    inline_link = bool(lead_url) and _link_fits_in_hook(prefix, prose, lead_url)
    hook = _fit_x(prefix, variable, prose, lead_url if inline_link else "")

    lines = _banner_block("Weak Signal of the Week", "X / Twitter")
    lines.append(f"**Hook post (≤{X_CHAR_LIMIT} chars — {len(hook)}):**")
    lines.append("")
    lines.append(hook)
    lines.append(f"📊 {image_ref}")
    lines.append("")
    lines.append("**Thread (optional):**")
    items: list[tuple[str, str, str, str]] = []
    if lead_url and not inline_link:
        # Displaced from the hook because it could not sit there beside a readable label (D-025).
        items.append(("Evidence", "", "", lead_url))
    for it in cluster:
        items.append((FACT_LABEL, _clean(it.summary), " ", f"({_md_link(it)})"))
    if interp:
        items.append((INTERP_LABEL, interp, "", ""))
    if tier:
        items.append(("", tier, "", ""))
    lines += _thread(items, start=2)
    if urls:
        lines.append("")
        lines.append("**Sources (reference list — not a post):**")
        lines.append("Sources: " + " ".join(urls))
    text = "\n".join(lines).rstrip() + "\n"
    return Draft(SURFACE_X, PIECE_WEAK_SIGNAL, "Weak Signal of the Week — X",
                 "weak-signal-x", hook, text, urls)


def _bullets_or_pad(items: tuple[DigestItem, ...], pad_note: str) -> list[str]:
    """Exactly three FACT bullets (each with its source link); pad honestly if fewer items."""
    bullets = [f"- {FACT_LABEL}: {_clean(it.summary)} ({_md_link(it)})" for it in items[:3]]
    while len(bullets) < 3:
        bullets.append(f"- {pad_note}")
    return bullets


def _weak_linkedin(cluster: tuple[DigestItem, ...], driver: str, image_ref: str) -> Draft:
    urls = _all_urls(cluster)
    pubs = _publishers(cluster, driver)
    if driver:
        hook = (f"The AI signal most feeds will miss this week: {_theme(cluster, driver)} is "
                f"quietly converging across {len(pubs)} independent sources.")
        pad = "(only a few early signals so far — full horizon list in the digest)"
    else:
        hook = ("No loud convergence this week — here's what is quietly moving on the AI horizon, "
                "before it trends:")
        pad = "(a thin week — these are the quiet items worth a bookmark)"

    lines = _banner_block("Weak Signal of the Week", "LinkedIn")
    lines.append(hook)
    lines.append("")
    lines += _bullets_or_pad(cluster, pad)
    lines.append("")
    interp = _lead_interpretation(cluster)
    lines.append(f"{INTERP_LABEL}: " + (interp or
                 "individually weak, together a direction worth tracking early."))
    tier = _tier_note(cluster)
    if tier:
        lines.append("")
        lines.append(tier)
    lines.append("")
    lines.append(f"[image slot] 📊 {image_ref}")
    lines.append("")
    lines.append("CTA: Full cluster + timeline + evidence on the blog. Follow for next week's radar.")
    if urls:
        lines.append("")
        lines.append("Sources: " + " · ".join(f"<{u}>" for u in urls))
    text = "\n".join(lines).rstrip() + "\n"
    return Draft(SURFACE_LINKEDIN, PIECE_WEAK_SIGNAL, "Weak Signal of the Week — LinkedIn",
                 "weak-signal-linkedin", hook, text, urls)


def _timeline(items: tuple[DigestItem, ...]) -> list[str]:
    dated = sorted(
        (it for it in items if it.published_at is not None),
        key=lambda it: it.published_at,  # type: ignore[return-value]
    )
    if not dated:
        return ["- (no published dates available for these items)"]
    return [f"- {it.published_at.date().isoformat()} — {_clean(it.title)} ({_md_link(it)})"
            for it in dated]


def _weak_medium(cluster: tuple[DigestItem, ...], driver: str, image_ref: str,
                 period: str) -> Draft:
    urls = _all_urls(cluster)
    pubs = _publishers(cluster, driver)
    converged = bool(driver)
    title = (f"Weak Signal of the Week: {_theme(cluster, driver)}" if converged
             else "Weak Signal of the Week: a quiet horizon")

    lines = _banner_block("Weak Signal of the Week", "Medium (long-form)")
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"*Period: {period}.*")
    lines.append("")
    if converged:
        lines.append(
            f"This week AI Verkenner surfaced a convergence most feeds will miss: "
            f"**{_theme(cluster, driver)}** drew {len(cluster)} individually-weak signals across "
            f"**{len(pubs)} independent publishers** ({', '.join(pubs)}) — the pattern of something "
            f"moving *before* it is loud. Every item below converges on that same entity; that "
            f"shared driver is what makes this a cluster rather than a list."
        )
    else:
        lines.append(
            "No strong cross-source convergence fired this week: no group of items shared a driving "
            "entity. Rather than manufacture a trend, here are the quiet items sitting on the "
            "horizon — unconnected for now, worth watching if they start to overlap."
        )
    tier = _tier_note(cluster)
    if tier:
        lines.append("")
        lines.append(tier)
    lines.append("")
    lines.append("## The cluster (source facts)")
    for it in cluster:
        lines.append(f"- **{_clean(it.title)}** — {FACT_LABEL}: {_clean(it.summary)} "
                     f"({_md_link(it)}, hype {it.hype}/5 — 0=signal)")
    lines.append("")
    lines.append("## Timeline")
    lines += _timeline(cluster)
    lines.append("")
    lines.append(f"## {INTERP_LABEL} (AI Verkenner's reading, item by item)")
    interps = [f"- On *{_clean(it.title)}*: {_clean(it.why_it_matters)}"
               for it in cluster if _clean(it.why_it_matters)]
    lines += interps or ["- Individually weak; together, an early direction worth tracking."]
    lines.append("")
    lines.append(f"![convergence cluster] {image_ref}")
    lines.append("")
    lines.append("## Evidence")
    for it in cluster:
        lines.append(f"- {_md_link(it)} — {it.source_url}")
    lines.append("")
    lines.append(f"## {METHOD_LABEL}")
    lines.append("> " + _METHODOLOGY)
    text = "\n".join(lines).rstrip() + "\n"
    return Draft(SURFACE_MEDIUM, PIECE_WEAK_SIGNAL, "Weak Signal of the Week — Medium",
                 "weak-signal-medium", title, text, urls)


# ----------------------------------------------------------------------------------------------- #
# The Noise Report (inverted hype — loudest but emptiest)
# ----------------------------------------------------------------------------------------------- #


def _noise_ranked(data: DigestData, *, limit: int) -> tuple[tuple[DigestItem, ...], int]:
    """The demoted items loudest-but-emptiest first, capped, plus the **true** demoted total.

    The cap (task 010 Defect 3) is editorial only: 187 demotions produced a 141 KB Medium draft
    nobody would read. Nothing is re-scored and nothing is hidden — the total comes back alongside
    the capped list and every surface states it, so the cap never misrepresents the corpus.
    """
    from app.scoring.ranking import salience

    ranked = tuple(sorted(data.noise, key=lambda it: (-it.hype, salience(it))))
    shown = ranked[:limit] if limit > 0 else ranked
    return shown, len(ranked)


def _demoted_total_line(shown: int, total: int) -> str:
    """The honest count sentence: the full demoted total first, the capped selection second."""
    if shown >= total:
        return f"{total} item(s) were demoted this week."
    return f"{total} items were demoted this week; these are the {shown} loudest."


def _noise_reason(it: DigestItem, high_hype: int) -> str:
    if it.hype >= high_hype:
        return f"hype {it.hype}/5 — loud, low signal"
    return "archived — low relevance to the stack"


def _noise_x(noise: tuple[DigestItem, ...], high_hype: int, total: int) -> Draft:
    urls = _all_urls(noise)
    inline_link = False
    if noise:
        lead = noise[0]
        prefix = "📢 Noise report — the loudest-but-emptiest AI story this week: "
        prose = f" ({_noise_reason(lead, high_hype)}). More heat than signal. "
        inline_link = _link_fits_in_hook(prefix, prose, lead.source_url)
        hook = _fit_x(prefix, _clean(lead.title), prose,
                      lead.source_url if inline_link else "")
    else:
        hook = "📢 Noise report: a genuinely quiet week — nothing crossed the noise threshold. 🎉"

    lines = _banner_block("Noise Report", "X / Twitter")
    lines.append(f"**Hook post (≤{X_CHAR_LIMIT} chars — {len(hook)}):**")
    lines.append("")
    lines.append(hook)
    lines.append("")
    if noise:
        lines.append("**Thread (optional):**")
        items: list[tuple[str, str, str, str]] = []
        if not inline_link:
            items.append(("Evidence", "", "", noise[0].source_url))
        # The true demoted total leads the thread, so the capped selection below can never read as
        # the whole corpus.
        items.append(("", _demoted_total_line(min(len(noise), 5), total), "", ""))
        for it in noise[:5]:
            items.append((FACT_LABEL, _clean(it.title),
                          f" — {_noise_reason(it, high_hype)} ", f"({_md_link(it)})"))
        items.append((INTERP_LABEL, "hype is inverted here — 0=signal, 5=noise. "
                                    "Loud ≠ important.", "", ""))
        lines += _thread(items, start=2)
        if urls:
            lines.append("")
            lines.append("**Sources (reference list — not a post):**")
            lines.append("Sources: " + " ".join(urls))
    text = "\n".join(lines).rstrip() + "\n"
    return Draft(SURFACE_X, PIECE_NOISE_REPORT, "Noise Report — X", "noise-report-x",
                 hook, text, urls)


def _noise_linkedin(noise: tuple[DigestItem, ...], high_hype: int, total: int) -> Draft:
    urls = _all_urls(noise)
    if noise:
        # `total` is the true demoted count, not the three bullets below it — the cap is editorial
        # and must never shrink the number the reader is given.
        hook = (f"This week's loudest-but-emptiest in AI — {total} stories that were all "
                f"volume, little signal. The {min(len(noise), 3)} loudest:")
        pad = "(only a couple crossed the noise line this week)"
    else:
        hook = "A rare quiet week in AI: nothing crossed the noise threshold. Enjoy the silence."
        pad = "(nothing to report — genuinely low-noise week)"

    lines = _banner_block("Noise Report", "LinkedIn")
    lines.append(hook)
    lines.append("")
    bullets = [f"- {FACT_LABEL}: {_clean(it.title)} — {_noise_reason(it, high_hype)} ({_md_link(it)})"
               for it in noise[:3]]
    while len(bullets) < 3:
        bullets.append(f"- {pad}")
    lines += bullets
    lines.append("")
    lines.append(f"{INTERP_LABEL}: a feed built on hype can't publish this about itself. "
                 "Signal > volume.")
    lines.append("")
    lines.append("CTA: Want the signal instead of the noise? Follow AI Verkenner's weekly radar.")
    if urls:
        lines.append("")
        lines.append("Sources: " + " · ".join(f"<{u}>" for u in urls))
    text = "\n".join(lines).rstrip() + "\n"
    return Draft(SURFACE_LINKEDIN, PIECE_NOISE_REPORT, "Noise Report — LinkedIn",
                 "noise-report-linkedin", hook, text, urls)


def _noise_medium(noise: tuple[DigestItem, ...], high_hype: int, period: str,
                  total: int) -> Draft:
    urls = _all_urls(noise)
    title = "The Noise Report"

    lines = _banner_block("Noise Report", "Medium (long-form)")
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"*Period: {period}.*")
    lines.append("")
    if noise:
        lines.append(
            f"{_demoted_total_line(len(noise), total)} They were loud enough to demote — high hype "
            "or low enough relevance to archive. Named honestly, loudest first, because a "
            "hype-driven feed structurally cannot."
        )
        lines.append("")
        lines.append("## The loudest-but-emptiest (source facts)")
        for it in noise:
            lines.append(f"- **{_clean(it.title)}** — {FACT_LABEL}: {_clean(it.summary)} "
                         f"({_noise_reason(it, high_hype)}) ({_md_link(it)})")
        lines.append("")
        lines.append(f"## {INTERP_LABEL}")
        lines.append("- Volume is not signal. Each item above scored high hype or low relevance to "
                     "the reader's actual stack — so it was demoted, not surfaced.")
        lines.append("")
        lines.append("## Evidence")
        for it in noise:
            lines.append(f"- {_md_link(it)} — {it.source_url}")
    else:
        lines.append("A genuinely quiet week: nothing crossed the noise threshold. No demotions to "
                     "report — which is itself a small signal.")
    lines.append("")
    lines.append(f"## {METHOD_LABEL}")
    lines.append("> " + _METHODOLOGY)
    text = "\n".join(lines).rstrip() + "\n"
    return Draft(SURFACE_MEDIUM, PIECE_NOISE_REPORT, "Noise Report — Medium",
                 "noise-report-medium", title, text, urls)


# ----------------------------------------------------------------------------------------------- #
# public entry point
# ----------------------------------------------------------------------------------------------- #


def _period_label(start: datetime | None, end: datetime | None) -> str:
    if start is None and end is None:
        return "the current corpus"
    s = start.date().isoformat() if start else "?"
    e = end.date().isoformat() if end else "?"
    return f"{s} → {e}"


def generate_posts(
    data: DigestData,
    *,
    digest_id: int | None = None,
    generated_at: datetime | None = None,
    high_hype: int | None = None,
    image_ref: str | None = None,
    noise_limit: int | None = None,
) -> PostBundle:
    """Project one `DigestData` into the six drafts (2 pieces × 3 surfaces).

    Pure: no LLM, no network, no posting. `image_ref` is the pointer the drafts embed for the
    convergence image; when omitted, a clearly-marked "screenshot the Cosmograph view" placeholder
    is used instead of a broken embed.
    """
    from app.core.config import settings

    generated_at = generated_at or datetime.now(timezone.utc)
    high_hype = settings.digest_high_hype if high_hype is None else high_hype
    noise_limit = settings.noise_report_limit if noise_limit is None else noise_limit
    image_ref = image_ref or PLACEHOLDER_IMAGE_REF
    period = _period_label(data.period_start, data.period_end)

    cluster, converged = weak_cluster(data)
    # The shared driving entity, or "" when no coherent cluster survived grouping. Everything the
    # weak-signal drafts claim (label, source count, "converging") keys off this one value.
    driver = data.weak_driver if converged else ""
    # `noise` is the capped, loudest-first selection; `noise_total` is the true demoted count that
    # every Noise Report surface must state (the cap is editorial, not a claim about corpus size).
    noise, noise_total = _noise_ranked(data, limit=noise_limit)

    drafts = (
        _weak_x(cluster, driver, image_ref),
        _weak_linkedin(cluster, driver, image_ref),
        _weak_medium(cluster, driver, image_ref, period),
        _noise_x(noise, high_hype, noise_total),
        _noise_linkedin(noise, high_hype, noise_total),
        _noise_medium(noise, high_hype, period, noise_total),
    )
    return PostBundle(
        digest_id=digest_id,
        generated_at=generated_at,
        period_start=data.period_start,
        period_end=data.period_end,
        has_convergence=converged,
        drafts=drafts,
    )


__all__ = ["generate_posts", "weak_cluster", "PostBundle", "Draft",
           "PLACEHOLDER_IMAGE_REF", "VAULT_BACKLINK"]

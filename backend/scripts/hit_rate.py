#!/usr/bin/env python3
"""Hit rate of a corpus against docs/USER_CONTEXT.md's named stack.

WHAT THIS MEASURES (source fact, not interpretation): how many raw items name a technology
that USER_CONTEXT.md explicitly lists under "Strong relevance signals" or "Active work".
Whole-word, separator-tolerant string matching over title + published summary. No LLM, no
embeddings, no scoring — this is deliberately dumber than enrichment so it can act as an
EXTERNAL check on it (CLAUDE.md: the maker is not the checker).

WHY IT EXISTS: the task 017 calibration sample matched 2 of 45 items (~4%) against the named
prediction categories. If a fresh ingest reproduces that rate, the binding constraint on
Verkenner's usefulness is SOURCE SCOPE, not scoring — and enriching the rest is spending money
on a corpus that cannot serve the user.

TERMS ARE TIERED BY AMBIGUITY, and ambiguous ones are reported separately rather than folded
into one number. "AKS" matching "breAKS" is exactly how a hit rate lies.

Usage:
    python3 hit_rate.py [path/to/corpus.db] [--since YYYY-MM-DD]
                        [--ingested-since YYYY-MM-DD[THH:MM:SS]] [--verbose]

  --since           filters on published_at  — "items the world published since X"
  --ingested-since  filters on created_at    — "items THIS run added". Use this one to
                    measure a fetch: an item published in June and first seen today is a
                    new item, and --since would silently drop it.

Run from the repository root, with backend/.venv active. The default corpus path is
relative (CLAUDE.md D-006: cwd picks the database).
"""
from __future__ import annotations

import re
import sqlite3
import sys
from collections import Counter

# --- Terms lifted verbatim from docs/USER_CONTEXT.md -------------------------------------------
# UNAMBIGUOUS: a whole-word match is a real match. Proper nouns and coined names.
UNAMBIGUOUS = [
    "Qdrant", "Neo4j", "GraphRAG", "pgvector", "Lakebase", "Knative", "tree-sitter",
    "Cosmograph", "Sunsynk", "Clickatell", "Paystack", "Ozow", "spaCy", "FastAPI",
    "Anthropic", "sentence-transformers", "Voyage", "Cursor", "Firebase", "Cloud Run",
    "Kubernetes", "Knowledge graph", "vector database", "vector store", "Agent SDK",
]
# AMBIGUOUS: real signals, but each has a common false-positive mode. Counted separately.
#   RAG    -> only as an uppercase standalone token (not "dRAG", "bRAG")
#   AKS    -> uppercase standalone only ("breaks" is the known false hit)
#   Claude -> proper noun, but also a first name
#   React  -> the library vs the verb "react"
#   STT    -> uppercase standalone
AMBIGUOUS = ["RAG", "AKS", "Claude", "React", "STT", "SQLite", "agentic", "embeddings"]

CASE_SENSITIVE = {"RAG", "AKS", "STT", "React"}


def _pattern(term: str) -> re.Pattern:
    """Whole-word, separator-tolerant: 'tree-sitter' also matches 'tree sitter', 'treesitter'."""
    parts = [re.escape(p) for p in re.split(r"[-\s]+", term)]
    body = r"[-\s]?".join(parts)
    flags = 0 if term in CASE_SENSITIVE else re.IGNORECASE
    return re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])", flags)


PATTERNS = {t: _pattern(t) for t in UNAMBIGUOUS + AMBIGUOUS}


def hits(text: str) -> tuple[set[str], set[str]]:
    """Return (unambiguous terms found, ambiguous terms found) in one item's text."""
    strong = {t for t in UNAMBIGUOUS if PATTERNS[t].search(text)}
    weak = {t for t in AMBIGUOUS if PATTERNS[t].search(text)}
    return strong, weak


def main() -> int:
    argv = sys.argv[1:]
    verbose = "--verbose" in argv
    since = ingested_since = None
    positional: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        # A flag's VALUE is not a positional argument. Consuming it as one made
        # `hit_rate.py --since 2026-08-19` open a database called "2026-08-19".
        if a in ("--since", "--ingested-since") and i + 1 < len(argv):
            if a == "--since":
                since = argv[i + 1]
            else:
                ingested_since = argv[i + 1]
            i += 2
            continue
        if not a.startswith("--"):
            positional.append(a)
        i += 1
    db = positional[0] if positional else "data/dev_corpus.db"

    con = sqlite3.connect(db)
    q = ("SELECT r.id, r.title, COALESCE(r.summary,''), r.source_name, r.published_at, "
         "e.relevance, e.priority_class "
         "FROM raw_item r LEFT JOIN enriched_item e ON e.event_id = r.event_id")
    params: list = []
    where: list[str] = []
    if since:
        where.append("r.published_at >= ?")
        params.append(since)
    if ingested_since:
        where.append("r.created_at >= ?")
        params.append(ingested_since)
    if where:
        q += " WHERE " + " AND ".join(where)
    rows = con.execute(q, params).fetchall()

    n = len(rows)
    window = ""
    if since:
        window += f"   published since {since}"
    if ingested_since:
        window += f"   ingested since {ingested_since}"
    if n == 0:
        print(f"no rows in {db}{window}")
        return 1

    strong_items, weak_only_items = [], []
    term_counts: Counter = Counter()
    by_source: Counter = Counter()
    source_totals: Counter = Counter()

    for rid, title, summary, source, pub, rel, pclass in rows:
        source_totals[source] += 1
        s, w = hits(f"{title}\n{summary}")
        for t in s | w:
            term_counts[t] += 1
        if s:
            strong_items.append((rid, title, source, pub, rel, pclass, sorted(s), sorted(w)))
            by_source[source] += 1
        elif w:
            weak_only_items.append((rid, title, source, pub, rel, pclass, sorted(w)))

    ns, nw = len(strong_items), len(weak_only_items)
    print(f"corpus: {db}{window}")
    print(f"items: {n}\n")
    print(f"  UNAMBIGUOUS hit:  {ns:4}  ({ns / n:6.1%})   names a term USER_CONTEXT lists explicitly")
    print(f"  ambiguous only:   {nw:4}  ({nw / n:6.1%})   needs eyeballing — see --verbose")
    print(f"  no hit:           {n - ns - nw:4}  ({(n - ns - nw) / n:6.1%})\n")

    print("terms found (count of items):")
    for t, c in term_counts.most_common():
        mark = " " if t in UNAMBIGUOUS else "?"
        print(f"  {mark} {c:4}  {t}")

    print("\nunambiguous hits by source (hits / total from that source):")
    for src, tot in source_totals.most_common():
        h = by_source.get(src, 0)
        if tot:
            print(f"    {h:4} / {tot:4}  ({h / tot:5.0%})  {src}")

    scored = [r for r in strong_items if r[4] is not None]
    if scored:
        mean_rel = sum(r[4] for r in scored) / len(scored)
        others = [r for r in rows if r[5] is not None]
        mean_all = sum(r[5] for r in others) / len(others) if others else 0
        print(f"\nmean relevance — unambiguous hits: {mean_rel:.2f}   whole corpus: {mean_all:.2f}")
        print("  (if these are equal, enrichment is NOT distinguishing the user's stack)")
        top = sorted(scored, key=lambda r: -r[4])[:10]
        print("\n  top 10 hits by relevance:")
        for rid, title, source, pub, rel, pclass, s, w in top:
            print(f"    rel={rel}  {pclass or '-':22}  {','.join(s)[:34]:34}  {title[:58]}")

    if verbose:
        print("\n--- every unambiguous hit ---")
        for rid, title, source, pub, rel, pclass, s, w in strong_items:
            print(f"  [{rid}] rel={rel} {source[:22]:22} {','.join(s)[:30]:30} {title[:60]}")
        print("\n--- ambiguous-only (AUDIT THESE for false positives) ---")
        for rid, title, source, pub, rel, pclass, w in weak_only_items:
            print(f"  [{rid}] rel={rel} {','.join(w)[:24]:24} {title[:64]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

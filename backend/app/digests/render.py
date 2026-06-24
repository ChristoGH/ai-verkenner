"""Render a `DigestData` to Markdown (M7).

Two renderers over the same structured data:

- `render_markdown` — the **deterministic fallback** used when no LLM provider is configured (and by
  the offline tests). It guarantees all ten sections, keeps source fact separate from
  interpretation, preserves every source link, and reports the noise count honestly. It is plain,
  not eloquent — structure and honesty over prose.
- `render_llm_inputs` — the **user message** for the composition LLM. It hands the model the same
  pre-selected, graph-grounded data (the system prompt is `prompts/digest.md`), so the LLM writes
  the decision-oriented prose without re-fetching or re-scoring anything.

Neither renderer re-scores or re-classifies — they only present `DigestData`.
"""

from __future__ import annotations

from datetime import datetime

from app.digests.sections import SECTION_HEADINGS, DigestData, DigestItem


def _period_label(start: datetime | None, end: datetime | None) -> str:
    if start is None and end is None:
        return "the current corpus"
    s = start.date().isoformat() if start else "?"
    e = end.date().isoformat() if end else "?"
    return f"{s} → {e}"


def _src(item: DigestItem) -> str:
    return f"[{item.source_name or 'source'}]({item.source_url})"


def _bullet(item: DigestItem) -> str:
    """One decision-oriented bullet: fact, then interpretation, then the action and the link."""
    parts = [f"- **{item.title}** — {item.summary}"]
    if item.why_it_matters.strip():
        parts.append(f" _Why:_ {item.why_it_matters}")
    if item.recommended_action.strip():
        parts.append(f" _Action:_ {item.recommended_action}")
    parts.append(f" ({_src(item)}, hype {item.hype}/5 — 0=signal)")
    return "".join(parts)


def _weak_bullet(item: DigestItem) -> str:
    line = f"- **{item.title}** — {item.summary}"
    if item.graph_why:
        line += f" _{item.graph_why}._"
    if item.contributing_sources:
        line += f" Sources: {', '.join(item.contributing_sources)}."
    line += f" ({_src(item)})"
    return line


def _section(heading: str, items: tuple[DigestItem, ...], *, weak: bool = False) -> list[str]:
    lines = [f"## {heading}"]
    if not items:
        lines.append("_Nothing this period._")
    else:
        render = _weak_bullet if weak else _bullet
        lines.extend(render(it) for it in items)
    lines.append("")
    return lines


def render_markdown(data: DigestData, *, user_context: str | None = None) -> str:
    """Deterministic fallback render — all ten sections, honest counts, links preserved."""
    period = _period_label(data.period_start, data.period_end)
    lines: list[str] = [f"# Weekly digest — {period}", ""]

    # 1. Executive summary (deterministic, honest).
    lines.append(f"## {SECTION_HEADINGS[0]}")
    lines.append(
        f"{data.total_events} development(s) this period: {len(data.must_know)} need attention, "
        f"{len(data.should_read)} worth reading, {len(data.weak_signals)} weak signal(s) on the "
        f"horizon, and {data.noise_count} filtered as noise (archived / high-hype)."
    )
    lines.append("")

    # 2–9. The list sections.
    lines += _section(SECTION_HEADINGS[1], data.must_know)
    lines += _section(SECTION_HEADINGS[2], data.should_read)
    lines += _section(SECTION_HEADINGS[3], data.weak_signals, weak=True)
    lines += _section(SECTION_HEADINGS[4], data.research_radar)
    lines += _section(SECTION_HEADINGS[5], data.tool_changes)
    lines += _section(SECTION_HEADINGS[6], data.risks)
    lines += _section(SECTION_HEADINGS[7], data.opportunities)
    lines += _section(SECTION_HEADINGS[8], data.suggested_experiments)

    # 10. Ignored / noise count.
    lines.append(f"## {SECTION_HEADINGS[9]}")
    lines.append(
        f"{data.noise_count} item(s) were archived or high-hype (hype-demoted) and excluded "
        f"from the body."
    )
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _input_item(item: DigestItem) -> str:
    bits = [
        f"  - title: {item.title}",
        f"    source: {item.source_name} <{item.source_url}>",
        f"    priority_class: {item.priority_class}",
        f"    scores: relevance={item.relevance} novelty={item.novelty} "
        f"actionability={item.actionability} strategic={item.strategic_potential} "
        f"hype={item.hype}(inverted:0=signal)",
        f"    summary (FACT): {item.summary}",
        f"    why_it_matters (INTERPRETATION): {item.why_it_matters}",
        f"    connection_to_user_work: {item.connection_to_user_work}",
        f"    recommended_action: {item.recommended_action}",
    ]
    if item.graph_why:
        bits.append(f"    convergence: {item.graph_why} "
                    f"[sources: {', '.join(item.contributing_sources)}]")
    return "\n".join(bits)


def _input_section(heading: str, items: tuple[DigestItem, ...]) -> str:
    if not items:
        return f"{heading}: (none)"
    return f"{heading}:\n" + "\n".join(_input_item(it) for it in items)


def render_llm_inputs(data: DigestData, *, user_context: str) -> str:
    """The user-message inputs for the composition LLM (system prompt = prompts/digest.md)."""
    period = _period_label(data.period_start, data.period_end)
    blocks = [
        f"period: {period}",
        f"user_context: {user_context}",
        "",
        "Pre-selected, graph-grounded items per section (compose decisions, not a link list; keep "
        "every source link; keep FACT separate from INTERPRETATION; treat hype as a demotion):",
        "",
        _input_section("MUST_KNOW (immediate_priority)", data.must_know),
        _input_section("SHOULD_READ (operational_update)", data.should_read),
        _input_section("WEAK_SIGNALS (horizon quadrant, by convergence)", data.weak_signals),
        _input_section("RESEARCH_RADAR", data.research_radar),
        _input_section("TOOL_CHANGES", data.tool_changes),
        _input_section("RISKS", data.risks),
        _input_section("OPPORTUNITIES", data.opportunities),
        _input_section("CANDIDATE_EXPERIMENTS", data.suggested_experiments),
        "",
        f"noise_count (archived / high-hype, excluded): {data.noise_count}",
        f"total_events_considered: {data.total_events}",
    ]
    return "\n".join(blocks)

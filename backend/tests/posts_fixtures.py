"""Two fixture Digests for the M7.5 post generator — built offline, no DB, no stores, no LLM.

`thin_digest()` mirrors the real M7 smoke: a horizon quadrant with **no** cross-source convergence
(single-source items, `convergence == 0`) plus a couple of noise demotions — the case the Weak-Signal
piece must degrade on without claiming anything is "converging".

`converging_digest()` is a synthetic digest **with** a genuine convergence: one entity (an on-device
agent runtime) drawing three individually-weak signals across three *named independent publishers* —
so the marquee "Weak Signal of the Week" code path is fully exercised without a live broad run.

Both are `DigestData` objects, so they drive `app.posts.generate_posts` directly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.digests.sections import DigestData, DigestItem

# Relative to now (offsets below run forward from here, staying in the past): a hardcoded absolute
# base ages out of the 30-day convergence window and fails on a calendar boundary, not a code change.
_BASE = datetime.now(timezone.utc) - timedelta(days=7)

# The driving entity every item in `converging_digest()` converges on. `DRIVER_UID` is the normalised
# identity that grouping keys off; `DRIVER` is only the display label. Deliberately NOT equal to any
# item's title, so the cluster-label regression stays pinned.
DRIVER = "on-device agent runtime"
DRIVER_UID = 4242


def _item(
    event_id: int,
    *,
    title: str,
    source_name: str,
    source_url: str,
    source_type: str = "rss",
    priority_class: str = "horizon_signal",
    category: str = "research",
    tags: tuple[str, ...] = (),
    relevance: int = 2,
    novelty: int = 3,
    actionability: int = 2,
    strategic_potential: int = 4,
    hype: int = 1,
    summary: str = "",
    why_it_matters: str = "",
    recommended_action: str = "",
    is_weak_signal: bool = True,
    horizon: str | None = "mid",
    graph_why: str = "",
    graph_score: float = 0.0,
    convergence: int = 0,
    contributing_sources: tuple[str, ...] = (),
    driver: str = "",
    driver_uid: int | None = None,
    driver_mentions: int = 0,
    driver_weight: float = 1.0,
    driver_weight_why: str = "",
    coverage_sources: tuple[str, ...] = (),
    published_offset_days: int = 0,
) -> DigestItem:
    return DigestItem(
        event_id=event_id,
        title=title,
        source_name=source_name,
        source_url=source_url,
        source_type=source_type,
        published_at=_BASE + timedelta(days=published_offset_days),
        priority_class=priority_class,
        category=category,
        tags=tags,
        relevance=relevance,
        novelty=novelty,
        actionability=actionability,
        strategic_potential=strategic_potential,
        hype=hype,
        summary=summary,
        why_it_matters=why_it_matters,
        connection_to_user_work="",
        recommended_action=recommended_action,
        is_weak_signal=is_weak_signal,
        horizon=horizon,
        graph_why=graph_why,
        graph_score=graph_score,
        convergence=convergence,
        contributing_sources=contributing_sources,
        driver=driver,
        driver_uid=driver_uid,
        driver_mentions=driver_mentions,
        driver_weight=driver_weight,
        driver_weight_why=driver_weight_why,
        coverage_sources=coverage_sources,
    )


def _empty_sections() -> dict:
    return dict(
        must_know=(), should_read=(), research_radar=(), tool_changes=(),
        risks=(), opportunities=(), suggested_experiments=(),
    )


def _noise_items() -> tuple[DigestItem, ...]:
    """Two demotions: one loud (hype 5) and one archived — the Noise Report's raw material."""
    loud = _item(
        90, title="This one AI trick will change EVERYTHING (you won't believe #3)",
        source_name="HypeDaily", source_url="https://hypedaily.example/agi-now",
        priority_class="operational_update", category="marketing", tags=("marketing",),
        relevance=2, novelty=1, actionability=1, strategic_potential=1, hype=5,
        summary="A vendor blog claims its chatbot is now 'basically AGI'.",
        is_weak_signal=False, horizon=None,
    )
    archived = _item(
        91, title="Weekly roundup: 47 links you already saw",
        source_name="LinkFarm", source_url="https://linkfarm.example/roundup-201",
        priority_class="archive", category="misc", tags=("roundup",),
        relevance=1, novelty=1, actionability=1, strategic_potential=1, hype=2,
        summary="An aggregator re-lists last week's headlines.",
        is_weak_signal=False, horizon=None,
    )
    return (loud, archived)


def thin_digest() -> DigestData:
    """No convergence: single-source horizon items + noise (mirrors the M7 smoke)."""
    weak = (
        _item(
            1, title="A small lab open-sources a state-ledger for tool-calling agents",
            source_name="The Register", source_url="https://theregister.example/ledger-agent",
            source_type="rss", category="research", tags=("agents",),
            summary="A niche paper proposes persisting agent state in SQLite before each tool call.",
            why_it_matters="A pre-call constraint check is a candidate design for reliable agents.",
            graph_score=0.0, convergence=0, contributing_sources=("The Register",),
        ),
        _item(
            2, title="Windows 26H2 preview ships to insiders",
            source_name="Ars Technica", source_url="https://arstechnica.example/win-26h2",
            source_type="rss", category="misc", tags=("os",),
            relevance=1, strategic_potential=1,
            summary="Microsoft pushes a new Windows preview build.",
            why_it_matters="Off-stack for a RAG/graph engineer; awareness only.",
            graph_score=0.0, convergence=0, contributing_sources=("Ars Technica",),
        ),
    )
    return DigestData(
        period_start=_BASE, period_end=_BASE + timedelta(days=6),
        total_events=4, item_count=2, noise_count=2, graphrag=True,
        weak_signals=weak, referenced_event_ids=(1, 2), noise=_noise_items(),
        **_empty_sections(),
    )


def converging_digest() -> DigestData:
    """A genuine convergence: one entity across three named independent publishers.

    All three items carry the **same** `driver_uid` — that shared driving entity is what makes them
    a cluster (task 010). Items converging on *different* entities are a list, not a convergence.
    """
    why = ("On-device agent runtimes are moving from research to shipping — three independent "
           "publishers touched the same stack in one week.")
    pubs3 = ("VentureBeat", "The Register", "arXiv")
    weak = (
        _item(
            10, title="Startup ships an on-device agent runtime SDK",
            source_name="VentureBeat", source_url="https://venturebeat.example/ondevice-runtime",
            source_type="rss", category="tool", tags=("agents", "on-device"),
            relevance=3, strategic_potential=5, hype=1,
            summary="A startup releases an SDK that runs tool-calling agents fully on-device.",
            why_it_matters=why,
            graph_why="edges grew across 3 independent publishers in 6 days", graph_score=0.87,
            convergence=3, contributing_sources=pubs3, published_offset_days=1,
            driver=DRIVER, driver_uid=DRIVER_UID,
        ),
        _item(
            11, title="Two new GitHub repos wrap the same on-device agent runtime",
            source_name="The Register", source_url="https://theregister.example/ondevice-repos",
            source_type="rss", category="tool", tags=("agents", "on-device"),
            relevance=2, strategic_potential=4, hype=1,
            summary="Two repositories appear this week wrapping the same on-device runtime.",
            why_it_matters="Code ships before blog posts — an early convergence indicator.",
            graph_why="same entity, distinct sources", graph_score=0.74,
            convergence=3, contributing_sources=pubs3, published_offset_days=3,
            driver=DRIVER, driver_uid=DRIVER_UID,
        ),
        _item(
            12, title="Preprint benchmarks on-device agents against cloud agents",
            source_name="arXiv", source_url="https://arxiv.example/abs/2606.01234",
            source_type="arxiv", category="research", tags=("agents", "benchmark"),
            relevance=3, strategic_potential=4, hype=0,
            summary="A preprint measures latency/cost of on-device vs cloud tool-calling agents.",
            why_it_matters="Independent academic corroboration of the same shift.",
            graph_why="research node joins the same cluster", graph_score=0.69,
            convergence=3, contributing_sources=pubs3, published_offset_days=5,
            driver=DRIVER, driver_uid=DRIVER_UID,
        ),
    )
    return DigestData(
        period_start=_BASE, period_end=_BASE + timedelta(days=6),
        total_events=5, item_count=3, noise_count=2, graphrag=True,
        weak_signals=weak, referenced_event_ids=(10, 11, 12), noise=_noise_items(),
        weak_driver=DRIVER,
        **_empty_sections(),
    )


# ---- real-corpus proportions (task 010, defects 2 + 3) ------------------------------------------ #

# A source URL the length the real M7.5 corpus actually carries — 160+ characters of slug and
# tracking parameters. The tidy short URLs above fit inside X's 280 by accident, which is why the
# thread items were never length-checked and why the hook starved to `Op…` (D-025). Fixtures have to
# be as ugly as the corpus or they cannot pin the defect.
def _long_url(n: int) -> str:
    return (
        f"https://venturebeat.example/2026/07/{10 + n}/enterprise-agent-orchestration-is-"
        f"consolidating-onto-model-provider-platforms-survey-of-101-enterprises-finds"
        f"?utm_source=ai-verkenner&utm_medium=rss&utm_campaign=weekly-radar-2026-07&item={n}"
    )


def _long_summary(n: int) -> str:
    """A summary the length enrichment really produces (400–800 chars), not a fixture one-liner."""
    return (
        f"A survey of 101 enterprises published this week ({n} of the cluster) finds agent "
        "orchestration consolidating onto model-provider platforms rather than the independent "
        "frameworks that dominated the previous eighteen months, with respondents citing "
        "procurement simplicity, single-vendor support and observability tooling as the deciding "
        "factors; the report separates stated intent from deployed workloads and notes that the "
        "deployed share remains a minority of production traffic, so the consolidation is a "
        "direction of travel rather than an accomplished fact."
    )


def long_form_digest() -> DigestData:
    """A genuine convergence at real-corpus proportions: long summaries **and** long source URLs.

    Same shape as `converging_digest()`, sized like the 2026-07-21 run. Drives the X surface into the
    case that produced 400–800-character thread items beside a carefully-fitted hook.
    """
    weak = tuple(
        _item(
            20 + n,
            title=f"Enterprise agent orchestration consolidates onto model-provider platforms ({n})",
            source_name=("VentureBeat", "The Register", "arXiv")[n],
            source_url=_long_url(n),
            source_type="rss", category="tool", tags=("agents",),
            relevance=3, strategic_potential=4, hype=1,
            summary=_long_summary(n),
            why_it_matters=(
                "If orchestration consolidates onto the model providers, the integration surface a "
                "RAG/graph stack has to track shrinks to a handful of vendor APIs — which changes "
                "what is worth building in-house and what is worth waiting for."
            ),
            graph_why="same entity across distinct publishers", graph_score=0.9 - n / 10,
            convergence=3, contributing_sources=("VentureBeat", "The Register", "arXiv"),
            driver=DRIVER, driver_uid=DRIVER_UID, driver_mentions=4,
            published_offset_days=n + 1,
        )
        for n in range(3)
    )
    return DigestData(
        period_start=_BASE, period_end=_BASE + timedelta(days=6),
        total_events=5, item_count=3, noise_count=2, graphrag=True,
        weak_signals=weak, referenced_event_ids=(20, 21, 22), noise=_noise_items(),
        weak_driver=DRIVER,
        **_empty_sections(),
    )


def noisy_digest(count: int = 40) -> DigestData:
    """`count` demoted items — the 187-demotion shape that produced a 141 KB Medium Noise Report.

    Hype descends across the list so "loudest first" is checkable, and every item carries a long
    title and URL so an uncapped render is genuinely large.
    """
    noise = tuple(
        _item(
            300 + n,
            title=f"Breaking: the {n}th vendor announces the same AI copilot, this time for slides",
            source_name=f"HypeDaily{n}", source_url=_long_url(100 + n),
            priority_class="archive" if n % 3 == 0 else "operational_update",
            category="marketing", tags=("marketing",),
            relevance=1, novelty=1, actionability=1, strategic_potential=1,
            hype=5 if n < count // 2 else 4,
            summary=_long_summary(n),
            is_weak_signal=False, horizon=None,
        )
        for n in range(count)
    )
    return DigestData(
        period_start=_BASE, period_end=_BASE + timedelta(days=6),
        total_events=count + 3, item_count=3, noise_count=count, graphrag=True,
        weak_signals=converging_digest().weak_signals, referenced_event_ids=(10, 11, 12),
        noise=noise, weak_driver=DRIVER,
        **_empty_sections(),
    )

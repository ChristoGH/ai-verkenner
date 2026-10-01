"""Task 016 — an item counts toward a driver's cluster only if the driver is substantively present.

The defect (D-036, D-052, and the original 8-item "LLM" cluster): the convergence read counts
MENTIONS, all weighted equally, so a piece whose headline is the driver and a retrospective that
name-checks it once contributed the same amount to a cluster **and to the "N independent sources"
claim printed on the draft** — the load-bearing claim of the entire Weak Signal piece.

The two real cases are pinned here **by name and with their real text**, taken from
`data/dev_corpus.db` over the 2026-07-14 → 07-21 window, so neither regression can return:

- **NextBSD** (event 96, The Register, D-052) — names `Claude Code` once, in the last twelve
  characters of an 84-character feed blurb, and its headline is about FreeBSD. A passing mention.
- **Mozilla / Firefox** (event 92, The Register, D-036) — names `Firefox` in its **headline**. It is
  substantively about Firefox and mention weight correctly keeps it. What that item lacks is AI
  content, which is a **topicality** question (task 016 non-goals; corpus scope, task 011) — see
  `test_mozilla_item_is_substantive_and_mention_weight_will_not_exclude_it` for the finding.

Offline and deterministic: the weights come from the real `scoring.mention_weight` function, never
hand-set, so these tests exercise the shipped path.
"""

from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.api import dashboard_service
from app.core.config import settings
from app.digests.sections import build_items, build_sections, cluster_sources, coherent_cluster
from app.graph import InMemoryGraph, project_new_events
from app.models import EnrichedItem, RawItem, Relationship
from app.posts import PIECE_WEAK_SIGNAL, SURFACE_LINKEDIN, SURFACE_X, generate_posts
from app.scoring.mention_weight import (
    LEAD_CHARS,
    WEIGHT_ABSENT,
    WEIGHT_LEAD,
    WEIGHT_PASSING,
    WEIGHT_REPEATED,
    WEIGHT_TITLE,
    mention_weight,
)
from tests import graph_helpers as gh
from tests.posts_fixtures import _item

from .test_cluster_coherence import _sections

# ---- the real corpus text these regressions are pinned to (dev_corpus.db, 2026-07-14 → 07-21) ----

# Event 96 — The Register. The full feed blurb, verbatim: 84 characters, one mention, at the end.
NEXTBSD_TITLE = "NextBSD returns to dollop Apple source on FreeBSD"
NEXTBSD_BODY = "New maintainer revives the project with Darwin components, Gershwin, and Claude Code"

# Event 100 — Simon Willison's Weblog. Headline names the driver; the body sustains it. (Excerpt.)
BUN_TITLE = "Claude Code uses Bun written in Rust now"
BUN_BODY = (
    "<p>In <a href='https://bun.com/blog/bun-in-rust'>Rewriting Bun in Rust</a> Jarred Sumner made "
    "the following claim: Claude Code v2.1.181 (released June 17th) and later use the Rust port of "
    "Bun.</p><p>I decided to have a poke at my own Claude Code installation to see if I could "
    "confirm this.</p>"
)

# Event 45 — Simon Willison's Weblog. The cluster's third item: one mention, body-only, 72% in.
# D-052 read it as substantive; the item's own text says otherwise, which is why the weight is
# measured rather than judged. (Excerpt preserving the shape: one late mention in a longer body.)
MERMAID_TITLE = "Mermaid to Unicode box art (grok-mermaid)"
MERMAID_BODY = (
    "<p><strong>Tool:</strong> Mermaid to Unicode box art (grok-mermaid)</p><p>While exploring the "
    "codebase for the newly open-sourced Grok CLI coding agent I came across a self-contained Rust "
    "implementation of a Mermaid diagram renderer that outputs Unicode box art. I extracted it and "
    "compiled it to WebAssembly so it can run in a browser, wiring up the page around it. "
    "The whole thing came together from a single prompt run in Claude Code for web.</p>"
)

# Event 92 — The Register, the D-036 Firefox case. Verbatim blurb; the driver is in the headline.
MOZILLA_TITLE = "Mozilla speeds Firefox release schedule to biweekly"
MOZILLA_BODY = "And what to expect in Firefox 153 as the next ESR release gets close"

_PUBS = ("Simon Willison's Weblog", "The Register", "arXiv cs.AI (Artificial Intelligence)")
_WEAK_SURFACES = (SURFACE_X, SURFACE_LINKEDIN)


def _weighed(event_id, *, title, body, source_name, driver, driver_uid, mentions=5,
             pubs=_PUBS, graph_score=0.5):
    """A horizon item whose driver weight is **computed by the shipped function** from its own text.

    Never hand-set: if `mention_weight` stops separating substantive from passing, these tests must
    fail rather than keep asserting a constant somebody typed in.
    """
    weight = mention_weight(driver, title=title, body=body)
    return _item(
        event_id,
        title=title,
        source_name=source_name,
        source_url=f"https://pub{event_id}.example/item{event_id}",
        priority_class="horizon_signal",
        summary=f"Source fact {event_id}.",
        why_it_matters=f"Interpretation of item {event_id}.",
        graph_score=graph_score,
        convergence=len(pubs),
        contributing_sources=pubs,
        coverage_sources=(source_name,),
        driver=driver,
        driver_uid=driver_uid,
        driver_mentions=mentions,
        driver_weight=weight.weight,
        driver_weight_why=weight.why,
    )


def _one(bundle, surface, piece=PIECE_WEAK_SIGNAL):
    return next(d for d in bundle.drafts if d.surface == surface and d.piece == piece)


# ---- the weight function itself ----


def test_weight_bands_separate_presence_from_reference():
    """Title > repeated > lead > named-once-in-passing > absent, and the floor sits between."""
    long_body = "filler. " * 60                                   # comfortably past LEAD_CHARS
    assert len(long_body) > LEAD_CHARS

    assert mention_weight("Qdrant", title="Qdrant ships 1.19", body="x").weight == WEIGHT_TITLE
    assert mention_weight(
        "Qdrant", title="A vector store update", body="Qdrant did this. Later, Qdrant did that."
    ).weight == WEIGHT_REPEATED
    assert mention_weight(
        "Qdrant", title="A vector store update", body="Qdrant leads this piece. " + long_body
    ).weight == WEIGHT_LEAD
    assert mention_weight(
        "Qdrant", title="A vector store update", body=long_body + " Built on Qdrant."
    ).weight == WEIGHT_PASSING
    assert mention_weight(
        "Qdrant", title="A vector store update", body="No mention here."
    ).weight == WEIGHT_ABSENT

    # The shipped floor separates presence from a passing reference and lands on no band.
    assert WEIGHT_PASSING < settings.cluster_member_min_weight < WEIGHT_LEAD


def test_matching_is_separator_tolerant_case_insensitive_and_word_bounded():
    """"claude-code" is "Claude Code"; "OpenAI" is not a mention of "AI"."""
    assert mention_weight(
        "Claude Code", title="Shipping with claude-code today", body=""
    ).weight == WEIGHT_TITLE
    assert mention_weight(
        "Claude Code", title="untitled", body="CLAUDE CODE ran it. claude_code ran it again."
    ).weight == WEIGHT_REPEATED

    # Word boundaries: a substring hit would make every "OpenAI" story an "AI" story.
    assert mention_weight("AI", title="OpenAI ships something", body="OpenAI again").weight == 0.0
    assert mention_weight("Claude", title="Claudette writes code", body="Claudette").weight == 0.0

    # An empty / whitespace driver is not a mention of anything.
    assert mention_weight("", title="anything", body="anything").weight == WEIGHT_ABSENT
    assert mention_weight("   ", title="anything", body="anything").weight == WEIGHT_ABSENT


def test_markup_is_stripped_before_counting():
    """Feed bodies are HTML; a mention inside a link must count once, and tags must not."""
    body = "<p>Built with <a href='https://claude.example/code'>Claude Code</a>.</p>"
    result = mention_weight("Claude Code", title="A tool", body=body)
    assert result.count == 1
    assert result.weight == WEIGHT_PASSING


def test_a_short_blurb_has_no_lead_to_be_named_in():
    """The Register's 84-character teaser is all "lead" by position — and must not qualify on it."""
    assert len(NEXTBSD_BODY) < LEAD_CHARS
    result = mention_weight("Claude Code", title=NEXTBSD_TITLE, body=NEXTBSD_BODY)
    assert result.weight == WEIGHT_PASSING, (
        "a syndication blurb was scored as a lead — every one-line feed becomes substantive"
    )


# ---- membership: a passing mention does not join the cluster ----


def test_passing_mention_excluded_from_cluster():
    """D-052's NextBSD item, by name: it names `Claude Code` once and is not a cluster member."""
    substantive = [
        _weighed(100, title=BUN_TITLE, body=BUN_BODY, source_name="Simon Willison's Weblog",
                 driver="Claude Code", driver_uid=258),
        _weighed(101, title="Claude Code adds a subagent API", body="Details follow.",
                 source_name="arXiv cs.AI (Artificial Intelligence)",
                 driver="Claude Code", driver_uid=258),
        _weighed(102, title="A week of Claude Code changes", body="Claude Code shipped twice.",
                 source_name="Hacker News (front page)", driver="Claude Code", driver_uid=258),
    ]
    nextbsd = _weighed(96, title=NEXTBSD_TITLE, body=NEXTBSD_BODY, source_name="The Register",
                       driver="Claude Code", driver_uid=258)
    assert nextbsd.driver_weight == WEIGHT_PASSING
    assert nextbsd.driver_weight < settings.cluster_member_min_weight

    cluster, driver = coherent_cluster([*substantive, nextbsd], min_items=3, min_sources=3)
    assert driver == "Claude Code"
    assert 96 not in {it.event_id for it in cluster}, (
        "the NextBSD passing mention is back in the Claude Code cluster (D-052)"
    )
    assert {it.event_id for it in cluster} == {100, 101, 102}


def test_substantive_mention_included():
    """Title presence, a repeated body mention and a lead mention all qualify; only 1-in-passing doesn't."""
    long_tail = " filler." * 60
    cases = {
        # event_id: (title, body)
        1: (BUN_TITLE, BUN_BODY),                                        # named in the title
        2: ("A tool ships", "Claude Code did this. Claude Code did that."),   # repeated in the body
        3: ("A tool ships", "Claude Code opens the piece." + long_tail),      # named in the lead
    }
    items = [
        _weighed(eid, title=t, body=b, source_name=_PUBS[eid % len(_PUBS)],
                 driver="Claude Code", driver_uid=258)
        for eid, (t, b) in cases.items()
    ]
    assert [it.driver_weight for it in items] == [WEIGHT_TITLE, WEIGHT_REPEATED, WEIGHT_LEAD]

    cluster, driver = coherent_cluster(items, min_items=3, min_sources=3)
    assert driver == "Claude Code"
    assert {it.event_id for it in cluster} == {1, 2, 3}


def test_mozilla_item_is_substantive_and_mention_weight_will_not_exclude_it():
    """D-036's Mozilla item, by name — and the finding that it is NOT a mention-weight defect.

    Task 016's acceptance criteria ask for this item to stop counting toward `Firefox`. Measured on
    its real text it is **strongly** about Firefox: the driver is in its headline. What the item
    lacks is AI content, which is a TOPICALITY question — explicitly a task 016 non-goal, and
    diagnosed by D-036 itself as corpus scope (task 011). Excluding it here would require a
    topicality gate smuggled in under a mention-weight name.

    This test pins the measurement so the disagreement stays visible instead of being quietly
    engineered away in a later change.
    """
    mozilla = mention_weight("Firefox", title=MOZILLA_TITLE, body=MOZILLA_BODY)
    assert mozilla.weight == WEIGHT_TITLE
    assert mozilla.weight >= settings.cluster_member_min_weight

    # And its cluster partner — the genuinely AI-relevant one — is substantive too, so weighting
    # leaves the D-036 pair exactly as task 013's floor already left it: excluded on the FLOOR
    # (2 items / 2 sources), never on mention weight.
    wasm = mention_weight(
        "Firefox", title="Firefox in WebAssembly",
        body="Puter compiled Firefox to WebAssembly such that the whole browser runs in a browser.",
    )
    assert wasm.weight == WEIGHT_TITLE

    pair = [
        _weighed(92, title=MOZILLA_TITLE, body=MOZILLA_BODY, source_name="The Register",
                 driver="Firefox", driver_uid=561, mentions=2, pubs=_PUBS[:2]),
        _weighed(67, title="Firefox in WebAssembly", body="Firefox runs in Firefox.",
                 source_name="Simon Willison's Weblog", driver="Firefox", driver_uid=561,
                 mentions=2, pubs=_PUBS[:2]),
    ]
    assert all(it.driver_weight >= settings.cluster_member_min_weight for it in pair)
    assert coherent_cluster(pair, min_items=3, min_sources=3) == ((), "")


# ---- the published claim is computed after weighting ----


def test_source_count_computed_after_weighting():
    """"N independent sources" counts only the sources that substantively covered the driver."""
    substantive = [
        _weighed(1, title="Claude Code ships a Rust runtime", body=BUN_BODY,
                 source_name="Simon Willison's Weblog", driver="Claude Code", driver_uid=258),
        _weighed(2, title="Claude Code adds a subagent API", body="More on Claude Code.",
                 source_name="Hacker News (front page)", driver="Claude Code", driver_uid=258),
        _weighed(3, title="Claude Code in production", body="Claude Code again.",
                 source_name="arXiv cs.AI (Artificial Intelligence)",
                 driver="Claude Code", driver_uid=258),
    ]
    passing = _weighed(96, title=NEXTBSD_TITLE, body=NEXTBSD_BODY, source_name="The Register",
                       driver="Claude Code", driver_uid=258)

    before = cluster_sources([*substantive, passing])
    cluster, driver = coherent_cluster([*substantive, passing], min_items=3, min_sources=3)
    after = cluster_sources(cluster)
    assert "The Register" in before and len(before) == 4
    assert "The Register" not in after and len(after) == 3, (
        "a publisher that only mentioned the driver in passing still backs the published claim"
    )

    # End to end: the number printed on the drafts is the post-weighting one.
    data = _sections([*substantive, passing])
    assert data.weak_driver == "Claude Code"
    bundle = generate_posts(data)
    assert bundle.has_convergence is True
    for surface in _WEAK_SURFACES:
        text = _one(bundle, surface).text
        assert "3 independent sources" in text, f"{surface} did not recount after weighting"
        assert "4 independent sources" not in text, f"{surface} still counts the passing mention"
    # URL invariant on the surviving members.
    for it in cluster:
        assert it.source_url in _one(bundle, SURFACE_X).text


def test_weighting_can_drop_cluster_below_floor():
    """The real 2026-07-21 trio: one substantive item and two passing ones → honest degradation.

    A smaller true claim beats a larger inflated one. Nothing here may be widened to keep the
    cluster alive — the correct output is the quiet-week draft.
    """
    trio = [
        _weighed(100, title=BUN_TITLE, body=BUN_BODY, source_name="Simon Willison's Weblog",
                 driver="Claude Code", driver_uid=258),
        _weighed(45, title=MERMAID_TITLE, body=MERMAID_BODY,
                 source_name="Simon Willison's Weblog", driver="Claude Code", driver_uid=258),
        _weighed(96, title=NEXTBSD_TITLE, body=NEXTBSD_BODY, source_name="The Register",
                 driver="Claude Code", driver_uid=258),
    ]
    assert [it.driver_weight for it in trio] == [WEIGHT_TITLE, WEIGHT_PASSING, WEIGHT_PASSING]

    # Unweighted this group cleared the floor (3 items); weighted it is one item and does not.
    assert len(trio) >= settings.weak_cluster_min_items
    assert coherent_cluster(trio, min_items=3, min_sources=3) == ((), "")

    data = _sections(trio)
    assert data.weak_driver == ""
    bundle = generate_posts(data)
    assert bundle.has_convergence is False
    for surface in _WEAK_SURFACES:
        draft = _one(bundle, surface)
        low = draft.text.lower()
        assert "converging" not in low, f"{surface} claims convergence over one substantive item"
        assert "independent sources" not in low, f"{surface} still prints a source count"
        assert "quiet" in low, f"{surface} lost the honest quiet-week framing"
        assert draft.source_urls
        for url in draft.source_urls:
            assert url in draft.text, f"{surface} dropped a source URL while degrading"


def test_unmeasured_items_are_never_silently_dropped():
    """A `DigestItem` built outside `build_items` defaults to substantive — filters must not eat it."""
    hand_built = _item(
        7, title="Hand-built", source_name="src", source_url="https://x.example/7",
        convergence=3, contributing_sources=_PUBS, coverage_sources=_PUBS,
        driver="Some Entity", driver_uid=77,
    )
    assert hand_built.driver_weight >= settings.cluster_member_min_weight
    cluster, driver = coherent_cluster([hand_built] * 1 + [
        _item(8 + i, title="Hand-built", source_name=_PUBS[i], source_url=f"https://x.example/{i}",
              convergence=3, contributing_sources=_PUBS, coverage_sources=_PUBS,
              driver="Some Entity", driver_uid=77)
        for i in range(2)
    ], min_items=3, min_sources=3)
    assert driver == "Some Entity" and len(cluster) == 3


# ---- exclusion is membership-only: nothing leaves the corpus or the graph ----


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _seed_claude_code(session):
    """Three substantive `Claude Code` developments + the NextBSD passing mention, in SQLite.

    Four unrelated developments are seeded alongside them so the IDF denominator is larger than the
    driver's own span — an entity present in *every* development is a hub and `graph_signals` floors
    its contribution to zero (M5.5), which would leave these items with no driver to weigh.
    """
    sources = [gh.add_source(session, name) for name in ("willison", "hackernews", "arxiv", "reg")]
    driver = gh.add_entity(session, "Claude Code", "tool")

    for i in range(4):
        other = gh.add_entity(session, f"Unrelated{i}", "tool")
        ev = gh.add_event(session, f"Unrelated development {i}")
        item = gh.add_item(session, sources[i % len(sources)], ev,
                           title=f"Unrelated development {i}", url=f"https://other/{i}")
        gh.add_relationship(session, other, "relates_to", other, event=ev, item=item)
        gh.add_enriched(session, ev, item, priority_class="archive")

    seeded = [
        ("Claude Code uses Bun written in Rust now", BUN_BODY, sources[0]),
        ("Claude Code adds a subagent API", "More detail on Claude Code follows.", sources[1]),
        ("Claude Code in production", "Claude Code again, and Claude Code once more.", sources[2]),
        (NEXTBSD_TITLE, NEXTBSD_BODY, sources[3]),
    ]
    events = []
    for i, (title, body, src) in enumerate(seeded):
        ev = gh.add_event(session, title)
        item = gh.add_item(session, src, ev, title=title, url=f"https://{src.name}/i{i}",
                           summary=body)
        partner = gh.add_entity(session, f"Partner{i}", "tool")
        gh.add_relationship(session, driver, "used_by", partner, event=ev, item=item)
        gh.add_enriched(session, ev, item, priority_class="horizon_signal", tags=["claude-code"],
                        relevance=1, novelty=3, actionability=2, strategic_potential=4, hype=1)
        events.append(ev)
    return events


def test_excluded_item_remains_in_corpus_and_graph(session):
    """The NextBSD item leaves the CLUSTER and nothing else: corpus row, edges and graph intact."""
    events = _seed_claude_code(session)
    nextbsd = events[-1]

    store = InMemoryGraph()
    project_new_events(session, store, session.exec(select(RawItem)).all())
    rows = list(session.exec(select(EnrichedItem)).all())
    signals = dashboard_service.compute_signals(session, store, rows)
    items = build_items(session, rows, signals)
    data = build_sections(items, signals, high_hype=4, section_limit=8, graphrag=True,
                          period_start=None, period_end=None)

    # It is excluded from the cluster …
    assert data.weak_driver == "Claude Code"
    assert nextbsd.id not in {it.event_id for it in data.weak_signals}
    excluded = next(it for it in items if it.event_id == nextbsd.id)
    assert excluded.driver_weight == WEIGHT_PASSING
    assert "named once" in excluded.driver_weight_why

    # … and present everywhere else. The corpus row and its URL:
    raw = session.exec(select(RawItem).where(RawItem.event_id == nextbsd.id)).first()
    assert raw is not None and raw.url.startswith("https://")
    assert session.exec(
        select(EnrichedItem).where(EnrichedItem.event_id == nextbsd.id)
    ).first() is not None
    # Its graph edges:
    assert session.exec(
        select(Relationship).where(Relationship.event_id == nextbsd.id)
    ).all()
    # And the projected graph still counts it toward the driver's convergence — weighting is a
    # membership filter, not a scoring or graph change.
    stats = {st.entity_uid: st for st in store.convergence(None)}
    assert stats[excluded.driver_uid].event_count == len(events), (
        "the excluded item was removed from the graph's convergence read"
    )
    # It is still in the period corpus alongside every other item.
    assert data.total_events == len(items)
    assert excluded in items


def test_weighting_does_not_touch_convergence_scoring(session):
    """`GraphSignal` is computed before any weight exists and is provably unchanged by it."""
    events = _seed_claude_code(session)
    store = InMemoryGraph()
    project_new_events(session, store, session.exec(select(RawItem)).all())
    rows = list(session.exec(select(EnrichedItem)).all())
    signals = dashboard_service.compute_signals(session, store, rows)

    passing = signals[events[-1].id]
    substantive = signals[events[0].id]
    assert passing.driver == substantive.driver == "Claude Code"
    assert passing.convergence == substantive.convergence, (
        "the passing item's own convergence score moved — this must be membership-only"
    )
    assert passing.score > 0.0
    assert settings.graph_min_sources == 2, "GRAPH_MIN_SOURCES was moved; task 016 forbids it"

"""Shared SQLite row builders for the M5 graph tests (model rows, not Pydantic schemas)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session

from app.models import EnrichedItem, Entity, Event, RawItem, Relationship, Source

TS = datetime(2026, 6, 18, tzinfo=timezone.utc)


def add_source(session: Session, name: str) -> Source:
    src = Source(name=name, source_type="rss", url=f"https://{name}.example/feed",
                 trust_level="high")
    session.add(src)
    session.commit()
    session.refresh(src)
    return src


def add_event(session: Session, title: str) -> Event:
    ev = Event(title=title)
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


def add_item(session: Session, source: Source, event: Event, *, title: str, url: str,
             published=TS) -> RawItem:
    item = RawItem(
        source_id=source.id, source_name=source.name, source_type=source.source_type,
        title=title, url=url, summary=title, dedup_key=url, content_hash="h:" + url,
        event_id=event.id, published_at=published,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    if event.representative_item_id is None:
        event.representative_item_id = item.id
        session.add(event)
        session.commit()
    return item


def add_entity(session: Session, name: str, type_: str) -> Entity:
    e = Entity(name=name, normalised_name=name.strip().lower(), type=type_)
    session.add(e)
    session.commit()
    session.refresh(e)
    return e


def add_relationship(session: Session, subject: Entity, predicate: str, obj: Entity,
                     *, event: Event, item: RawItem, ts=TS) -> Relationship:
    rel = Relationship(
        subject_entity_id=subject.id, predicate=predicate, object_entity_id=obj.id,
        ts=ts, event_id=event.id, raw_item_id=item.id,
    )
    session.add(rel)
    session.commit()
    session.refresh(rel)
    return rel


def add_enriched(session: Session, event: Event, item: RawItem, *, priority_class: str,
                 tags=None, relevance=3, novelty=3, actionability=3, strategic_potential=3,
                 hype=1) -> EnrichedItem:
    ei = EnrichedItem(
        event_id=event.id, raw_item_id=item.id, source_url=item.url, category="tool",
        tags=tags or [], relevance=relevance, novelty=novelty, actionability=actionability,
        strategic_potential=strategic_potential, hype=hype, summary="fact",
        why_it_matters="", connection_to_user_work="", recommended_action="",
        priority_class=priority_class, method="llm",
    )
    session.add(ei)
    session.commit()
    session.refresh(ei)
    return ei

"""Entity alias resolution — one concept, one uid (task 014).

Enrichment extracts whatever surface form a publisher used, so the same thing arrives as several
`Entity` rows: `AI` / `LLM` / `LLMs` / `Large language models`, or `OpenAI` / `Open AI`. D-024
measured five uids for one concept in a single week's horizon quadrant. That inflates driver counts
and — the damaging half — **fragments genuine clusters below `WEAK_CLUSTER_MIN_ITEMS`, so real
signals are missed**: a false-negative generator in an early-warning product.

This module resolves those surface forms to one canonical identity using an **explicit, curated,
human-editable map** (`sources/entity_aliases.yaml`). There is deliberately no fuzzy matching, no
embedding similarity and no learned entity resolution — an unlisted form stays its own entity.

Two invariants shape the design:

* **SQLite is untouched** (ADR 0001). Resolution happens at *graph projection* time; every extracted
  row survives exactly as enrichment wrote it, and `graph-reindex` rebuilds the normalised graph
  from SQLite alone.
* **The canonical uid is a real `Entity.id`**, so everything downstream that maps a uid back to a
  row — `graph_signals`, the dashboard, the digest's `driver_uid` grouping — keeps working without
  a parallel identity space.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml
from sqlmodel import Session, select

from app.models import Entity
from app.schemas.enrichment import normalise_entity_name

logger = logging.getLogger(__name__)


def _fold(name: str) -> str:
    """The lookup key: the normalised name, with a conservative trailing-`s` fold.

    `LLMs` → `llm` finds a map entry listed only in the singular. The fold is applied **only when
    matching against the map** — two unlisted entities are never merged because one happens to be
    the other's plural.
    """
    key = normalise_entity_name(name)
    return key[:-1] if len(key) > 3 and key.endswith("s") else key


@dataclass(frozen=True)
class AliasMap:
    """Curated surface-form → canonical-display-name map. Empty means "normalise nothing"."""

    canonical_by_key: dict[str, str]

    @property
    def is_empty(self) -> bool:
        return not self.canonical_by_key

    def canonical_name(self, name: str) -> str:
        """The canonical display name for a surface form, or the name unchanged if unmapped."""
        return self.canonical_by_key.get(_fold(name), name)

    def canonical_key(self, name: str) -> str:
        """The normalised identity a surface form resolves to (its own, when unmapped)."""
        return normalise_entity_name(self.canonical_name(name))

    def is_mapped(self, name: str) -> bool:
        return _fold(name) in self.canonical_by_key


_EMPTY = AliasMap(canonical_by_key={})


def load_alias_map(path: Path | None = None) -> AliasMap:
    """Load the alias YAML. A missing or malformed file degrades to "no normalisation", loudly.

    Fail-safe, like the source registry: a broken alias file must never stop a run from projecting
    the graph — it just means nothing is merged, which is the pre-task-014 behaviour.
    """
    if path is None:
        from app.core.config import settings

        path = settings.entity_aliases_file
    if not Path(path).exists():
        logger.warning("entity alias file not found at %s; no entity normalisation applied", path)
        return _EMPTY
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        raw = data.get("aliases") or {}
    except (yaml.YAMLError, OSError) as exc:  # noqa: BLE001 — degrade, never crash a run
        logger.warning("entity alias file %s is unreadable (%s); no normalisation applied", path,
                       exc)
        return _EMPTY

    mapping: dict[str, str] = {}
    for canonical, surface_forms in raw.items():
        canonical = str(canonical).strip()
        if not canonical:
            continue
        # The canonical form maps to itself, so every member of a family shares one key.
        for form in [canonical, *(surface_forms or [])]:
            key = _fold(str(form))
            if not key:
                continue
            if key in mapping and mapping[key] != canonical:
                logger.warning(
                    "alias %r is claimed by both %r and %r; keeping %r",
                    form, mapping[key], canonical, mapping[key],
                )
                continue
            mapping[key] = canonical
    return AliasMap(canonical_by_key=mapping)


class EntityResolver:
    """Maps `Entity.id` → the canonical `Entity.id` for its alias family, for one projection run.

    The canonical row is chosen deterministically: the row whose normalised name *is* the canonical
    form if one exists, else the lowest id in the family. Ids are monotonic, so a later-extracted
    alias never re-points an existing family — resolution is stable across reindexes.
    """

    def __init__(self, session: Session, alias_map: AliasMap | None = None) -> None:
        self.alias_map = load_alias_map() if alias_map is None else alias_map
        self._canonical_id: dict[int, int] = {}
        self._display: dict[int, str] = {}
        if not self.alias_map.is_empty:
            self._build(session)

    def _build(self, session: Session) -> None:
        rows = session.exec(select(Entity).order_by(Entity.id)).all()
        families: dict[str, list[Entity]] = {}
        for row in rows:
            if self.alias_map.is_mapped(row.name) or self.alias_map.is_mapped(row.normalised_name):
                families.setdefault(self.alias_map.canonical_key(row.name), []).append(row)

        for key, members in families.items():
            winner = min(members, key=lambda e: (e.normalised_name != key, e.id))
            canonical_name = self.alias_map.canonical_name(members[0].name)
            for member in members:
                self._canonical_id[member.id] = winner.id
                self._display[member.id] = canonical_name

    def resolve(self, entity_id: int) -> int:
        """The canonical uid for an entity id — itself when the entity is not in the map."""
        return self._canonical_id.get(entity_id, entity_id)

    def resolve_all(self, entity_ids) -> set[int]:
        return {self.resolve(eid) for eid in entity_ids}

    def display_name(self, entity_id: int, fallback: str) -> str:
        """The canonical display name for an entity id, or `fallback` when it is not in the map."""
        return self._display.get(entity_id, fallback)

    @property
    def merged_count(self) -> int:
        """How many entity rows resolve to a uid other than their own (for run reporting)."""
        return sum(1 for eid, cid in self._canonical_id.items() if eid != cid)

"""Pydantic shapes for LLM enrichment + extraction output (M4).

These validate and repair the model's JSON before it ever touches SQLite. Scores are constrained
to 0–5, entity types to a known set, and the entity/relationship payload is capped/validated so
extraction noise can't sprawl into the graph.

The five-axis polarity is the brief's: relevance/novelty/actionability/strategic_potential run
higher = more salient; **hype is inverted** (0 = signal, 5 = noise). Priority class is NOT computed
here — `app/scoring/priority.compute_priority_class` owns that rule.
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

_WS_RE = re.compile(r"\s+")


def normalise_entity_name(name: str) -> str:
    """The Phase-1 entity-resolution key: lowercase, trim, collapse internal whitespace.

    So "OpenAI", "openai ", and "Open AI" → "openai" / "open ai" deterministically. Deliberately
    basic (no fuzzy/embedding merge — that is Phase 2).
    """
    return _WS_RE.sub(" ", name.strip().lower())


class EntityType(str, Enum):
    """The constrained set of entity types (keeps extraction from inventing categories)."""

    org = "org"
    model = "model"
    person = "person"
    tool = "tool"
    concept = "concept"


class Scores(BaseModel):
    """The five scores, each an integer 0–5. hype is inverted (0 = signal, 5 = noise)."""

    model_config = ConfigDict(extra="ignore")

    relevance: int
    novelty: int
    actionability: int
    strategic_potential: int
    hype: int

    @field_validator("relevance", "novelty", "actionability", "strategic_potential", "hype")
    @classmethod
    def _in_range(cls, value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("score must be an integer")
        if value < 0 or value > 5:
            raise ValueError("score must be within 0..5")
        return value


class ClassifyResult(BaseModel):
    """Output of the classifier prompt."""

    model_config = ConfigDict(extra="ignore")

    category: str = "uncategorised"
    tags: list[str] = Field(default_factory=list)
    scores: Scores

    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(t).strip() for t in value if str(t).strip()]
        return []


class SummariseResult(BaseModel):
    """Output of the summariser prompt. Fact (summary) is kept separate from interpretation."""

    model_config = ConfigDict(extra="ignore")

    summary: str
    why_it_matters: str = ""
    connection_to_user_work: str = ""
    recommended_action: str = ""


class WeakSignalResult(BaseModel):
    """Output of the weak-signal prompt (optional lane)."""

    model_config = ConfigDict(extra="ignore")

    is_weak_signal: bool = False
    horizon: str | None = None
    rationale: str = ""
    what_to_watch: str = ""

    @field_validator("horizon")
    @classmethod
    def _known_horizon(cls, value: str | None) -> str | None:
        if value is None:
            return None
        v = value.strip().lower()
        return v if v in {"near", "mid", "far"} else None


class EntityIn(BaseModel):
    """One extracted entity (pre-persistence)."""

    model_config = ConfigDict(extra="ignore")

    name: str
    type: EntityType

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("entity name must not be blank")
        return value.strip()


class RelationshipIn(BaseModel):
    """One extracted relationship triple (subject/predicate/object as entity names)."""

    model_config = ConfigDict(extra="ignore")

    subject: str
    predicate: str
    object: str

    @field_validator("subject", "predicate", "object")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("relationship fields must not be blank")
        return value.strip()


class GraphExtractResult(BaseModel):
    """Output of the graph-extraction prompt: entities + timestamped relationship triples."""

    model_config = ConfigDict(extra="ignore")

    entities: list[EntityIn] = Field(default_factory=list)
    relationships: list[RelationshipIn] = Field(default_factory=list)

"""The `Source` registry model.

A `Source` is one curated entry in `sources/sources.yaml`. The registry is a hand-maintained,
human-curated pipeline — never a crawler (see CLAUDE.md). This is the validation gate: a bad
entry must be reported clearly, not silently dropped or allowed to crash a run.

`source_type` is constrained to the known set, which includes the curated GitHub-intelligence
types sanctioned by ADR 0002. At M1 the GitHub-intelligence fetchers are stubs (M3); the registry
still validates their entries so `sources.yaml` can declare them now.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class SourceType(str, Enum):
    """The known source types. Adding one here is a deliberate editorial act."""

    # Implemented in M1.
    rss = "rss"
    github_releases = "github_releases"
    arxiv = "arxiv"

    # Curated GitHub-intelligence types (ADR 0002). Registered at M1; fetchers land in M3.
    github_star_velocity = "github_star_velocity"
    github_new_repos = "github_new_repos"
    github_advisories = "github_advisories"
    github_changes = "github_changes"


class TrustLevel(str, Enum):
    """Editorial trust in a source. Used later as a ranking input, not a filter."""

    high = "high"
    medium = "medium"
    low = "low"


class Source(BaseModel):
    """One curated source. URLs are preserved verbatim (core invariant)."""

    # Reject unknown keys so a typo'd field surfaces as a validation error, not a silent drop.
    model_config = ConfigDict(extra="forbid")

    name: str
    source_type: SourceType
    url: str
    repo_owner: str | None = None
    repo_name: str | None = None
    arxiv_query: str | None = None
    enabled: bool = True
    trust_level: TrustLevel

    @field_validator("name", "url")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def _check_type_specific_fields(self) -> Source:
        """Enforce the fields each source type needs to be fetchable.

        Kept minimal: only the M1 fetchers (github_releases, arxiv) have hard requirements. The
        GitHub-intelligence types are driven by watched orgs/users/topics whose required fields
        are defined when their fetchers land (M3); they are not constrained here.
        """
        if self.source_type is SourceType.github_releases:
            if not self.repo_owner or not self.repo_name:
                raise ValueError(
                    "github_releases requires both 'repo_owner' and 'repo_name'"
                )
        if self.source_type is SourceType.arxiv and not self.arxiv_query:
            raise ValueError("arxiv requires 'arxiv_query'")
        return self

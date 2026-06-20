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

    # Curated GitHub-intelligence types (ADR 0002). Registered at M1; fetchers implemented in M6.5.
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
    # Curated GitHub-intelligence targets (ADR 0002) — watched topic / package / issue-label.
    github_topic: str | None = None       # github_new_repos / github_star_velocity by topic
    github_ecosystem: str | None = None   # github_advisories: pip | npm | ... (default pip)
    github_package: str | None = None     # github_advisories: package in the user's stack
    github_label: str | None = None       # github_changes: issue/PR label (default breaking-change)
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
        """Enforce the fields each source type needs to be fetchable (curated targets, ADR 0002)."""
        if self.source_type is SourceType.github_releases:
            if not self.repo_owner or not self.repo_name:
                raise ValueError("github_releases requires both 'repo_owner' and 'repo_name'")
        if self.source_type is SourceType.arxiv and not self.arxiv_query:
            raise ValueError("arxiv requires 'arxiv_query'")
        # github_new_repos: a watched org/user (repo_owner) OR a watched topic.
        if self.source_type is SourceType.github_new_repos:
            if not self.repo_owner and not self.github_topic:
                raise ValueError("github_new_repos requires 'repo_owner' or 'github_topic'")
        # github_star_velocity: a watched topic OR a specific repo (repo_owner + repo_name).
        if self.source_type is SourceType.github_star_velocity:
            if not self.github_topic and not (self.repo_owner and self.repo_name):
                raise ValueError(
                    "github_star_velocity requires 'github_topic' or 'repo_owner'+'repo_name'"
                )
        # github_advisories: a watched package (in the user's stack), with an ecosystem.
        if self.source_type is SourceType.github_advisories:
            if not self.github_package and not (self.repo_owner and self.repo_name):
                raise ValueError(
                    "github_advisories requires 'github_package' or 'repo_owner'+'repo_name'"
                )
        # github_changes: a watched repo to scan for breaking-change/deprecation issues.
        if self.source_type is SourceType.github_changes:
            if not self.repo_owner or not self.repo_name:
                raise ValueError("github_changes requires both 'repo_owner' and 'repo_name'")
        return self

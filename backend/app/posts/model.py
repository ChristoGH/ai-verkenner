"""Data contract for the M7.5 post generator — the draft objects and the shared constants.

A `Draft` is one publishable-but-unpublished piece of text for one surface (X / LinkedIn / Medium).
A `PostBundle` is everything a single `posts` run produces: the two pieces (Weak Signal of the Week +
Noise Report) across the three surfaces, plus the metadata the writers need.

Draft-only by construction: nothing here knows how to *post*. There are no clients, tokens, or
network calls anywhere in `app.posts` — publishing is a deliberate human action (see task 009 and
docs/SIGNATURE_OUTPUTS.md §3). A test asserts this surface stays inert.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# Surfaces (the three public projections of one intelligence).
SURFACE_X = "x"
SURFACE_LINKEDIN = "linkedin"
SURFACE_MEDIUM = "medium"
SURFACES = (SURFACE_X, SURFACE_LINKEDIN, SURFACE_MEDIUM)

# Pieces (the two signature outputs).
PIECE_WEAK_SIGNAL = "weak-signal"
PIECE_NOISE_REPORT = "noise-report"
PIECES = (PIECE_WEAK_SIGNAL, PIECE_NOISE_REPORT)

# X (Twitter) hard limit for the single hook post.
X_CHAR_LIMIT = 280

# Consistent labels so FACT stays visibly separate from INTERPRETATION in every surface, and the
# tests can assert the separation is present.
FACT_LABEL = "FACT"
INTERP_LABEL = "Why it matters"
METHOD_LABEL = "Methodology"

# The DRAFT marker every file carries. `NO auto-posting` is asserted by the tests — this text is the
# machine-checkable promise that the artifact is for human review, not automation.
DRAFT_BANNER = (
    "DRAFT — AI Verkenner · generated for HUMAN REVIEW · NOT auto-posted. "
    "Publishing to X / LinkedIn / Medium is a manual step you take after reviewing."
)

# Backlink written into every vault note so the drafts hang off the project's hub note.
VAULT_BACKLINK = "[[AI Verkenner]]"


@dataclass(frozen=True)
class Draft:
    """One surface's draft for one piece. `text` is the full markdown (DRAFT banner included)."""

    surface: str                     # one of SURFACES
    piece: str                       # one of PIECES
    title: str                       # human title (used for the file name / vault note title)
    slug: str                        # file-name stem, e.g. "weak-signal-x"
    hook: str                        # the lead line; for X this is the <= 280-char hook post
    text: str                        # the complete draft markdown, ready to paste
    source_urls: tuple[str, ...]     # every source URL the draft references (invariant: preserved)


@dataclass(frozen=True)
class PostBundle:
    """Everything one `posts` run produces."""

    digest_id: int | None
    generated_at: datetime
    period_start: datetime | None
    period_end: datetime | None
    has_convergence: bool            # did a genuine cross-source convergence drive the weak signal?
    drafts: tuple[Draft, ...]

    def for_surface(self, surface: str) -> tuple[Draft, ...]:
        return tuple(d for d in self.drafts if d.surface == surface)

    def for_piece(self, piece: str) -> tuple[Draft, ...]:
        return tuple(d for d in self.drafts if d.piece == piece)

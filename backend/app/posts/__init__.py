"""Posts (M7.5) — project one weekly `Digest` into publishable DRAFTS.

Two signature pieces (Weak Signal of the Week + Noise Report) across three surfaces (X, LinkedIn,
Medium). Draft-only and human-in-the-loop: this package never posts, calls a social API, or touches
the network — publishing is a manual step (see docs/SIGNATURE_OUTPUTS.md §3, task 009).
"""

from app.posts.generator import PLACEHOLDER_IMAGE_REF, generate_posts, weak_cluster
from app.posts.model import (
    PIECE_NOISE_REPORT,
    PIECE_WEAK_SIGNAL,
    SURFACE_LINKEDIN,
    SURFACE_MEDIUM,
    SURFACE_X,
    Draft,
    PostBundle,
)

__all__ = [
    "generate_posts",
    "weak_cluster",
    "PostBundle",
    "Draft",
    "PLACEHOLDER_IMAGE_REF",
    "SURFACE_X",
    "SURFACE_LINKEDIN",
    "SURFACE_MEDIUM",
    "PIECE_WEAK_SIGNAL",
    "PIECE_NOISE_REPORT",
]

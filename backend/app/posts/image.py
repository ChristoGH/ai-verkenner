"""Static convergence-cluster image for the M7.5 drafts — pragmatic, not a WebGL renderer.

Given the weak-signal cluster, draw a small static graph — the converging entity at the centre with an
edge to each contributing publisher — as a PNG, using `matplotlib` + `networkx` **when they are
installed** (the optional `[posts]` extra). When they are not (the default light install), or when
rendering fails, we do not break the run: we write a **clearly-marked placeholder** with a one-line
instruction to screenshot the Cosmograph Network view, and the drafts embed that instruction instead
of a broken image link. Fail-safe, like every other stage.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.digests.sections import DigestItem
from app.posts.generator import PLACEHOLDER_IMAGE_REF, _publishers, _theme

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImageArtifact:
    """The image the drafts point at: a rendered PNG, or a placeholder note."""

    path: Path | None        # the file written (PNG or the placeholder .md), if any
    is_placeholder: bool     # True ⇒ no PNG; `ref` is the screenshot instruction
    ref: str                 # the pointer the drafts embed


_PLACEHOLDER_BODY = (
    "# Convergence cluster — image placeholder\n\n"
    "> No static image was rendered (matplotlib/networkx not installed, or nothing to draw).\n"
    "> **Screenshot the Cosmograph Network view** of this cluster in the dashboard and attach it "
    "to the X / LinkedIn / Medium drafts.\n\n"
    "Cluster: {theme}\nPublishers: {pubs}\n"
)


def _write_placeholder(out_path: Path, items: tuple[DigestItem, ...]) -> ImageArtifact:
    md_path = out_path.with_suffix(".placeholder.md")
    theme = _theme(items) if items else "(no cluster this period)"
    pubs = ", ".join(_publishers(items)) or "(none)"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_PLACEHOLDER_BODY.format(theme=theme, pubs=pubs))
    return ImageArtifact(path=md_path, is_placeholder=True, ref=PLACEHOLDER_IMAGE_REF)


def export_convergence_image(
    items: tuple[DigestItem, ...], out_path: Path, *, allow_render: bool = True
) -> ImageArtifact:
    """Render the cluster to `out_path` (PNG) if possible, else write a placeholder beside it.

    `allow_render=False` forces the placeholder path (used to keep tests light and deterministic).
    """
    if not items or not allow_render:
        return _write_placeholder(out_path, items)
    try:
        import matplotlib
        matplotlib.use("Agg")  # headless; no display required
        import matplotlib.pyplot as plt
        import networkx as nx
    except Exception:  # noqa: BLE001 — optional deps absent ⇒ degrade to placeholder
        logger.info("matplotlib/networkx not available; writing image placeholder")
        return _write_placeholder(out_path, items)

    try:
        graph = nx.Graph()
        centre = _theme(items)
        graph.add_node(centre, kind="entity")
        for pub in _publishers(items):
            graph.add_node(pub, kind="publisher")
            graph.add_edge(centre, pub)

        pos = nx.spring_layout(graph, seed=42)  # deterministic layout
        colours = ["#e2564d" if graph.nodes[n].get("kind") == "entity" else "#4d7be2"
                   for n in graph.nodes]
        fig, ax = plt.subplots(figsize=(6, 4))
        nx.draw_networkx(graph, pos, ax=ax, node_color=colours, node_size=1400,
                         font_size=8, edge_color="#9aa0a6", with_labels=True)
        ax.set_title("Weak signal: convergence cluster (AI Verkenner)", fontsize=10)
        ax.axis("off")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.tight_layout()
        fig.savefig(out_path, dpi=140)
        plt.close(fig)
    except Exception as exc:  # noqa: BLE001 — never break a run on a plotting error
        logger.warning("convergence image render failed (%s); writing placeholder", exc)
        return _write_placeholder(out_path, items)

    return ImageArtifact(path=out_path, is_placeholder=False,
                         ref=f"![convergence cluster]({out_path.name})")


__all__ = ["export_convergence_image", "ImageArtifact"]

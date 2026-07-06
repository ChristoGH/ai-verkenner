"""M7.5 convergence image — placeholder path (default, no heavy deps) + optional PNG render.

Offline and deterministic. The placeholder path is the one that always runs in CI (matplotlib is an
optional extra); the render path is exercised only when matplotlib + networkx happen to be installed.
"""

from __future__ import annotations

import importlib.util

import pytest

from app.posts.generator import PLACEHOLDER_IMAGE_REF
from app.posts.image import export_convergence_image
from tests.posts_fixtures import converging_digest

_HAS_PLOTTING = (
    importlib.util.find_spec("matplotlib") is not None
    and importlib.util.find_spec("networkx") is not None
)


def test_placeholder_when_render_disabled(tmp_path):
    cluster = converging_digest().weak_signals
    art = export_convergence_image(cluster, tmp_path / "cluster.png", allow_render=False)
    assert art.is_placeholder is True
    assert art.ref == PLACEHOLDER_IMAGE_REF
    assert art.path is not None and art.path.exists()
    assert "Cosmograph" in art.path.read_text()  # the screenshot instruction is written


def test_placeholder_when_no_cluster(tmp_path):
    art = export_convergence_image((), tmp_path / "cluster.png", allow_render=True)
    assert art.is_placeholder is True
    assert art.path is not None and art.path.exists()


@pytest.mark.skipif(not _HAS_PLOTTING, reason="matplotlib/networkx not installed (optional [posts])")
def test_renders_png_when_plotting_available(tmp_path):
    cluster = converging_digest().weak_signals
    out = tmp_path / "cluster.png"
    art = export_convergence_image(cluster, out, allow_render=True)
    assert art.is_placeholder is False
    assert art.path == out and out.exists() and out.stat().st_size > 0
    assert out.name in art.ref

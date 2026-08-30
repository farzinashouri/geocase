"""Gates for the procedurally generated, non-trivial vector geometry.

The catalog's hand-authored canonicals top out at 10 vertices, so nothing in it
stresses a vertex-dense consumer. These cases are generated rather than
authored, which makes determinism the property that has to be gated: the whole
fixture tree is compared against a fresh regeneration in CI, so a generator
that wandered by one float would fail the build with no way to tell drift from
noise.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
VECTOR_ROOT = REPO_ROOT / "src" / "geocase" / "data" / "core" / "vector"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

pytest.importorskip("shapely")

from generate_vector_fixtures import (  # type: ignore[import-not-found] # noqa: E402
    _MAX_BYTES_NON_SPATIALITE,
    _canonical_geometry,
    _dense_parametric_ring,
    _koch_ring,
    _procedural_specs,
    _read_case_files,
)

from geocase import load_case  # noqa: E402
from geocase.catalog.registry import get_registry  # noqa: E402


def test_koch_ring_is_deterministic_across_calls() -> None:
    """Two calls, one answer -- and no PRNG anywhere in the module."""
    first = _koch_ring(sides=6, depth=3, radius=1.5, centre=(10.0, 50.0))
    second = _koch_ring(sides=6, depth=3, radius=1.5, centre=(10.0, 50.0))

    assert first.wkt == second.wkt

    # Structural, not observational: a seeded PRNG is reproducible only as long
    # as CPython's stream is, and this repo gates on byte-identical output.
    source = (SCRIPTS / "generate_vector_fixtures.py").read_text(encoding="utf-8")
    for banned in ("import random", "import time", "import uuid"):
        assert banned not in source, f"{banned} breaks byte-identical regeneration"


@pytest.mark.parametrize(("sides", "depth"), [(3, 2), (6, 4)])
def test_koch_ring_vertex_count_matches_the_closed_form(sides: int, depth: int) -> None:
    """Each pass turns one segment into four, so the count is exact, not about."""
    ring = _koch_ring(sides=sides, depth=depth, radius=1.0, centre=(0.0, 0.0))

    assert len(ring.exterior.coords) == sides * 4**depth + 1


def test_high_vertex_case_exceeds_two_thousand_vertices() -> None:
    """The point of the case: a vertex count a real implementation can choke on."""
    geom = load_case("dense_ring_polygon_4k").load().geometry.iloc[0]

    assert len(geom.exterior.coords) >= 2000
    assert geom.is_valid


def test_irregular_polygon_is_not_a_rectangle() -> None:
    """Guards the actual defect: 12 canonicals are plain 5-vertex rectangles."""
    geom = load_case("fractal_coastline_polygon").load().geometry.iloc[0]

    assert len(geom.exterior.coords) > 8
    assert geom.area / geom.minimum_rotated_rectangle.area < 0.9


def test_generated_fixtures_stay_under_the_size_budget() -> None:
    """Asserted rather than estimated -- the estimate was ~88 KB of WKT."""
    for spec in _procedural_specs():
        primary = spec.path
        assert primary.exists(), f"{spec.case_id}: {primary} missing"
        total = sum(
            path.stat().st_size
            for path in primary.parent.glob(primary.stem + ".*")
            if path.is_file()
        )
        assert total <= _MAX_BYTES_NON_SPATIALITE, (
            f"{spec.case_id}: {total / 1024:.0f} KB over budget"
        )


def test_single_feature_invariant_still_holds_for_canonicals() -> None:
    """The guard scopes the transcoding families; it is kept, not loosened."""
    cases = _read_case_files(VECTOR_ROOT)
    case_dir, data = cases["simple_valid_polygon"]

    payload = json.loads((case_dir / data["files"]["primary"]).read_text())
    payload["features"].append(payload["features"][0])

    with tempfile.TemporaryDirectory() as tmp:
        fake_dir = Path(tmp)
        (fake_dir / data["files"]["primary"]).write_text(json.dumps(payload))
        fake = {"simple_valid_polygon": (fake_dir, data)}
        with pytest.raises(RuntimeError, match="features"):
            _canonical_geometry("simple_valid_polygon", fake)


def test_dense_parametric_ring_hits_the_requested_vertex_count() -> None:
    """``vertices`` is an exact dial, so fixture size is chosen not discovered."""
    ring = _dense_parametric_ring(
        vertices=512, radius=1.0, lobes=17, amplitude=0.18, centre=(0.0, 0.0)
    )

    assert len(ring.exterior.coords) == 513  # the closing point repeats the first
    assert ring.is_valid


def test_procedural_cases_sit_outside_the_transcoding_family() -> None:
    """No canonical source, no cross_format_canonical tag: a separate concern."""
    registry = get_registry()
    for case_id in ("fractal_coastline_polygon", "dense_ring_polygon_4k"):
        case = registry.get(case_id)
        assert "cross_format_canonical" not in case.tags
        assert not (case.params or {}).get("canonical_source_case_id")
        assert "procedural" in case.tags

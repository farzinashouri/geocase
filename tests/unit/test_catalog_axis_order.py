"""Gates for the GML baselines' authority axis-order declaration.

The six ``*_gml_baseline`` files genuinely contain ``(latitude, longitude)``
coordinates on disk. That is not a bug: they are written with
``urn:ogc:def:crs:EPSG::4326``, and the URN form forces EPSG:4326's *declared*
axis order regardless of GDAL's traditional-order setting. ``VectorCase.load()``
returns them lon-first, correctly.

What was missing until plan 34 is that **no ``case.yaml`` said so.** A user
parsing these files as text -- a perfectly reasonable thing to do with XML --
gets a coordinate swap with nothing in the catalog to warn them. That is the
gap: not wrong bytes, an undeclared property.

See docs/plans/34-close-reviewed-catalog-gaps.md, Phase 4.2.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from geocase.catalog.registry import get_registry

REPO_ROOT = Path(__file__).resolve().parents[2]
VECTOR_ROOT = REPO_ROOT / "src" / "geocase" / "data" / "core" / "vector"

_GML_CASES = [
    "point_gml_baseline",
    "linestring_gml_baseline",
    "polygon_gml_baseline",
    "multipoint_gml_baseline",
    "multilinestring_gml_baseline",
    "multipolygon_gml_baseline",
]


def _metadata(case_id: str):  # type: ignore[no-untyped-def]
    return get_registry().get(case_id)


def _gml_path(case_id: str) -> Path:
    from geocase.catalog.roots import case_roots_by_id

    return case_roots_by_id()[case_id] / _metadata(case_id).files.primary


@pytest.mark.parametrize("case_id", _GML_CASES)
def test_gml_baselines_declare_authority_axis_order(case_id: str) -> None:
    """All six carried the property; none declared it before plan 34."""
    assert "crs/axis_order" in _metadata(case_id).risk_types


@pytest.mark.parametrize("case_id", _GML_CASES)
def test_gml_file_contains_authority_order_coordinates(case_id: str) -> None:
    """The whole gap in one assertion.

    The raw bytes carry the EPSG URN and put latitude first. The catalog now
    says so; this checks the bytes still back the claim.
    """
    text = _gml_path(case_id).read_text(encoding="utf-8")
    assert "urn:ogc:def:crs:EPSG::4326" in text

    match = re.search(r"<gml:(?:pos|posList)>([^<]+)</gml:", text)
    assert match is not None, "no gml:pos or gml:posList found"

    first, second = (float(v) for v in match.group(1).split()[:2])
    extent = _metadata(case_id).extent
    assert extent is not None

    # First ordinate is the latitude: it matches the declared north/south
    # band, and -- for these fixtures -- does not match the east/west one.
    assert extent.south - 1.0 <= first <= extent.north + 1.0
    assert extent.west - 1.0 <= second <= extent.east + 1.0


@pytest.mark.parametrize("case_id", _GML_CASES)
def test_loaded_geometry_is_lon_first(case_id: str) -> None:
    """OGR reads the URN correctly, so the loaded geometry is *not* swapped.

    This is what makes the risk type a documentation problem rather than a
    data one -- and why the fixtures were left alone.
    """
    from geocase import load_case

    bounds = load_case(case_id).load().total_bounds
    extent = _metadata(case_id).extent
    assert extent is not None
    assert bounds[0] == pytest.approx(extent.west, abs=1e-6)
    assert bounds[1] == pytest.approx(extent.south, abs=1e-6)


def test_out_of_bounds_case_does_not_claim_axis_order() -> None:
    """It catches a swap only because latitude 100 is out of range.

    That is a *validity* signal, not an axis-order declaration. Recorded here
    so the distinction is not rediscovered by someone adding the term to it.
    """
    assert "crs/axis_order" not in _metadata("out_of_bounds_coordinates").risk_types

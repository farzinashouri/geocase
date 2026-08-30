"""Gates for extent extraction -- Plan 31, Phase 2.

The class of bug these exist to catch: an extent that looks fine as four
numbers but is not where the data is. Two specific ways that happens here --
a UTM raster whose metre bounds are published as if they were degrees, and a
dateline-crossing polygon whose naive ``total_bounds`` reports the whole
planet -- are the reason this module exists rather than a two-line
``gdf.total_bounds`` at the call site.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# mypy cannot see scripts/ (it is outside the gated `mypy src` scope).
from catalog_extent import case_extent  # type: ignore[import-not-found] # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "src"))

from geocase.catalog.registry import get_registry  # noqa: E402

pytest.importorskip("geopandas")
pytest.importorskip("rasterio")


def _case(case_id: str):
    return get_registry().get(case_id)


def test_vector_extent_matches_the_declared_bounds() -> None:
    """``simple_valid_polygon`` has asserted its own bounds since day one."""
    case = _case("simple_valid_polygon")
    extent = case_extent(case)

    assert extent is not None
    declared = case.params["expected_bounds"]
    assert (extent.west, extent.south, extent.east, extent.north) == tuple(declared)


def test_utm_raster_is_reprojected_to_degrees() -> None:
    """A UTM 33N raster must publish lon/lat, not metres.

    The shared fixture transform is ``from_origin(500000, 4500000, 10, 10)``,
    which is roughly 15E, 40.6N -- southern Italy. Publishing the raw bounds
    would put the case at "longitude 500000", which every consumer of the
    extent, the map included, would then place off the edge of the world.
    """
    extent = case_extent(_case("optical_rgb_small"))

    assert extent is not None
    assert 14.0 < extent.west < 16.0, extent
    assert 40.0 < extent.south < 41.5, extent
    assert -180.0 <= extent.west <= 180.0
    assert -90.0 <= extent.north <= 90.0


def test_dateline_case_yields_a_wrapped_box() -> None:
    """170E..190E must come back as west=170, east=-170, not -180..180."""
    extent = case_extent(_case("dateline_crossing_polygon"))

    assert extent is not None
    assert extent.crosses_antimeridian, extent
    assert extent.west == pytest.approx(170.0, abs=0.5)
    assert extent.east == pytest.approx(-170.0, abs=0.5)


def test_unloadable_case_returns_none() -> None:
    """``unclosed_ring_polygon`` is deliberately malformed and must not raise."""
    assert case_extent(_case("unclosed_ring_polygon")) is None


def test_netcdf_is_skipped() -> None:
    """xarray is not in the catalog CI install set, so netcdf gets no extent."""
    netcdf = [
        case for case in get_registry().list_cases() if str(case.category) == "netcdf"
    ]
    for case in netcdf:
        assert case_extent(case) is None, case.id


def test_extents_are_rounded_so_pages_do_not_churn() -> None:
    """Unrounded floats would make the committed case.yaml files churn."""
    extent = case_extent(_case("optical_rgb_small"))

    assert extent is not None
    for value in (extent.west, extent.south, extent.east, extent.north):
        assert round(value, 6) == value, value


def test_out_of_domain_latitude_gets_no_extent() -> None:
    """A point at latitude 100 has no valid WGS84 box, so it gets none.

    Clamping it to 90 would publish a plausible-looking extent for data whose
    whole reason to exist is that it has no valid position -- a false green
    light of exactly the kind this catalog is built to remove.
    """
    case = _case("out_of_bounds_coordinates")
    assert case_extent(case) is None
    assert case.extent is None

"""Parametrized tests for GDAL footprint utility using bundled GeoCase data."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, cast

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape
from shapely.ops import unary_union
from geocase.assertions import (
    assert_footprint_no_holes,
    assert_footprint_rectangularity,
    assert_footprint_similar_to_expected,
)

_EXAMPLES_DIR = Path(__file__).resolve().parent
if str(_EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(_EXAMPLES_DIR))

# ``gdal_footprint`` imports ``osgeo`` at module scope, and the GDAL Python
# bindings are source-only on PyPI. Skip here rather than inside
# ``gdal_footprint.py`` — that module is not a test module, so pytest would not
# honor the skip and collection would fail outright. The ``sys.path`` insert
# above must stay above this guard so the import below can resolve.
pytest.importorskip("osgeo")

from gdal_footprint import geotiff_footprint_to_geojson


TypedMarkerDecorator = Callable[
    ..., Callable[[Callable[..., object]], Callable[..., object]]
]

geocase_case = cast(TypedMarkerDecorator, pytest.mark.geocase_case)

def _expected_convex_hull_from_raster(path: Path):
    with rasterio.open(path) as src:
        data = src.read(1)
        nodata = src.nodata

        if nodata is None:
            valid_mask = np.isfinite(data)
        else:
            valid_mask = np.isfinite(data) & (data != nodata)

        if not np.any(valid_mask):
            return None

        polys = []
        for geom, value in shapes(
            valid_mask.astype(np.uint8),
            mask=valid_mask,
            transform=src.transform,
        ):
            if int(value) == 1:
                polys.append(shape(geom))

        if not polys:
            return None

        return unary_union(polys).convex_hull


@geocase_case("geotiff_nodata_small", "geotiff_utm_boundary")
def test_gdal_footprint_core_cases_match_expected_convex_hull(
    geocase: Any,
    tmp_path: Path,
) -> None:
    case_id = geocase.id
    tif_path = geocase.primary_path
    out_path = tmp_path / f"{case_id}_footprint.geojson"
    created = geotiff_footprint_to_geojson(tif_path, out_path)

    assert created == out_path
    assert out_path.exists()

    expected_hull = _expected_convex_hull_from_raster(tif_path)
    assert expected_hull is not None

    footprint = gpd.read_file(out_path)
    assert len(footprint) >= 1
    assert footprint.is_valid.all()
    assert not footprint.geometry.is_empty.any()
    assert_footprint_no_holes(footprint)
    assert_footprint_rectangularity(footprint, min_ratio=0.95)

    allowed_types = {"Polygon", "MultiPolygon"}
    assert set(footprint.geometry.geom_type).issubset(allowed_types)

    actual = unary_union(list(footprint.geometry))
    assert actual.is_valid
    assert actual.equals(actual.convex_hull)

    symmetric_diff_area = actual.symmetric_difference(expected_hull).area
    assert symmetric_diff_area <= 1e-6

    with rasterio.open(tif_path) as src:
        left, bottom, right, top = src.bounds

    minx, miny, maxx, maxy = footprint.total_bounds
    tolerance = 1e-6

    assert left - tolerance <= minx <= right + tolerance
    assert left - tolerance <= maxx <= right + tolerance
    assert bottom - tolerance <= miny <= top + tolerance
    assert bottom - tolerance <= maxy <= top + tolerance


@geocase_case(
    "all_valid_rectangular",
    "rotated_two_islands",
    "nonsquare_diagonal_sparse",
    "thin_corridor_shape",
)
def test_gdal_footprint_edge_cases_against_real_expected_data(
    geocase: Any,
    tmp_path: Path,
) -> None:
    case_id = geocase.id
    tif_path = geocase.primary_path
    expected_name = str(geocase.params["expected_footprint"])
    min_rect_ratio = float(geocase.params["min_rect_ratio"])
    expected_path = geocase.root_dir / expected_name
    out_path = tmp_path / f"{case_id}_footprint.geojson"
    geotiff_footprint_to_geojson(tif_path, out_path)

    assert expected_path.exists(), f"Missing expected footprint fixture: {expected_path}"

    actual = gpd.read_file(out_path)
    expected = gpd.read_file(expected_path)

    assert_footprint_no_holes(actual)
    assert_footprint_no_holes(expected)
    assert_footprint_similar_to_expected(
        actual,
        expected,
        max_diff_ratio=1e-10,
    )

    # Use a case-specific threshold from metadata because some edge scenes are
    # intentionally non-rectangular while still having a correct expected footprint.
    assert_footprint_rectangularity(actual, min_ratio=min_rect_ratio)


@geocase_case("hole_center_nodata")
def test_gdal_footprint_fills_interior_nodata_void(
    geocase: Any,
    tmp_path: Path,
) -> None:
    """``gdal_footprint`` ignores an interior NoData void and returns it solid.

    This is the divergence the case advertises via its ``nodata_ignored`` /
    ``footprint_generation_error`` risk types, and it was unobservable until
    Plan 28 Phase 1: the fixture had drifted into the *inverse* of its own
    description -- NoData on the outer border, interior fully valid -- so
    footprint extraction had no interior hole to drop and the case passed a
    ``no holes`` assertion that could never have failed.

    Split out from the parametrized test above because that test asserts the
    expected footprint has no holes, which is true of every edge case *except*
    this one.
    """
    def hole_count(geom: Any) -> int:
        if geom.geom_type == "MultiPolygon":
            return sum(len(part.interiors) for part in geom.geoms)
        return len(geom.interiors)

    tif_path = geocase.primary_path
    expected_path = geocase.root_dir / str(geocase.params["expected_footprint"])
    out_path = tmp_path / f"{geocase.id}_footprint.geojson"
    geotiff_footprint_to_geojson(tif_path, out_path)

    actual = unary_union(list(gpd.read_file(out_path).geometry))
    expected = unary_union(list(gpd.read_file(expected_path).geometry))

    # The ground-truth footprint, derived from the raster's own mask, is a ring.
    assert hole_count(expected) == 1, "expected footprint should retain the void"

    # gdal_footprint returns it solid: the hole is silently filled in.
    assert hole_count(actual) == 0
    assert actual.area > expected.area

    # The difference is exactly the void, so a consumer trusting this footprint
    # would treat NoData pixels as valid data.
    void_area = actual.difference(expected).area
    assert void_area == pytest.approx(actual.area - expected.area)


@geocase_case(
    "simple_valid_polygon",
    "polygon_with_hole",
    "self_intersecting_polygon",
    "dateline_crossing_polygon",
    "mixed_encoding_attributes",
)
def test_gdal_footprint_rejects_vector_inputs(
    geocase: Any,
    tmp_path: Path,
) -> None:
    case_id = geocase.id
    vector_path = geocase.primary_path
    out_path = tmp_path / f"{case_id}_footprint.geojson"

    with pytest.raises(
        ValueError,
        match="no raster bands|Unable to open raster dataset",
    ):
        geotiff_footprint_to_geojson(vector_path, out_path)



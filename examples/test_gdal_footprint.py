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
    "hole_center_nodata",
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

    # Deliberately strict rectangle-likeness to surface problematic scene shapes.
    # It is acceptable for this assertion to fail on difficult edge cases.
    assert_footprint_rectangularity(actual, min_ratio=min_rect_ratio)


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



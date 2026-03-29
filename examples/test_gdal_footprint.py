"""Parametrized tests for GDAL footprint utility using bundled GeoCase data."""

from __future__ import annotations

import sys
from pathlib import Path

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


_CORE_RASTER_CASES = [
    (
        "geotiff_nodata_small",
        Path("src/geocase/data/core/raster/geotiff_nodata_small/nodata_sample.tif"),
    ),
    (
        "geotiff_utm_boundary",
        Path("src/geocase/data/core/raster/geotiff_utm_boundary/utm_boundary.tif"),
    ),
]

_EDGE_RASTER_CASES = [
    (
        "all_valid_rectangular",
        Path("src/geocase/data/core/raster/footprint_edge_cases/all_valid_rectangular.tif"),
        Path("src/geocase/data/core/raster/footprint_edge_cases/all_valid_rectangular_footprint.geojson"),
        0.99,
    ),
    (
        "hole_center_nodata",
        Path("src/geocase/data/core/raster/footprint_edge_cases/hole_center_nodata.tif"),
        Path("src/geocase/data/core/raster/footprint_edge_cases/hole_center_nodata_footprint.geojson"),
        0.98,
    ),
    (
        "rotated_two_islands",
        Path("src/geocase/data/core/raster/footprint_edge_cases/rotated_two_islands.tif"),
        Path("src/geocase/data/core/raster/footprint_edge_cases/rotated_two_islands_footprint.geojson"),
        0.98,
    ),
    (
        "nonsquare_diagonal_sparse",
        Path("src/geocase/data/core/raster/footprint_edge_cases/nonsquare_diagonal_sparse.tif"),
        Path("src/geocase/data/core/raster/footprint_edge_cases/nonsquare_diagonal_sparse_footprint.geojson"),
        0.98,
    ),
    (
        "thin_corridor_shape",
        Path("src/geocase/data/core/raster/footprint_edge_cases/thin_corridor_shape.tif"),
        Path("src/geocase/data/core/raster/footprint_edge_cases/thin_corridor_shape_footprint.geojson"),
        0.98,
    ),
]

_VECTOR_CASES = [
    (
        "simple_valid_polygon",
        Path("src/geocase/data/core/vector/simple_valid_polygon/geometry.geojson"),
    ),
    (
        "polygon_with_hole",
        Path("src/geocase/data/core/vector/polygon_with_hole/geometry.geojson"),
    ),
    (
        "self_intersecting_polygon",
        Path("src/geocase/data/core/vector/self_intersecting_polygon/geometry.geojson"),
    ),
    (
        "dateline_crossing_polygon",
        Path("src/geocase/data/core/vector/dateline_crossing_polygon/geometry.geojson"),
    ),
    (
        "mixed_encoding_attributes",
        Path("src/geocase/data/core/vector/mixed_encoding_attributes/mixed_attrs.gpkg"),
    ),
]


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


@pytest.mark.parametrize("case_id,tif_path", _CORE_RASTER_CASES)
def test_gdal_footprint_core_cases_match_expected_convex_hull(
    case_id: str,
    tif_path: Path,
    tmp_path: Path,
) -> None:
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


@pytest.mark.parametrize(
    "case_id,tif_path,expected_path,min_rect_ratio",
    _EDGE_RASTER_CASES,
)
def test_gdal_footprint_edge_cases_against_real_expected_data(
    case_id: str,
    tif_path: Path,
    expected_path: Path,
    min_rect_ratio: float,
    tmp_path: Path,
) -> None:
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


@pytest.mark.parametrize("case_id,vector_path", _VECTOR_CASES)
def test_gdal_footprint_rejects_vector_inputs(
    case_id: str,
    vector_path: Path,
    tmp_path: Path,
) -> None:
    out_path = tmp_path / f"{case_id}_footprint.geojson"

    with pytest.raises(
        ValueError,
        match="no raster bands|Unable to open raster dataset",
    ):
        geotiff_footprint_to_geojson(vector_path, out_path)



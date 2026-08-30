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


#: The three edge cases whose ``gdal_footprint`` output is a strictly larger
#: hull than the raster's real valid-pixel mask, with the number of disjoint
#: parts the mask-exact truth has. ``all_valid_rectangular`` is deliberately
#: absent: a full rectangle *is* its own convex hull, so GDAL matches truth
#: there. That control is what shows the divergence below is a property of
#: these shapes and not of the harness (Plan 32 Phase 1.4).
_HULL_INFLATED = {
    "rotated_two_islands": 2,
    "nonsquare_diagonal_sparse": 8,
    "thin_corridor_shape": 1,
}


@geocase_case(
    "all_valid_rectangular",
    "rotated_two_islands",
    "nonsquare_diagonal_sparse",
    "thin_corridor_shape",
)
def test_gdal_footprint_diverges_from_the_real_valid_pixel_mask(
    geocase: Any,
    tmp_path: Path,
) -> None:
    """What a footprint consumer gets wrong, and by how much.

    This test used to compare ``gdal_footprint``'s output against a file that
    *was* ``gdal_footprint``'s output, at ``max_diff_ratio=1e-10`` -- a
    regression check on GDAL against itself, which could not fail for the
    reason these cases were written. Plan 32 split the two meanings apart:

    - ``params.expected_footprint`` -> ``<case>_footprint_truth.geojson``, the
      mask-exact geometry emitted from the same array as the raster;
    - ``params.recorded_gdal_footprint`` -> ``<case>_footprint_gdal_hull.geojson``,
      the recorded GDAL answer, kept so a behaviour change stays visible.

    So the assertions below are: GDAL still reproduces its own recording
    (exact), and GDAL's answer is a strict superset of the truth wherever the
    valid pixels are not already a rectangle.
    """
    case_id = geocase.id
    tif_path = geocase.primary_path
    min_rect_ratio = float(geocase.params["min_rect_ratio"])

    truth_path = geocase.root_dir / str(geocase.params["expected_footprint"])
    assert truth_path.exists(), f"Missing truth footprint fixture: {truth_path}"

    out_path = tmp_path / f"{case_id}_footprint.geojson"
    geotiff_footprint_to_geojson(tif_path, out_path)

    actual_gdf = gpd.read_file(out_path)
    truth_gdf = gpd.read_file(truth_path)
    actual = unary_union(list(actual_gdf.geometry))
    truth = unary_union(list(truth_gdf.geometry))

    assert_footprint_no_holes(actual_gdf)

    # 1. The recorded-behaviour baseline, where one exists: GDAL must still
    #    produce byte-for-byte what it produced when the fixture was taken.
    hull_name = geocase.params.get("recorded_gdal_footprint")
    if hull_name is not None:
        hull_path = geocase.root_dir / str(hull_name)
        assert hull_path.exists(), f"Missing recorded GDAL footprint: {hull_path}"
        assert_footprint_similar_to_expected(
            actual_gdf,
            gpd.read_file(hull_path),
            max_diff_ratio=1e-10,
        )

    if case_id not in _HULL_INFLATED:
        # 2a. The control: every pixel is valid, so the hull *is* the mask and
        #     GDAL agrees with ground truth exactly.
        assert_footprint_similar_to_expected(actual_gdf, truth_gdf, max_diff_ratio=1e-10)
        assert_footprint_rectangularity(truth_gdf, min_ratio=min_rect_ratio)
        return

    # 2b. The divergence, asserted in the direction observed: GDAL's footprint
    #     covers the truth, is strictly larger, and where the truth is a
    #     MultiPolygon it has merged the disjoint parts into one.
    assert actual.covers(truth), "GDAL's footprint should be a superset of the truth"
    assert actual.area > truth.area

    def part_count(geom: Any) -> int:
        return len(geom.geoms) if geom.geom_type.startswith("Multi") else 1

    expected_parts = _HULL_INFLATED[case_id]
    assert part_count(truth) == expected_parts
    if expected_parts > 1:
        assert part_count(actual) == 1, (
            "GDAL merges the disjoint valid regions into a single polygon"
        )

    # The threshold in metadata describes the *truth* geometry, which is
    # genuinely non-rectangular. GDAL's hull is near-rectangular by
    # construction, so it clears the same bar trivially -- which is exactly why
    # asserting rectangularity against the hull asserted nothing.
    assert_footprint_rectangularity(truth_gdf, min_ratio=min_rect_ratio)
    truth_ratio = truth.area / truth.minimum_rotated_rectangle.area
    actual_ratio = actual.area / actual.minimum_rotated_rectangle.area
    assert actual_ratio > truth_ratio


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



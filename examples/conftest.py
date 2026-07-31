"""Pytest configuration for the GeoCase example suites.

The "simple" interview suite (``test_easy_geospatial_interview_questions_simple``)
runs the shared edge-case scenarios against the *naive* reference
implementation. Those scenarios are "expose"/"discover" demonstrations: they
assert the correct, edge-case-aware behaviour that only the ``_perfect``
implementation provides, so the simple helper is expected to fail exactly the
inputs listed below (every other input, and every ``_perfect`` counterpart,
passes).

We mark only those specific nodes ``xfail(strict=True)`` from here, instead of
marking whole test functions, so that:

* the parametrized "handles_all_cases" tests still report normal ``passed`` on
  the inputs the simple helper *does* handle (no ``xpassed`` noise), and
* if the simple helper is ever improved to handle one of these inputs, the
  strict xfail turns into a failure and prompts us to drop it from this list.
"""

from __future__ import annotations

_SIMPLE_SUITE_FILENAME = "test_easy_geospatial_interview_questions_simple.py"

# One reason per demonstration scenario, keyed by the (unparametrized) test
# function name.
_SIMPLE_LIMITATION_REASONS: dict[str, str] = {
    "test_reproject_point_normalizes_wrapped_longitude_fixture": (
        "simple reproject_point does not normalize wrapped longitudes"
    ),
    "test_reproject_point_handles_all_point_cases": (
        "simple reproject_point does not normalize dateline-wrapped longitudes"
    ),
    "test_point_in_polygon_excludes_boundary_point": (
        "simple point_in_polygon treats boundary points as inside"
    ),
    "test_get_bbox_classic_antimeridian_polygon_uses_minimal_span": (
        "simple get_bbox does not compute the minimal antimeridian span"
    ),
    "test_get_bbox_handles_all_polygon_cases": (
        "simple get_bbox does not compute the minimal antimeridian span"
    ),
    "test_buffer_in_meters_keeps_dateline_polygon_valid": (
        "simple buffer_in_meters does not handle dateline-crossing geometries"
    ),
    "test_buffer_in_meters_handles_all_polygon_cases": (
        "simple buffer_in_meters assumes WGS84 input and breaks on projected/"
        "dateline geometries"
    ),
    "test_get_utm_epsg_handles_svalbard_special_zone": (
        "simple get_utm_epsg lacks Svalbard/Norway special-zone handling"
    ),
    "test_get_utm_epsg_handles_all_utm_polygon_cases": (
        "simple get_utm_epsg lacks UTM special-zone handling"
    ),
    "test_area_m2_rejects_invalid_self_intersection": (
        "simple area_m2 does not validate or reject invalid geometries"
    ),
    "test_area_m2_handles_all_polygon_cases": (
        "simple area_m2 assumes WGS84 input and does not reject invalid geometries"
    ),
    "test_dissolve_polygons_repairs_invalid_inputs_before_union": (
        "simple dissolve_polygons does not repair invalid inputs before union"
    ),
    "test_dissolve_polygons_handles_all_polygon_cases": (
        "simple dissolve_polygons does not repair invalid inputs before union"
    ),
    "test_clip_raster_accepts_wgs84_bbox_for_projected_raster": (
        "simple clip_raster assumes the bbox CRS matches the raster CRS"
    ),
    "test_pixel_to_world_returns_pixel_center_coordinates": (
        "simple pixel_to_world returns the pixel corner, not its center"
    ),
    "test_rasters_aligned_accepts_shifted_raster_on_same_pixel_lattice": (
        "simple rasters_aligned is overly strict about origin offsets"
    ),
    "test_reproject_geometry_handles_all_polygon_cases": (
        "simple reproject_geometry does not normalize dateline longitudes"
    ),
    "test_reproject_geometry_normalizes_dateline_case_longitudes": (
        "simple reproject_geometry does not normalize dateline longitudes"
    ),
    "test_find_intersections_reports_metric_area": (
        "simple find_intersections reports area in degrees, not metres"
    ),
    "test_validate_polygon_geometry_accepts_repairable_invalid_polygon": (
        "simple validate_polygon_geometry does not repair fixable invalid polygons"
    ),
    "test_validate_polygon_geometry_handles_all_polygon_cases": (
        "simple validate_polygon_geometry does not repair fixable invalid polygons"
    ),
    "test_sample_raster_at_lonlat_masks_nodata_pixel": (
        "simple sample_raster_at_lonlat returns the raw NoData sentinel"
    ),
    "test_cluster_points_keeps_dateline_chain_connected": (
        "simple cluster_points does not keep a transitive dateline chain together"
    ),
    "test_cluster_points_handles_all_point_cases": (
        "simple cluster_points assumes WGS84 input and breaks on projected/dateline "
        "points"
    ),
    "test_fix_geometry_returns_polygonal_output_for_spike_case": (
        "simple fix_geometry returns mixed-geometry output for spike fixtures"
    ),
    "test_rasterize_geometries_burns_pixels_for_geocase_polygon": (
        "simple rasterize_geometries does not reproject geometry to the raster CRS"
    ),
    "test_rasterize_geometries_handles_all_rasterization_polygon_cases": (
        "simple rasterize_geometries does not reproject geometry to the raster CRS"
    ),
    "test_crosses_antimeridian_matches_case_expectation": (
        "simple crosses_antimeridian misses >180-degree dateline encodings"
    ),
    "test_crosses_antimeridian_handles_all_polygon_cases": (
        "simple crosses_antimeridian misses >180-degree encodings and 3D coords"
    ),
}

# The exact set of node names (``item.name``, including any ``[param]`` suffix)
# in the simple suite that the naive implementation is expected to fail.
_SIMPLE_EXPECTED_FAILURES: frozenset[str] = frozenset({
    "test_reproject_point_normalizes_wrapped_longitude_fixture",
    "test_reproject_point_handles_all_point_cases[vector-point-epsg4326-dateline-longitude-wrapping-reprojection]",
    "test_point_in_polygon_excludes_boundary_point",
    "test_get_bbox_classic_antimeridian_polygon_uses_minimal_span",
    "test_get_bbox_handles_all_polygon_cases[vector-polygon-epsg4326-antimeridian-dateline]",
    "test_buffer_in_meters_keeps_dateline_polygon_valid",
    "test_buffer_in_meters_handles_all_polygon_cases[vector-polygon-epsg32633-rasterization-utm]",
    "test_buffer_in_meters_handles_all_polygon_cases[vector-polygon-epsg4326-antimeridian-dateline-2]",
    "test_get_utm_epsg_handles_svalbard_special_zone",
    "test_get_utm_epsg_handles_all_utm_polygon_cases",
    "test_area_m2_rejects_invalid_self_intersection",
    "test_area_m2_handles_all_polygon_cases[vector-polygon-epsg32633-rasterization-utm]",
    "test_area_m2_handles_all_polygon_cases[vector-polygon-epsg4326-invalid-self-intersection-topology]",
    "test_area_m2_handles_all_polygon_cases[vector-polygon-epsg4326-invalid-repair-spike]",
    "test_dissolve_polygons_repairs_invalid_inputs_before_union",
    "test_dissolve_polygons_handles_all_polygon_cases[vector-polygon-epsg4326-invalid-self-intersection-topology]",
    "test_dissolve_polygons_handles_all_polygon_cases[vector-polygon-epsg4326-invalid-repair-spike]",
    "test_clip_raster_accepts_wgs84_bbox_for_projected_raster",
    "test_pixel_to_world_returns_pixel_center_coordinates",
    "test_rasters_aligned_accepts_shifted_raster_on_same_pixel_lattice",
    "test_reproject_geometry_handles_all_polygon_cases[vector-polygon-epsg4326-antimeridian-dateline-2]",
    "test_reproject_geometry_normalizes_dateline_case_longitudes",
    "test_find_intersections_reports_metric_area",
    "test_validate_polygon_geometry_accepts_repairable_invalid_polygon",
    "test_validate_polygon_geometry_handles_all_polygon_cases[vector-polygon-epsg32633-rasterization-utm]",
    "test_sample_raster_at_lonlat_masks_nodata_pixel",
    "test_cluster_points_keeps_dateline_chain_connected",
    "test_cluster_points_handles_all_point_cases[vector-point-epsg3857-epsg3857-valid-web-mercator]",
    "test_cluster_points_handles_all_point_cases[vector-point-epsg4326-clustering-dateline-transitive-connectivity]",
    "test_fix_geometry_returns_polygonal_output_for_spike_case",
    "test_rasterize_geometries_burns_pixels_for_geocase_polygon",
    "test_rasterize_geometries_handles_all_rasterization_polygon_cases",
    "test_crosses_antimeridian_matches_case_expectation[_dateline_polygon_geometry-True]",
    "test_crosses_antimeridian_handles_all_polygon_cases[vector-polygon-epsg32633-rasterization-utm]",
    "test_crosses_antimeridian_handles_all_polygon_cases[vector-polygon-epsg4326-antimeridian-dateline-2]",
    "test_crosses_antimeridian_handles_all_polygon_cases[vector-polygon-epsg4326-attributes-format-limitation-format-specific]",
})


def pytest_collection_modifyitems(config, items):  # noqa: ARG001
    """Mark the known simple-implementation deficiencies as strict xfails."""
    import pytest

    for item in items:
        if item.fspath.basename != _SIMPLE_SUITE_FILENAME:
            continue
        if item.name not in _SIMPLE_EXPECTED_FAILURES:
            continue
        reason = _SIMPLE_LIMITATION_REASONS.get(item.originalname)
        if reason is None:
            continue
        item.add_marker(pytest.mark.xfail(reason=reason, strict=True))

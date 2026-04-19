from __future__ import annotations

import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).with_name("easy_geospatial_interview_questions.py")
_MODULE_SPEC = importlib.util.spec_from_file_location(
    "easy_geospatial_interview_questions_combined_perfect",
    _MODULE_PATH,
)
if _MODULE_SPEC is None or _MODULE_SPEC.loader is None:
    raise ImportError(f"Could not load interview module from {_MODULE_PATH}")

_MODULE = importlib.util.module_from_spec(_MODULE_SPEC)
_MODULE_SPEC.loader.exec_module(_MODULE)

reproject_point_perfect = _MODULE.reproject_point_perfect
point_in_polygon_perfect = _MODULE.point_in_polygon_perfect
get_bbox_perfect = _MODULE.get_bbox_perfect
buffer_in_meters_perfect = _MODULE.buffer_in_meters_perfect
get_utm_epsg_perfect = _MODULE.get_utm_epsg_perfect
area_m2_perfect = _MODULE.area_m2_perfect
dissolve_polygons_perfect = _MODULE.dissolve_polygons_perfect
clip_raster_perfect = _MODULE.clip_raster_perfect
pixel_to_world_perfect = _MODULE.pixel_to_world_perfect
rasters_aligned_perfect = _MODULE.rasters_aligned_perfect
reproject_geometry_perfect = _MODULE.reproject_geometry_perfect
find_intersections_perfect = _MODULE.find_intersections_perfect
validate_polygon_geometry_perfect = _MODULE.validate_polygon_geometry_perfect
sample_raster_at_lonlat_perfect = _MODULE.sample_raster_at_lonlat_perfect
cluster_points_perfect = _MODULE.cluster_points_perfect
fix_geometry_perfect = _MODULE.fix_geometry_perfect
rasterize_geometries_perfect = _MODULE.rasterize_geometries_perfect
crosses_antimeridian_perfect = _MODULE.crosses_antimeridian_perfect
detect_null_island_perfect = _MODULE.detect_null_island_perfect
validate_coordinate_bounds_perfect = _MODULE.validate_coordinate_bounds_perfect

__all__ = [
    "reproject_point_perfect",
    "point_in_polygon_perfect",
    "get_bbox_perfect",
    "buffer_in_meters_perfect",
    "get_utm_epsg_perfect",
    "area_m2_perfect",
    "dissolve_polygons_perfect",
    "clip_raster_perfect",
    "pixel_to_world_perfect",
    "rasters_aligned_perfect",
    "reproject_geometry_perfect",
    "find_intersections_perfect",
    "validate_polygon_geometry_perfect",
    "sample_raster_at_lonlat_perfect",
    "cluster_points_perfect",
    "fix_geometry_perfect",
    "rasterize_geometries_perfect",
    "crosses_antimeridian_perfect",
    "detect_null_island_perfect",
    "validate_coordinate_bounds_perfect",
]

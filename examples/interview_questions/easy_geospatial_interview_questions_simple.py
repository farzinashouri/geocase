from __future__ import annotations

import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).with_name("easy_geospatial_interview_questions.py")
_MODULE_SPEC = importlib.util.spec_from_file_location(
    "easy_geospatial_interview_questions_combined_simple",
    _MODULE_PATH,
)
if _MODULE_SPEC is None or _MODULE_SPEC.loader is None:
    raise ImportError(f"Could not load interview module from {_MODULE_PATH}")

_MODULE = importlib.util.module_from_spec(_MODULE_SPEC)
_MODULE_SPEC.loader.exec_module(_MODULE)

reproject_point = _MODULE.reproject_point
point_in_polygon = _MODULE.point_in_polygon
get_bbox = _MODULE.get_bbox
buffer_in_meters = _MODULE.buffer_in_meters
get_utm_epsg = _MODULE.get_utm_epsg
area_m2 = _MODULE.area_m2
dissolve_polygons = _MODULE.dissolve_polygons
clip_raster = _MODULE.clip_raster
pixel_to_world = _MODULE.pixel_to_world
rasters_aligned = _MODULE.rasters_aligned
reproject_geometry = _MODULE.reproject_geometry
find_intersections = _MODULE.find_intersections
validate_polygon_geometry = _MODULE.validate_polygon_geometry
sample_raster_at_lonlat = _MODULE.sample_raster_at_lonlat
cluster_points = _MODULE.cluster_points
fix_geometry = _MODULE.fix_geometry
rasterize_geometries = _MODULE.rasterize_geometries
crosses_antimeridian = _MODULE.crosses_antimeridian
detect_null_island = _MODULE.detect_null_island
validate_coordinate_bounds = _MODULE.validate_coordinate_bounds

__all__ = [
    "reproject_point",
    "point_in_polygon",
    "get_bbox",
    "buffer_in_meters",
    "get_utm_epsg",
    "area_m2",
    "dissolve_polygons",
    "clip_raster",
    "pixel_to_world",
    "rasters_aligned",
    "reproject_geometry",
    "find_intersections",
    "validate_polygon_geometry",
    "sample_raster_at_lonlat",
    "cluster_points",
    "fix_geometry",
    "rasterize_geometries",
    "crosses_antimeridian",
    "detect_null_island",
    "validate_coordinate_bounds",
]

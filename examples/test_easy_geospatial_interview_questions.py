"""Edge-case tests for the easy interview utilities using GeoCase datasets."""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path
from typing import Any

import pytest
import rasterio
from pyproj import Transformer
from shapely.affinity import translate
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from geocase.catalog.loader import load_case_metadata
from geocase.cases.factory import create_case

pytest.importorskip("osgeo")

_MODULE_PATH = (
    Path(__file__).resolve().parent
    / "interview_questions"
    / "easy_geospatial_interview_questions.py"
)
_MODULE_SPEC = importlib.util.spec_from_file_location(
    "easy_geospatial_interview_questions",
    _MODULE_PATH,
)
if _MODULE_SPEC is None or _MODULE_SPEC.loader is None:
    raise ImportError(f"Could not load interview module from {_MODULE_PATH}")

_INTERVIEW_MODULE = importlib.util.module_from_spec(_MODULE_SPEC)
_MODULE_SPEC.loader.exec_module(_INTERVIEW_MODULE)

area_m2 = _INTERVIEW_MODULE.area_m2
area_m2_perfect = _INTERVIEW_MODULE.area_m2_perfect
buffer_in_meters = _INTERVIEW_MODULE.buffer_in_meters
buffer_in_meters_perfect = _INTERVIEW_MODULE.buffer_in_meters_perfect
clip_raster = _INTERVIEW_MODULE.clip_raster
clip_raster_perfect = _INTERVIEW_MODULE.clip_raster_perfect
cluster_points = _INTERVIEW_MODULE.cluster_points
cluster_points_perfect = _INTERVIEW_MODULE.cluster_points_perfect
crosses_antimeridian = _INTERVIEW_MODULE.crosses_antimeridian
crosses_antimeridian_perfect = _INTERVIEW_MODULE.crosses_antimeridian_perfect
dissolve_polygons = _INTERVIEW_MODULE.dissolve_polygons
dissolve_polygons_perfect = _INTERVIEW_MODULE.dissolve_polygons_perfect
find_intersections = _INTERVIEW_MODULE.find_intersections
find_intersections_perfect = _INTERVIEW_MODULE.find_intersections_perfect
fix_geometry = _INTERVIEW_MODULE.fix_geometry
fix_geometry_perfect = _INTERVIEW_MODULE.fix_geometry_perfect
get_bbox = _INTERVIEW_MODULE.get_bbox
get_bbox_perfect = _INTERVIEW_MODULE.get_bbox_perfect
get_utm_epsg = _INTERVIEW_MODULE.get_utm_epsg
get_utm_epsg_perfect = _INTERVIEW_MODULE.get_utm_epsg_perfect
pixel_to_world = _INTERVIEW_MODULE.pixel_to_world
pixel_to_world_perfect = _INTERVIEW_MODULE.pixel_to_world_perfect
point_in_polygon = _INTERVIEW_MODULE.point_in_polygon
point_in_polygon_perfect = _INTERVIEW_MODULE.point_in_polygon_perfect
rasterize_geometries = _INTERVIEW_MODULE.rasterize_geometries
rasterize_geometries_perfect = _INTERVIEW_MODULE.rasterize_geometries_perfect
rasters_aligned = _INTERVIEW_MODULE.rasters_aligned
rasters_aligned_perfect = _INTERVIEW_MODULE.rasters_aligned_perfect
reproject_geometry = _INTERVIEW_MODULE.reproject_geometry
reproject_geometry_perfect = _INTERVIEW_MODULE.reproject_geometry_perfect
reproject_point = _INTERVIEW_MODULE.reproject_point
reproject_point_perfect = _INTERVIEW_MODULE.reproject_point_perfect
sample_raster_at_lonlat = _INTERVIEW_MODULE.sample_raster_at_lonlat
sample_raster_at_lonlat_perfect = _INTERVIEW_MODULE.sample_raster_at_lonlat_perfect
validate_polygon_geometry = _INTERVIEW_MODULE.validate_polygon_geometry
validate_polygon_geometry_perfect = _INTERVIEW_MODULE.validate_polygon_geometry_perfect


_REPO_ROOT = Path(__file__).resolve().parents[1]
_CORE_ROOT = _REPO_ROOT / "src" / "geocase" / "data" / "core"
_VECTOR_ROOT = _CORE_ROOT / "vector"
_RASTER_ROOT = _CORE_ROOT / "raster"


def _load_case(case_id: str) -> Any:
    """Load a bundled GeoCase fixture by case id."""
    for category_root in (_VECTOR_ROOT, _RASTER_ROOT):
        root = category_root / case_id
        if root.exists():
            meta = load_case_metadata(root / "case.yaml")
            return create_case(meta, root)
    raise FileNotFoundError(f"Unknown GeoCase fixture: {case_id}")


def _load_geometry(case_id: str):
    """Load and union all geometries for a vector GeoCase fixture."""
    gdf = _load_case(case_id).load()
    return unary_union(list(gdf.geometry))


def _longitude_delta(lon_a: float, lon_b: float) -> float:
    """Return the wrapped longitudinal difference in degrees."""
    return abs(((lon_a - lon_b + 180.0) % 360.0) - 180.0)


# Question 1: Reproject a point
def test_reproject_point_roundtrips_dateline_case() -> None:
    """Question 1: round-trip a dateline case point across EPSG:3857."""
    geom = _load_geometry("dateline_crossing_polygon")
    point = geom.representative_point()

    x, y = reproject_point(point.x, point.y, 4326, 3857)
    lon, lat = reproject_point(x, y, 3857, 4326)

    assert math.isfinite(x)
    assert math.isfinite(y)
    assert _longitude_delta(lon, point.x) < 1e-6
    assert lat == pytest.approx(point.y, abs=1e-6)


def test_reproject_point_identity_for_same_crs() -> None:
    """Question 1: keep coordinates unchanged when source and target CRS match."""
    geom = _load_geometry("utm_zone_33_polygon")
    point = geom.representative_point()
    x, y = reproject_point(point.x, point.y, 4326, 4326)

    assert x == pytest.approx(point.x)
    assert y == pytest.approx(point.y)


@pytest.mark.xfail(reason="The interview version preserves wrapped longitudes instead of normalizing them for geographic output.")
def test_reproject_point_normalizes_wrapped_longitude_fixture() -> None:
    """Question 1: expose missing longitude normalization for the wrapped-point GeoCase fixture."""
    case = _load_case("wrapped_longitude_point")
    point = case.load().geometry.iloc[0]

    lon, lat = reproject_point(point.x, point.y, 4326, 4326)

    assert lon == pytest.approx(case.params["normalized_lon"])
    assert lat == pytest.approx(case.params["source_lat"])


def test_reproject_point_perfect_normalizes_wrapped_longitude() -> None:
    """Question 1 perfect: normalize wrapped geographic longitudes back into the usual range."""
    geom = _load_geometry("dateline_crossing_polygon")
    point = geom.representative_point()
    wrapped_lon = point.x if point.x >= 0.0 else point.x + 360.0

    lon, lat = reproject_point_perfect(wrapped_lon, point.y, 4326, 4326)

    assert -180.0 <= lon <= 180.0
    assert _longitude_delta(lon, point.x) < 1e-6
    assert lat == pytest.approx(point.y, abs=1e-6)


def test_reproject_point_perfect_normalizes_wrapped_longitude_fixture() -> None:
    """Question 1 perfect: normalize the dedicated wrapped-longitude GeoCase point."""
    case = _load_case("wrapped_longitude_point")
    point = case.load().geometry.iloc[0]

    lon, lat = reproject_point_perfect(point.x, point.y, 4326, 4326)

    assert lon == pytest.approx(case.params["normalized_lon"])
    assert lat == pytest.approx(case.params["source_lat"])


# Question 2: Check whether a point lies inside a polygon
def test_point_in_polygon_respects_hole_from_geocase() -> None:
    """Question 2: confirm points inside holes are excluded."""
    geom = _load_geometry("polygon_with_hole")
    assert isinstance(geom, Polygon)

    polygon_point = geom.representative_point()
    hole_polygon = Polygon(list(geom.interiors[0].coords))
    hole_point = hole_polygon.representative_point()

    assert point_in_polygon(polygon_point.wkt, geom.wkt) is True
    assert point_in_polygon(hole_point.wkt, geom.wkt) is False


def test_point_in_polygon_handles_simple_inside_and_outside_points() -> None:
    """Question 2: accept interior points and reject exterior ones for a simple polygon."""
    polygon = _load_geometry("simple_valid_polygon")
    inside_point = polygon.representative_point()
    minx, miny, maxx, maxy = polygon.bounds
    width = maxx - minx
    height = maxy - miny
    outside_point = Point(maxx + width, maxy + height)

    assert point_in_polygon(inside_point.wkt, polygon.wkt) is True
    assert point_in_polygon(outside_point.wkt, polygon.wkt) is False


@pytest.mark.xfail(reason="The interview version uses covers, so boundary points count as inside.")
def test_point_in_polygon_excludes_boundary_point() -> None:
    """Question 2: expose boundary-inclusion behavior in the original helper."""
    polygon = _load_geometry("simple_valid_polygon")
    assert isinstance(polygon, Polygon)
    boundary_point = Point(list(polygon.exterior.coords)[0])

    assert point_in_polygon(boundary_point.wkt, polygon.wkt) is False


def test_point_in_polygon_perfect_excludes_boundary_point() -> None:
    """Question 2 perfect: treat boundary points as outside strict interior checks."""
    polygon = _load_geometry("simple_valid_polygon")
    assert isinstance(polygon, Polygon)
    boundary_point = Point(list(polygon.exterior.coords)[0])

    assert point_in_polygon_perfect(boundary_point.wkt, polygon.wkt) is False


# Question 3: Compute the bounding box of a geometry
def test_get_bbox_returns_ordered_bounds_for_simple_case() -> None:
    """Question 3: verify normal bounds ordering for a simple polygon."""
    geom = _load_geometry("simple_valid_polygon")

    minx, miny, maxx, maxy = get_bbox(geom)

    assert minx < maxx
    assert miny < maxy


def test_get_bbox_matches_expected_bounds_for_manual_polygon() -> None:
    """Question 3: return exact bounds stored in GeoCase metadata."""
    case = _load_case("simple_valid_polygon")
    geom = case.load().geometry.iloc[0]
    expected_bounds = tuple(case.params["expected_bounds"])

    assert get_bbox(geom) == pytest.approx(expected_bounds)


def test_get_bbox_normalizes_dateline_crossing_span() -> None:
    """Question 3: expose overly wide bounds for a dateline-crossing polygon."""
    geom = _load_geometry("dateline_crossing_polygon")

    minx, _, maxx, _ = get_bbox(geom)

    assert (maxx - minx) <= 180.0


@pytest.mark.xfail(reason="The interview version returns raw bounds for classic antimeridian polygons.")
def test_get_bbox_classic_antimeridian_polygon_uses_minimal_span() -> None:
    """Question 3: expose over-wide raw bounds on a classic wrapped dateline polygon."""
    geom = _load_geometry("classic_antimeridian_polygon")

    minx, _, maxx, _ = get_bbox(geom)

    assert (maxx - minx) <= 180.0


def test_get_bbox_perfect_classic_antimeridian_polygon_uses_minimal_span() -> None:
    """Question 3 perfect: normalize classic wrapped dateline polygons to a compact span."""
    geom = _load_geometry("classic_antimeridian_polygon")

    minx, _, maxx, _ = get_bbox_perfect(geom)

    assert (maxx - minx) <= 180.0


# Question 4: Buffer a geometry in metres
def test_buffer_in_meters_expands_polygon_with_hole() -> None:
    """Question 4: check that metric buffering expands the geometry."""
    geom = _load_geometry("polygon_with_hole")

    buffered = buffer_in_meters(geom, 500.0)

    assert not buffered.is_empty
    assert buffered.is_valid
    assert buffered.area > geom.area
    assert buffered.covers(geom.representative_point())


def test_buffer_in_meters_returns_empty_geometry_unchanged() -> None:
    """Question 4: keep an empty geometry empty when buffering."""
    empty_polygon = _load_geometry("empty_polygon")

    buffered = buffer_in_meters(empty_polygon, 100.0)

    assert buffered.is_empty


@pytest.mark.xfail(reason="The interview version can produce invalid buffered output for dateline-crossing polygons.")
def test_buffer_in_meters_keeps_dateline_polygon_valid() -> None:
    """Question 4: expose buffering instability on dateline-crossing polygons."""
    geom = _load_geometry("dateline_crossing_polygon")

    buffered = buffer_in_meters(geom, 10_000.0)

    assert buffered.is_valid


def test_buffer_in_meters_perfect_keeps_dateline_polygon_valid() -> None:
    """Question 4 perfect: keep a dateline-crossing polygon valid after buffering."""
    geom = _load_geometry("dateline_crossing_polygon")

    buffered = buffer_in_meters_perfect(geom, 10_000.0)

    assert not buffered.is_empty
    assert buffered.is_valid
    assert buffered.area > geom.area


# Question 5: Find the UTM EPSG code from longitude/latitude
def test_get_utm_epsg_flips_across_antimeridian_edges() -> None:
    """Question 5: verify UTM zone selection near the antimeridian."""
    point_case = _load_case("dateline_points_pair")
    gdf = point_case.load()
    points = sorted(gdf.geometry, key=lambda geom: geom.x)
    west_point, east_point = points[0], points[-1]

    west_epsg = get_utm_epsg(west_point.x, west_point.y)
    east_epsg = get_utm_epsg(east_point.x, east_point.y)

    assert west_epsg == point_case.params["expected_west_utm_epsg"]
    assert east_epsg == point_case.params["expected_east_utm_epsg"]


def test_get_utm_epsg_returns_expected_zone_for_central_europe() -> None:
    """Question 5: return the expected EPSG for a standard northern UTM location."""
    case = _load_case("utm_zone_33_polygon")
    geom = case.load().geometry.iloc[0]
    point = geom.representative_point()

    assert get_utm_epsg(point.x, point.y) == case.params["expected_utm_epsg"]


@pytest.mark.xfail(reason="The interview version does not apply the Svalbard special UTM zone rules.")
def test_get_utm_epsg_handles_svalbard_special_zone() -> None:
    """Question 5: expose missing Svalbard special-zone handling in the original helper."""
    case = _load_case("svalbard_special_zone_polygon")
    point = case.load().geometry.iloc[0].representative_point()

    assert get_utm_epsg(point.x, point.y) == case.params["expected_utm_epsg"]


def test_get_utm_epsg_perfect_handles_svalbard_special_zone() -> None:
    """Question 5 perfect: apply Svalbard special-zone logic correctly."""
    case = _load_case("svalbard_special_zone_polygon")
    point = case.load().geometry.iloc[0].representative_point()

    assert get_utm_epsg_perfect(point.x, point.y) == case.params["expected_utm_epsg"]


# Question 6: Calculate polygon area in square metres
def test_area_m2_detects_hole_area_loss() -> None:
    """Question 6: ensure holes reduce the measured polygon area."""
    geom = _load_geometry("polygon_with_hole")
    assert isinstance(geom, Polygon)

    shell_only = Polygon(list(geom.exterior.coords))

    assert area_m2(geom) > 0.0
    assert area_m2(shell_only) > area_m2(geom)


def test_area_m2_returns_zero_for_empty_polygon() -> None:
    """Question 6: return zero area for an empty polygon."""
    assert area_m2(_load_geometry("empty_polygon")) == 0.0


@pytest.mark.xfail(reason="The helper currently computes area for invalid polygons instead of rejecting them.")
def test_area_m2_rejects_invalid_self_intersection() -> None:
    """Question 6: expose acceptance of invalid self-intersecting polygons."""
    geom = _load_geometry("self_intersecting_polygon")

    with pytest.raises((TypeError, ValueError)):
        area_m2(geom)


def test_area_m2_perfect_rejects_invalid_self_intersection() -> None:
    """Question 6 perfect: reject invalid self-intersecting polygons explicitly."""
    geom = _load_geometry("self_intersecting_polygon")

    with pytest.raises(ValueError, match="valid"):
        area_m2_perfect(geom)


def test_area_m2_perfect_matches_baseline_on_valid_polygon() -> None:
    """Question 6 perfect: match the baseline area result for valid input."""
    geom = _load_geometry("polygon_with_hole")

    assert area_m2_perfect(geom) == pytest.approx(area_m2(geom))


# Question 7: Merge overlapping polygons
def test_dissolve_polygons_merges_shifted_overlap() -> None:
    """Question 7: confirm overlapping polygons dissolve into one part."""
    geom = _load_geometry("simple_valid_polygon")
    shifted = translate(geom, xoff=0.05, yoff=0.05)

    dissolved = dissolve_polygons([geom, shifted])

    assert len(dissolved) == 1
    assert dissolved[0].area < geom.area + shifted.area


def test_dissolve_polygons_preserves_disjoint_parts() -> None:
    """Question 7: keep disjoint polygons as separate dissolved parts."""
    gdf = _load_case("disjoint_polygons").load()
    polygon_a, polygon_b = list(gdf.geometry)

    dissolved = dissolve_polygons([polygon_a, polygon_b])

    assert len(dissolved) == 2


@pytest.mark.xfail(reason="The interview version can raise a topology error instead of repairing invalid polygons before unioning them.")
def test_dissolve_polygons_repairs_invalid_inputs_before_union() -> None:
    """Question 7: expose dissolve failures on invalid polygon inputs."""
    invalid_geom = _load_geometry("self_intersecting_polygon")
    valid_geom = _load_geometry("simple_valid_polygon")

    dissolved = dissolve_polygons([invalid_geom, valid_geom])

    assert dissolved
    assert all(part.is_valid for part in dissolved)


def test_dissolve_polygons_perfect_repairs_invalid_inputs_before_union() -> None:
    """Question 7 perfect: repair invalid polygons before dissolving them."""
    invalid_geom = _load_geometry("self_intersecting_polygon")
    valid_geom = _load_geometry("simple_valid_polygon")

    dissolved = dissolve_polygons_perfect([invalid_geom, valid_geom])

    assert dissolved
    assert all(part.is_valid for part in dissolved)
    assert all(part.geom_type == "Polygon" for part in dissolved)


# Question 8: Clip a raster by a bounding box
def test_clip_raster_creates_smaller_subset(tmp_path: Path) -> None:
    """Question 8: verify clipping produces a smaller raster subset."""
    raster_case = _load_case("geotiff_utm_boundary")
    output_path = tmp_path / "clipped_utm_boundary.tif"

    with rasterio.open(raster_case.primary_path) as src:
        left, bottom, right, top = src.bounds
        bbox = (
            left + (right - left) * 0.2,
            bottom + (top - bottom) * 0.2,
            right - (right - left) * 0.2,
            top - (top - bottom) * 0.2,
        )
        original_shape = (src.width, src.height)

    clip_raster(str(raster_case.primary_path), str(output_path), bbox)

    assert output_path.exists()

    with rasterio.open(output_path) as clipped:
        assert clipped.width < original_shape[0]
        assert clipped.height < original_shape[1]


def test_clip_raster_handles_small_nodata_raster(tmp_path: Path) -> None:
    """Question 8: successfully clip the bundled NoData raster as a baseline case."""
    raster_case = _load_case("geotiff_nodata_small")
    output_path = tmp_path / "clipped_nodata_small.tif"

    with rasterio.open(raster_case.primary_path) as src:
        left, bottom, right, top = src.bounds
        bbox = (left, bottom + (top - bottom) * 0.5, right, top)

    clip_raster(str(raster_case.primary_path), str(output_path), bbox)

    with rasterio.open(output_path) as clipped:
        assert clipped.count == 1
        assert clipped.width > 0
        assert clipped.height > 0


@pytest.mark.xfail(reason="The interview version assumes the bbox is already in the raster CRS.")
def test_clip_raster_accepts_wgs84_bbox_for_projected_raster(tmp_path: Path) -> None:
    """Question 8: expose CRS assumptions when clipping a projected raster with WGS84 bounds."""
    raster_case = _load_case("geotiff_utm_boundary")
    vector_geom = _load_geometry("rasterize_match_wgs84_polygon")
    output_path = tmp_path / "clipped_wgs84_bbox_original.tif"

    clip_raster(str(raster_case.primary_path), str(output_path), vector_geom.bounds)

    with rasterio.open(output_path) as clipped:
        assert clipped.width > 1
        assert clipped.height > 1


def test_clip_raster_perfect_accepts_wgs84_bbox_for_projected_raster(tmp_path: Path) -> None:
    """Question 8 perfect: reproject a WGS84 bbox before clipping a projected raster."""
    raster_case = _load_case("geotiff_utm_boundary")
    vector_geom = _load_geometry("rasterize_match_wgs84_polygon")
    output_path = tmp_path / "clipped_wgs84_bbox_perfect.tif"

    clip_raster_perfect(
        str(raster_case.primary_path),
        str(output_path),
        vector_geom.bounds,
        bbox_epsg=4326,
    )

    with rasterio.open(output_path) as clipped:
        assert clipped.width > 1
        assert clipped.height > 1


# Question 9: Convert raster pixel coordinates to geographic coordinates
def test_pixel_to_world_matches_gdal_geotransform() -> None:
    """Question 9: match pixel-to-world output to the dataset geotransform."""
    from osgeo import gdal

    raster_case = _load_case("geotiff_nodata_small")
    dataset = gdal.Open(str(raster_case.primary_path))

    assert dataset is not None

    row = dataset.RasterYSize // 2
    col = dataset.RasterXSize // 2
    gt = dataset.GetGeoTransform()

    expected_x = gt[0] + col * gt[1] + row * gt[2]
    expected_y = gt[3] + col * gt[4] + row * gt[5]
    observed_x, observed_y = pixel_to_world(dataset, row, col)

    assert observed_x == pytest.approx(expected_x)
    assert observed_y == pytest.approx(expected_y)

    dataset = None


def test_pixel_to_world_returns_upper_left_corner_for_origin_pixel() -> None:
    """Question 9: return the dataset origin for the upper-left pixel."""
    from osgeo import gdal

    raster_case = _load_case("geotiff_nodata_small")
    dataset = gdal.Open(str(raster_case.primary_path))

    assert dataset is not None

    gt = dataset.GetGeoTransform()
    x, y = pixel_to_world(dataset, 0, 0)

    assert x == pytest.approx(gt[0])
    assert y == pytest.approx(gt[3])

    dataset = None


@pytest.mark.xfail(reason="The interview version returns the upper-left corner, not the pixel center.")
def test_pixel_to_world_returns_pixel_center_coordinates() -> None:
    """Question 9: expose corner-versus-center ambiguity for pixel coordinates."""
    from osgeo import gdal

    raster_case = _load_case("geotiff_nodata_small")
    dataset = gdal.Open(str(raster_case.primary_path))

    assert dataset is not None

    row = dataset.RasterYSize // 2
    col = dataset.RasterXSize // 2

    with rasterio.open(raster_case.primary_path) as src:
        expected_x, expected_y = src.xy(row, col)

    observed_x, observed_y = pixel_to_world(dataset, row, col)

    assert observed_x == pytest.approx(expected_x)
    assert observed_y == pytest.approx(expected_y)

    dataset = None


def test_pixel_to_world_perfect_returns_pixel_center_coordinates() -> None:
    """Question 9 perfect: return center coordinates for the requested pixel."""
    from osgeo import gdal

    raster_case = _load_case("geotiff_nodata_small")
    dataset = gdal.Open(str(raster_case.primary_path))

    assert dataset is not None

    row = dataset.RasterYSize // 2
    col = dataset.RasterXSize // 2

    with rasterio.open(raster_case.primary_path) as src:
        expected_x, expected_y = src.xy(row, col)

    observed_x, observed_y = pixel_to_world_perfect(dataset, row, col)

    assert observed_x == pytest.approx(expected_x)
    assert observed_y == pytest.approx(expected_y)

    dataset = None


# Question 10: Detect whether two rasters are aligned
def test_rasters_aligned_detects_clipped_output_as_not_aligned(tmp_path: Path) -> None:
    """Question 10: detect that a clipped raster no longer aligns."""
    from osgeo import gdal

    raster_case = _load_case("geotiff_nodata_small")
    clipped_path = tmp_path / "clipped_nodata.tif"

    with rasterio.open(raster_case.primary_path) as src:
        left, bottom, right, top = src.bounds
        bbox = (
            left,
            bottom,
            left + (right - left) * 0.8,
            top,
        )

    clip_raster(str(raster_case.primary_path), str(clipped_path), bbox)

    dataset_a = gdal.Open(str(raster_case.primary_path))
    dataset_b = gdal.Open(str(raster_case.primary_path))
    dataset_c = gdal.Open(str(clipped_path))

    assert dataset_a is not None
    assert dataset_b is not None
    assert dataset_c is not None

    assert rasters_aligned(dataset_a, dataset_b) is True
    assert rasters_aligned(dataset_a, dataset_c) is False

    dataset_a = None
    dataset_b = None
    dataset_c = None


@pytest.mark.xfail(reason="The interview version requires identical extents instead of accepting integer-pixel grid offsets.")
def test_rasters_aligned_accepts_shifted_raster_on_same_pixel_lattice() -> None:
    """Question 10: expose overly strict alignment checks for a one-pixel-shifted GeoCase raster."""
    from osgeo import gdal

    base_case = _load_case("geotiff_nodata_small")
    shifted_case = _load_case("geotiff_nodata_small_shifted")

    dataset_a = gdal.Open(str(base_case.primary_path))
    dataset_b = gdal.Open(str(shifted_case.primary_path))

    assert dataset_a is not None
    assert dataset_b is not None

    assert rasters_aligned(dataset_a, dataset_b) is True

    dataset_a = None
    dataset_b = None


def test_rasters_aligned_perfect_accepts_equivalent_mem_copy() -> None:
    """Question 10 perfect: treat an equivalent in-memory raster copy as aligned."""
    from osgeo import gdal

    raster_case = _load_case("geotiff_nodata_small")
    dataset = gdal.Open(str(raster_case.primary_path))

    assert dataset is not None

    mem_copy = gdal.GetDriverByName("MEM").CreateCopy("", dataset)

    assert rasters_aligned_perfect(dataset, mem_copy) is True

    dataset = None
    mem_copy = None


def test_rasters_aligned_perfect_accepts_shifted_raster_on_same_pixel_lattice() -> None:
    """Question 10 perfect: accept GeoCase rasters aligned on the same pixel lattice with a one-pixel shift."""
    from osgeo import gdal

    base_case = _load_case("geotiff_nodata_small")
    shifted_case = _load_case("geotiff_nodata_small_shifted")

    dataset_a = gdal.Open(str(base_case.primary_path))
    dataset_b = gdal.Open(str(shifted_case.primary_path))

    assert dataset_a is not None
    assert dataset_b is not None

    assert rasters_aligned_perfect(dataset_a, dataset_b) is True

    dataset_a = None
    dataset_b = None


def test_rasters_aligned_perfect_rejects_clipped_output(tmp_path: Path) -> None:
    """Question 10 perfect: still reject rasters that no longer share the same grid."""
    from osgeo import gdal

    raster_case = _load_case("geotiff_nodata_small")
    clipped_path = tmp_path / "clipped_nodata_perfect.tif"

    with rasterio.open(raster_case.primary_path) as src:
        left, bottom, right, top = src.bounds
        bbox = (left, bottom, left + (right - left) * 0.8, top)

    clip_raster(str(raster_case.primary_path), str(clipped_path), bbox)

    dataset_a = gdal.Open(str(raster_case.primary_path))
    dataset_b = gdal.Open(str(clipped_path))

    assert dataset_a is not None
    assert dataset_b is not None

    assert rasters_aligned_perfect(dataset_a, dataset_b) is False

    dataset_a = None
    dataset_b = None


# Question 11: Reproject a geometry
def test_reproject_geometry_keeps_dateline_case_non_empty() -> None:
    """Question 11: confirm reprojection keeps the dateline geometry usable."""
    geom = _load_geometry("dateline_crossing_polygon")

    projected = reproject_geometry(geom, 4326, 3857)

    assert not projected.is_empty
    assert all(math.isfinite(value) for value in projected.bounds)


def test_reproject_geometry_identity_preserves_simple_polygon() -> None:
    """Question 11: preserve geometry coordinates when reprojection is identity."""
    geom = _load_geometry("simple_valid_polygon")

    projected = reproject_geometry(geom, 4326, 4326)

    assert projected.equals_exact(geom, tolerance=0.0)


@pytest.mark.xfail(reason="The interview version preserves wrapped longitudes on geographic identity reprojection.")
def test_reproject_geometry_normalizes_dateline_case_longitudes() -> None:
    """Question 11: expose missing longitude normalization for the wrapped dateline polygon."""
    geom = _load_geometry("dateline_crossing_polygon")

    projected = reproject_geometry(geom, 4326, 4326)

    assert projected.bounds[0] >= -180.0
    assert projected.bounds[2] <= 180.0


def test_reproject_geometry_perfect_normalizes_geographic_longitudes() -> None:
    """Question 11 perfect: normalize wrapped longitudes when output stays geographic."""
    geom = _load_geometry("dateline_crossing_polygon")

    projected = reproject_geometry_perfect(geom, 4326, 4326)

    assert not projected.is_empty
    assert projected.is_valid
    assert projected.bounds[0] >= -180.0
    assert projected.bounds[2] <= 180.0


def test_reproject_geometry_perfect_identity_preserves_simple_polygon() -> None:
    """Question 11 perfect: keep already-normalized identity reprojection unchanged."""
    geom = _load_geometry("simple_valid_polygon")

    projected = reproject_geometry_perfect(geom, 4326, 4326)

    assert projected.equals_exact(geom, tolerance=0.0)


# Question 12: Find intersections between input polygons and AOIs
def test_find_intersections_reports_overlap() -> None:
    """Question 12: verify overlap reporting includes area and geometry."""
    geom = _load_geometry("simple_valid_polygon")
    shifted = translate(geom, xoff=0.05, yoff=0.05)

    intersections = find_intersections([geom], [shifted])

    assert len(intersections) == 1
    assert intersections[0]["candidate_index"] == 0
    assert intersections[0]["aoi_index"] == 0
    assert intersections[0]["intersection_area"] > 0.0
    assert not intersections[0]["intersection_geom"].is_empty


def test_find_intersections_returns_empty_for_disjoint_polygons() -> None:
    """Question 12: return no matches for disjoint polygons."""
    gdf = _load_case("disjoint_polygons").load()
    polygon_a, polygon_b = list(gdf.geometry)

    assert find_intersections([polygon_a], [polygon_b]) == []


@pytest.mark.xfail(reason="The interview version reports intersection area in source CRS units, not square metres.")
def test_find_intersections_reports_metric_area() -> None:
    """Question 12: expose that intersection area is computed in degrees, not metres."""
    geom = _load_geometry("simple_valid_polygon")
    shifted = translate(geom, xoff=0.05, yoff=0.05)

    intersections = find_intersections([geom], [shifted])
    assert len(intersections) == 1

    projected_intersection = reproject_geometry(intersections[0]["intersection_geom"], 4326, 3857)
    expected_area_m2 = projected_intersection.area

    assert intersections[0]["intersection_area"] == pytest.approx(expected_area_m2)


def test_find_intersections_perfect_reports_metric_area() -> None:
    """Question 12 perfect: report overlap area in square metres for WGS84 inputs."""
    geom = _load_geometry("simple_valid_polygon")
    shifted = translate(geom, xoff=0.05, yoff=0.05)

    intersections = find_intersections_perfect([geom], [shifted], geom_epsg=4326)
    assert len(intersections) == 1

    expected_area_m2 = area_m2_perfect(intersections[0]["intersection_geom"])

    assert intersections[0]["intersection_area"] == pytest.approx(expected_area_m2)


# Question 13: Validate a geometry before DB insertion
def test_validate_polygon_geometry_flags_invalid_and_too_small_cases() -> None:
    """Question 13: flag invalid geometry and minimum-area failures."""
    invalid_geom = _load_geometry("self_intersecting_polygon")
    small_geom = _load_geometry("simple_valid_polygon")

    invalid_ok, invalid_errors = validate_polygon_geometry(invalid_geom, min_area_m2=1.0)
    small_ok, small_errors = validate_polygon_geometry(small_geom, min_area_m2=1e20)

    assert invalid_ok is False
    assert any("invalid" in error.lower() for error in invalid_errors)
    assert small_ok is False
    assert any("below minimum" in error.lower() for error in small_errors)


def test_validate_polygon_geometry_accepts_valid_polygon() -> None:
    """Question 13: accept a valid polygon that exceeds the minimum area."""
    geom = _load_geometry("simple_valid_polygon")

    ok, errors = validate_polygon_geometry(geom, min_area_m2=1.0)

    assert ok is True
    assert errors == []


@pytest.mark.xfail(reason="The interview version rejects repairable invalid polygons instead of repairing them first.")
def test_validate_polygon_geometry_accepts_repairable_invalid_polygon() -> None:
    """Question 13: expose lack of repair-before-validation for fixable invalid polygons."""
    geom = _load_geometry("self_intersecting_polygon")

    ok, errors = validate_polygon_geometry(geom, min_area_m2=1.0)

    assert ok is True
    assert errors == []


def test_validate_polygon_geometry_perfect_repairs_invalid_polygon() -> None:
    """Question 13 perfect: repair a fixable invalid polygon before validating it."""
    geom = _load_geometry("self_intersecting_polygon")

    ok, errors = validate_polygon_geometry_perfect(geom, min_area_m2=1.0)

    assert ok is True
    assert errors == []


def test_validate_polygon_geometry_perfect_accepts_valid_polygon() -> None:
    """Question 13 perfect: keep already-valid polygon inputs accepted."""
    geom = _load_geometry("simple_valid_polygon")

    ok, errors = validate_polygon_geometry_perfect(geom, min_area_m2=1.0)

    assert ok is True
    assert errors == []


def test_validate_polygon_geometry_perfect_keeps_minimum_area_check() -> None:
    """Question 13 perfect: still fail polygons that stay below the minimum area."""
    geom = _load_geometry("simple_valid_polygon")

    ok, errors = validate_polygon_geometry_perfect(geom, min_area_m2=1e20)

    assert ok is False
    assert any("below minimum" in error.lower() for error in errors)


# Question 14: Extract raster value at a geographic point
def test_sample_raster_at_lonlat_matches_center_pixel_value() -> None:
    """Question 14: sample the same value seen at a raster center pixel."""
    from osgeo import gdal

    raster_case = _load_case("geotiff_utm_boundary")

    with rasterio.open(raster_case.primary_path) as src:
        row = src.height // 2
        col = src.width // 2
        x, y = src.xy(row, col)
        lon, lat = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True).transform(x, y)
        expected = src.read(1)[row, col].item()

    dataset = gdal.Open(str(raster_case.primary_path))
    assert dataset is not None

    observed = sample_raster_at_lonlat(dataset, lon, lat)

    assert observed == pytest.approx(expected)

    dataset = None


def test_sample_raster_at_lonlat_reads_value_from_nodata_fixture_center() -> None:
    """Question 14: sample a valid center pixel from the NoData raster fixture."""
    from osgeo import gdal

    raster_case = _load_case("geotiff_nodata_small")

    with rasterio.open(raster_case.primary_path) as src:
        row = src.height // 2
        col = src.width // 2
        x, y = src.xy(row, col)
        lon, lat = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True).transform(x, y)
        expected = src.read(1)[row, col].item()

    dataset = gdal.Open(str(raster_case.primary_path))
    assert dataset is not None

    observed = sample_raster_at_lonlat(dataset, lon, lat)

    assert observed == pytest.approx(expected)

    dataset = None


@pytest.mark.xfail(reason="The interview version returns the nodata sentinel instead of masking it.")
def test_sample_raster_at_lonlat_masks_nodata_pixel() -> None:
    """Question 14: expose that the original helper returns the raw NoData sentinel."""
    from osgeo import gdal

    raster_case = _load_case("geotiff_nodata_small")

    with rasterio.open(raster_case.primary_path) as src:
        data = src.read(1)
        nodata = src.nodata
        rows, cols = (data == nodata).nonzero()
        row = int(rows[0])
        col = int(cols[0])
        x, y = src.xy(row, col)
        lon, lat = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True).transform(x, y)

    dataset = gdal.Open(str(raster_case.primary_path))
    assert dataset is not None

    assert sample_raster_at_lonlat(dataset, lon, lat) is None

    dataset = None


def test_sample_raster_at_lonlat_perfect_masks_nodata_pixel() -> None:
    """Question 14 perfect: return None when the sampled pixel is NoData."""
    from osgeo import gdal

    raster_case = _load_case("geotiff_nodata_small")

    with rasterio.open(raster_case.primary_path) as src:
        data = src.read(1)
        nodata = src.nodata
        rows, cols = (data == nodata).nonzero()
        row = int(rows[0])
        col = int(cols[0])
        x, y = src.xy(row, col)
        lon, lat = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True).transform(x, y)

    dataset = gdal.Open(str(raster_case.primary_path))
    assert dataset is not None

    assert sample_raster_at_lonlat_perfect(dataset, lon, lat) is None

    dataset = None


# Question 15: Group nearby points into clusters
def test_cluster_points_groups_nearby_dateline_points() -> None:
    """Question 15: expose clustering issues for points split by the dateline."""
    gdf = _load_case("dateline_points_pair").load()
    points = list(gdf.geometry)

    clusters = cluster_points(points, max_distance_m=50_000.0)

    assert len(clusters) == 1


def test_cluster_points_groups_nearby_points_in_one_cluster() -> None:
    """Question 15: group nearby points together in a straightforward local case."""
    gdf = _load_case("nearby_points_cluster").load()
    points = list(gdf.geometry)

    clusters = cluster_points(points, max_distance_m=100.0)

    assert len(clusters) == 1
    assert len(clusters[0]) == 3


@pytest.mark.xfail(reason="The interview version can split a transitive dateline cluster because of projection distortion.")
def test_cluster_points_keeps_dateline_chain_connected() -> None:
    """Question 15: expose failure to keep a transitive dateline chain in one cluster."""
    case = _load_case("dateline_chain_cluster")
    points = list(case.load().geometry)

    clusters = cluster_points(points, max_distance_m=case.params["max_distance_m"])

    assert len(clusters) == case.params["expected_cluster_count"]
    assert sorted(len(cluster) for cluster in clusters) == case.params["expected_cluster_sizes"]


def test_cluster_points_perfect_groups_nearby_dateline_points() -> None:
    """Question 15 perfect: cluster antimeridian-adjacent points geodesically."""
    gdf = _load_case("dateline_points_pair").load()
    points = list(gdf.geometry)

    clusters = cluster_points_perfect(points, max_distance_m=50_000.0)

    assert len(clusters) == 1
    assert len(clusters[0]) == 2


def test_cluster_points_perfect_groups_nearby_points_in_one_cluster() -> None:
    """Question 15 perfect: keep the simple local clustering case working too."""
    gdf = _load_case("nearby_points_cluster").load()
    points = list(gdf.geometry)

    clusters = cluster_points_perfect(points, max_distance_m=100.0)

    assert len(clusters) == 1
    assert len(clusters[0]) == 3


def test_cluster_points_perfect_keeps_dateline_chain_connected() -> None:
    """Question 15 perfect: keep the dateline chain fixture in one transitive cluster."""
    case = _load_case("dateline_chain_cluster")
    points = list(case.load().geometry)

    clusters = cluster_points_perfect(points, max_distance_m=case.params["max_distance_m"])

    assert len(clusters) == case.params["expected_cluster_count"]
    assert sorted(len(cluster) for cluster in clusters) == case.params["expected_cluster_sizes"]


# Question 16: Repair invalid polygons where possible
def test_fix_geometry_repairs_self_intersection_case() -> None:
    """Question 16: verify invalid self-intersections can be repaired."""
    geom = _load_geometry("self_intersecting_polygon")

    fixed = fix_geometry(geom)

    assert not fixed.is_empty
    assert fixed.is_valid


def test_fix_geometry_returns_valid_geometry_unchanged() -> None:
    """Question 16: leave already valid geometries usable and valid."""
    geom = _load_geometry("simple_valid_polygon")

    fixed = fix_geometry(geom)

    assert fixed.equals(geom)
    assert fixed.is_valid


@pytest.mark.xfail(reason="The interview version can return a mixed GeometryCollection instead of polygon-only repaired output.")
def test_fix_geometry_returns_polygonal_output_for_spike_case() -> None:
    """Question 16: expose mixed-geometry repair output for the spike fixture."""
    geom = _load_geometry("spike_invalid_polygon")

    fixed = fix_geometry(geom)

    assert fixed.geom_type in {"Polygon", "MultiPolygon"}
    assert fixed.is_valid


def test_fix_geometry_perfect_repairs_self_intersection_case() -> None:
    """Question 16 perfect: return valid polygonal geometry for a fixable self-intersection."""
    geom = _load_geometry("self_intersecting_polygon")

    fixed = fix_geometry_perfect(geom)

    assert not fixed.is_empty
    assert fixed.is_valid
    assert fixed.geom_type in {"Polygon", "MultiPolygon"}


def test_fix_geometry_perfect_returns_valid_geometry_unchanged() -> None:
    """Question 16 perfect: leave already-valid polygon geometry untouched."""
    geom = _load_geometry("simple_valid_polygon")

    fixed = fix_geometry_perfect(geom)

    assert fixed.equals(geom)
    assert fixed.is_valid


def test_fix_geometry_perfect_returns_polygonal_output_for_spike_case() -> None:
    """Question 16 perfect: keep only polygonal output when spike repair yields mixed geometry."""
    geom = _load_geometry("spike_invalid_polygon")

    fixed = fix_geometry_perfect(geom)

    assert fixed.geom_type in {"Polygon", "MultiPolygon"}
    assert fixed.is_valid


# Question 17: Rasterize vector geometries onto a reference raster grid
@pytest.mark.xfail(reason="Rasterization does not reproject vector inputs onto the raster CRS.")
def test_rasterize_geometries_burns_pixels_for_geocase_polygon(tmp_path: Path) -> None:
    """Question 17: expose missing reprojection during rasterization."""
    vector_geom = _load_geometry("simple_valid_polygon")
    raster_case = _load_case("geotiff_utm_boundary")
    output_path = tmp_path / "rasterized_polygon.tif"

    rasterize_geometries([vector_geom], str(raster_case.primary_path), str(output_path))

    with rasterio.open(output_path) as src:
        data = src.read(1)

    assert data.max() == 1


def test_rasterize_geometries_burns_pixels_when_geometry_matches_raster_crs(tmp_path: Path) -> None:
    """Question 17: rasterize successfully when input geometry is preprojected to raster CRS."""
    raster_case = _load_case("geotiff_utm_boundary")
    vector_geom = _load_geometry("rasterize_match_utm33_polygon")
    output_path = tmp_path / "rasterized_polygon_projected.tif"

    rasterize_geometries([vector_geom], str(raster_case.primary_path), str(output_path))

    with rasterio.open(output_path) as src:
        data = src.read(1)

    assert data.max() == 1


def test_rasterize_geometries_perfect_reprojects_wgs84_geometry(tmp_path: Path) -> None:
    """Question 17 perfect: reproject WGS84 polygons onto the raster CRS before burning."""
    raster_case = _load_case("geotiff_utm_boundary")
    vector_geom = _load_geometry("rasterize_match_wgs84_polygon")
    output_path = tmp_path / "rasterized_polygon_perfect.tif"

    rasterize_geometries_perfect(
        [vector_geom],
        str(raster_case.primary_path),
        str(output_path),
        src_epsg=4326,
    )

    with rasterio.open(output_path) as src:
        data = src.read(1)

    assert data.max() == 1


# Question 18: Determine whether a polygon crosses the antimeridian
@pytest.mark.parametrize(
    ("case_id", "expected"),
    [
        pytest.param(
            "dateline_crossing_polygon",
            True,
            marks=pytest.mark.xfail(
                reason="The heuristic misses dateline cases encoded with longitudes beyond 180.",
            ),
        ),
        ("simple_valid_polygon", False),
    ],
)
def test_crosses_antimeridian_matches_case_expectation(case_id: str, expected: bool) -> None:
    """Question 18: verify antimeridian detection on simple and dateline cases."""
    geom = _load_geometry(case_id)

    assert crosses_antimeridian(geom) is expected


def test_crosses_antimeridian_detects_classic_wrapped_polygon() -> None:
    """Question 18: detect a polygon whose longitudes jump from 179 to -179 degrees."""
    geom = _load_geometry("classic_antimeridian_polygon")

    assert crosses_antimeridian(geom) is True


@pytest.mark.parametrize(
    ("case_id", "expected"),
    [
        ("dateline_crossing_polygon", True),
        ("simple_valid_polygon", False),
        ("classic_antimeridian_polygon", True),
    ],
)
def test_crosses_antimeridian_perfect_matches_case_expectation(
    case_id: str,
    expected: bool,
) -> None:
    """Question 18 perfect: detect both wrapped and >180° dateline encodings."""
    geom = _load_geometry(case_id)

    assert crosses_antimeridian_perfect(geom) is expected
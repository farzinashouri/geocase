"""Edge-case tests for the easy interview utilities using GeoCase datasets."""

from __future__ import annotations

import importlib.util
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import pytest
import rasterio
from pyproj import CRS, Transformer
from shapely.affinity import translate
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from geocase.catalog import load_case_index, load_case_metadata, select_cases
from geocase.cases.factory import create_case
from geocase.pytest_plugin.case_diagnostics import (
    build_case_params,
    describe_case_data,
    failure_context,
)

pytest.importorskip("osgeo")

_SIMPLE_MODULE_PATH = (
    Path(__file__).resolve().parent
    / "interview_questions"
    / "easy_geospatial_interview_questions_simple.py"
)
_SIMPLE_MODULE_SPEC = importlib.util.spec_from_file_location(
    "easy_geospatial_interview_questions_simple",
    _SIMPLE_MODULE_PATH,
)
if _SIMPLE_MODULE_SPEC is None or _SIMPLE_MODULE_SPEC.loader is None:
    raise ImportError(f"Could not load interview module from {_SIMPLE_MODULE_PATH}")

_PERFECT_MODULE_PATH = (
    Path(__file__).resolve().parent
    / "interview_questions"
    / "easy_geospatial_interview_questions_perfect.py"
)
_PERFECT_MODULE_SPEC = importlib.util.spec_from_file_location(
    "easy_geospatial_interview_questions_perfect",
    _PERFECT_MODULE_PATH,
)
if _PERFECT_MODULE_SPEC is None or _PERFECT_MODULE_SPEC.loader is None:
    raise ImportError(f"Could not load interview module from {_PERFECT_MODULE_PATH}")

_SIMPLE_MODULE = importlib.util.module_from_spec(_SIMPLE_MODULE_SPEC)
_SIMPLE_MODULE_SPEC.loader.exec_module(_SIMPLE_MODULE)
_PERFECT_MODULE = importlib.util.module_from_spec(_PERFECT_MODULE_SPEC)
_PERFECT_MODULE_SPEC.loader.exec_module(_PERFECT_MODULE)

area_m2 = _SIMPLE_MODULE.area_m2
area_m2_perfect = _PERFECT_MODULE.area_m2_perfect
buffer_in_meters = _SIMPLE_MODULE.buffer_in_meters
buffer_in_meters_perfect = _PERFECT_MODULE.buffer_in_meters_perfect
clip_raster = _SIMPLE_MODULE.clip_raster
clip_raster_perfect = _PERFECT_MODULE.clip_raster_perfect
cluster_points = _SIMPLE_MODULE.cluster_points
cluster_points_perfect = _PERFECT_MODULE.cluster_points_perfect
crosses_antimeridian = _SIMPLE_MODULE.crosses_antimeridian
crosses_antimeridian_perfect = _PERFECT_MODULE.crosses_antimeridian_perfect
dissolve_polygons = _SIMPLE_MODULE.dissolve_polygons
dissolve_polygons_perfect = _PERFECT_MODULE.dissolve_polygons_perfect
find_intersections = _SIMPLE_MODULE.find_intersections
find_intersections_perfect = _PERFECT_MODULE.find_intersections_perfect
fix_geometry = _SIMPLE_MODULE.fix_geometry
fix_geometry_perfect = _PERFECT_MODULE.fix_geometry_perfect
get_bbox = _SIMPLE_MODULE.get_bbox
get_bbox_perfect = _PERFECT_MODULE.get_bbox_perfect
get_utm_epsg = _SIMPLE_MODULE.get_utm_epsg
get_utm_epsg_perfect = _PERFECT_MODULE.get_utm_epsg_perfect
pixel_to_world = _SIMPLE_MODULE.pixel_to_world
pixel_to_world_perfect = _PERFECT_MODULE.pixel_to_world_perfect
point_in_polygon = _SIMPLE_MODULE.point_in_polygon
point_in_polygon_perfect = _PERFECT_MODULE.point_in_polygon_perfect
rasterize_geometries = _SIMPLE_MODULE.rasterize_geometries
rasterize_geometries_perfect = _PERFECT_MODULE.rasterize_geometries_perfect
rasters_aligned = _SIMPLE_MODULE.rasters_aligned
rasters_aligned_perfect = _PERFECT_MODULE.rasters_aligned_perfect
reproject_geometry = _SIMPLE_MODULE.reproject_geometry
reproject_geometry_perfect = _PERFECT_MODULE.reproject_geometry_perfect
reproject_point = _SIMPLE_MODULE.reproject_point
reproject_point_perfect = _PERFECT_MODULE.reproject_point_perfect
sample_raster_at_lonlat = _SIMPLE_MODULE.sample_raster_at_lonlat
sample_raster_at_lonlat_perfect = _PERFECT_MODULE.sample_raster_at_lonlat_perfect
validate_polygon_geometry = _SIMPLE_MODULE.validate_polygon_geometry
validate_polygon_geometry_perfect = _PERFECT_MODULE.validate_polygon_geometry_perfect
detect_null_island = _SIMPLE_MODULE.detect_null_island
detect_null_island_perfect = _PERFECT_MODULE.detect_null_island_perfect
validate_coordinate_bounds = _SIMPLE_MODULE.validate_coordinate_bounds
validate_coordinate_bounds_perfect = _PERFECT_MODULE.validate_coordinate_bounds_perfect


_REPO_ROOT = Path(__file__).resolve().parents[1]
_PACKAGE_ROOT = _REPO_ROOT / "src" / "geocase"
_CASE_INDEX_PATH = _PACKAGE_ROOT / "metadata" / "case-index.yaml"
_CORE_ROOT = _REPO_ROOT / "src" / "geocase" / "data" / "core"
_VECTOR_ROOT = _CORE_ROOT / "vector"
_RASTER_ROOT = _CORE_ROOT / "raster"


@lru_cache(maxsize=1)
def _indexed_case_entries() -> tuple[tuple[Any, Path], ...]:
    """Load all indexed case metadata and their case root directories."""
    entries: list[tuple[Any, Path]] = []
    for rel_path in load_case_index(_CASE_INDEX_PATH):
        case_yaml = _PACKAGE_ROOT / rel_path
        metadata = load_case_metadata(case_yaml)
        entries.append((metadata, case_yaml.parent))
    return tuple(entries)


@lru_cache(maxsize=1)
def _indexed_case_map() -> dict[str, tuple[Any, Path]]:
    """Map case id to (metadata, case root) for indexed cases."""
    return {metadata.id: (metadata, root) for metadata, root in _indexed_case_entries()}


def _load_case(case_id: str) -> Any:
    """Load an indexed GeoCase fixture by case id."""
    case_entry = _indexed_case_map().get(case_id)
    if case_entry is None:
        raise FileNotFoundError(f"Unknown indexed GeoCase fixture: {case_id}")
    metadata, root = case_entry
    return create_case(metadata, root)


def _load_geometry(case_id: str):
    """Load and union all geometries for a vector GeoCase fixture."""
    gdf = _load_case(case_id).load()
    return unary_union(list(gdf.geometry))


def _select_case_metadata(
    *,
    extra_filter: Callable[[Any], bool] | None = None,
    **selection_kwargs: Any,
) -> list[Any]:
    """Select indexed case metadata using catalog selectors plus optional filter."""
    metadata = [metadata for metadata, _ in _indexed_case_entries()]

    matches = select_cases(metadata, **selection_kwargs)
    if extra_filter is not None:
        matches = [meta for meta in matches if extra_filter(meta)]
    return matches


def _load_selected_case(**selection_kwargs: Any) -> Any:
    """Load exactly one bundled GeoCase fixture chosen by metadata selectors."""
    matches = _select_case_metadata(**selection_kwargs)
    if len(matches) != 1:
        raise AssertionError(
            f"Expected exactly one selected case, found {len(matches)} for {selection_kwargs}."
        )
    return _load_case(matches[0].id)


def _select_bundled_vector_cases(**selection_kwargs: Any) -> list[Any]:
    """Select bundled vector fixtures from indexed metadata using selectors."""
    metadata = [
        metadata
        for metadata, _ in _indexed_case_entries()
        if metadata.category == "vector" and metadata.storage_class == "bundled"
    ]
    return select_cases(metadata, **selection_kwargs)


def _load_selected_geometry(geocase: Any):
    """Load and union all geometries from a selector-resolved vector case."""
    return unary_union(list(geocase.load().geometry))


def _is_valid_geometry_case(meta: Any) -> bool:
    """Return True if case is expected to have valid, non-empty geometry.

    Checks:
    1. assertions.expect_valid_geometry is not False
    2. Tags do not include 'invalid' or 'empty'
    """
    assertions = getattr(meta, "assertions", None)
    if assertions is not None:
        if getattr(assertions, "expect_valid_geometry", None) is False:
            return False
    tags = set(getattr(meta, "tags", []) or [])
    if "invalid" in tags or "empty" in tags:
        return False
    return True


def _is_loadable_case(meta: Any) -> bool:
    """Return True if case is expected to be loadable.

    Checks assertions.expect_loadable is not False.
    """
    assertions = getattr(meta, "assertions", None)
    if assertions is not None:
        if getattr(assertions, "expect_loadable", None) is False:
            return False
    return True


def _is_invalid_geometry_case(meta: Any) -> bool:
    """Return True if case is expected to have invalid geometry.

    These are cases that should be explicitly rejected by _perfect functions.
    Checks:
    1. assertions.expect_valid_geometry is False, OR
    2. Tags include 'invalid'

    Also requires that the case is loadable (we need to load it to test rejection).
    """
    if not _is_loadable_case(meta):
        return False

    assertions = getattr(meta, "assertions", None)
    if assertions is not None:
        if getattr(assertions, "expect_valid_geometry", None) is False:
            return True

    tags = set(getattr(meta, "tags", []) or [])
    return "invalid" in tags


# Valid-only params (default for standard tests)
_VECTOR_POINT_CASE_PARAMS = build_case_params(
    _select_case_metadata(
        category="vector",
        geometry_type="Point",
        extra_filter=_is_valid_geometry_case,
    ),
    load_case=_load_case,
)
_VECTOR_POLYGON_CASE_PARAMS = build_case_params(
    _select_case_metadata(
        category="vector",
        geometry_type="Polygon",
        extra_filter=_is_valid_geometry_case,
    ),
    load_case=_load_case,
)
_RASTER_CASE_PARAMS = build_case_params(
    _select_case_metadata(category="raster"),
    load_case=_load_case,
)

# All cases params (for tests that handle invalid/empty)
# Note: still excludes cases that can't be loaded (expect_loadable: false)
_VECTOR_POINT_ALL_PARAMS = build_case_params(
    _select_case_metadata(
        category="vector",
        geometry_type="Point",
        extra_filter=_is_loadable_case,
    ),
    load_case=_load_case,
)
_VECTOR_POLYGON_ALL_PARAMS = build_case_params(
    _select_case_metadata(
        category="vector",
        geometry_type="Polygon",
        extra_filter=_is_loadable_case,
    ),
    load_case=_load_case,
)

# Invalid geometry params (for tests that verify rejection of invalid input)
# These cases should cause _perfect functions to raise ValueError
_INVALID_POLYGON_PARAMS = build_case_params(
    _select_case_metadata(
        category="vector",
        geometry_type="Polygon",
        extra_filter=_is_invalid_geometry_case,
    ),
    load_case=_load_case,
)
_INVALID_POINT_PARAMS = build_case_params(
    _select_case_metadata(
        category="vector",
        geometry_type="Point",
        extra_filter=_is_invalid_geometry_case,
    ),
    load_case=_load_case,
)
_INVALID_LINESTRING_PARAMS = build_case_params(
    _select_case_metadata(
        category="vector",
        geometry_type="LineString",
        extra_filter=_is_invalid_geometry_case,
    ),
    load_case=_load_case,
)


def _load_unique_case(**selection_kwargs: Any) -> Any:
    """Load exactly one case selected from metadata criteria."""
    return _load_selected_case(**selection_kwargs)


def _load_unique_geometry(**selection_kwargs: Any):
    """Load exactly one geometry fixture selected from metadata criteria."""
    return unary_union(list(_load_unique_case(**selection_kwargs).load().geometry))


def _baseline_polygon_case() -> Any:
    return _load_unique_case(
        category="vector",
        geometry_type="Polygon",
        tags_all=["valid", "baseline"],
        risk_types_any=["none"],
    )


def _baseline_polygon_geometry():
    return _load_unique_geometry(
        category="vector",
        geometry_type="Polygon",
        tags_all=["valid", "baseline"],
        risk_types_any=["none"],
    )


def _polygon_with_hole_geometry():
    return _load_unique_geometry(
        category="vector",
        geometry_type="Polygon",
        tags_all=["hole", "interior_ring"],
    )


def _empty_polygon_geometry():
    return _load_unique_geometry(
        category="vector",
        geometry_type="Polygon",
        tags_all=["empty", "baseline"],
    )


def _self_intersecting_polygon_geometry():
    return _load_unique_geometry(
        category="vector",
        geometry_type="Polygon",
        tags_all=["invalid", "self_intersection"],
    )


def _spike_invalid_polygon_geometry():
    return _load_unique_geometry(
        category="vector",
        geometry_type="Polygon",
        tags_all=["invalid", "spike", "repair"],
    )


def _dateline_polygon_geometry():
    return _load_unique_geometry(
        category="vector",
        geometry_type="Polygon",
        tags_all=["dateline", "crs"],
        extra_filter=lambda meta: bool(meta.params.get("crosses_dateline")),
    )


def _classic_antimeridian_polygon_geometry():
    return _load_unique_geometry(
        category="vector",
        geometry_type="Polygon",
        tags_all=["dateline", "antimeridian"],
        extra_filter=lambda meta: "crs" not in meta.tags,
    )


def _disjoint_polygons_case() -> Any:
    return _load_unique_case(
        category="vector",
        geometry_type="Polygon",
        tags_all=["multipart", "topology"],
        risk_types_any=["overaggressive_dissolve"],
    )


def _utm_polygon_case() -> Any:
    return _load_unique_case(
        category="vector",
        geometry_type="Polygon",
        tags_all=["utm"],
        extra_filter=lambda meta: meta.crs == "EPSG:4326" and "special-case" not in meta.tags,
    )


def _svalbard_polygon_case() -> Any:
    return _load_unique_case(
        category="vector",
        geometry_type="Polygon",
        tags_all=["utm", "special-case"],
    )


def _wrapped_longitude_point_case() -> Any:
    return _load_unique_case(
        category="vector",
        geometry_type="Point",
        tags_all=["longitude_wrapping", "reprojection"],
    )


def _dateline_points_pair_case() -> Any:
    return _load_unique_case(
        category="vector",
        geometry_type="Point",
        tags_all=["dateline", "antimeridian", "clustering"],
    )


def _nearby_points_cluster_case() -> Any:
    return _load_unique_case(
        category="vector",
        geometry_type="Point",
        tags_all=["clustering", "baseline"],
    )


def _dateline_chain_cluster_case() -> Any:
    return _load_unique_case(
        category="vector",
        geometry_type="Point",
        tags_all=["dateline", "clustering", "transitive_connectivity"],
    )


def _utm_boundary_raster_case() -> Any:
    return _load_unique_case(
        category="raster",
        tags_all=["utm", "boundary", "reprojection"],
    )


def _nodata_raster_case() -> Any:
    return _load_unique_case(
        category="raster",
        tags_all=["nodata", "masking"],
    )


def _shifted_nodata_raster_case() -> Any:
    return _load_unique_case(
        category="raster",
        tags_all=["nodata", "alignment", "affine_transform"],
    )


def _rotated_raster_case() -> Any:
    return _load_unique_case(
        category="raster",
        tags_all=["rotated"],
    )


def _rasterize_match_wgs84_polygon_geometry():
    return _load_unique_geometry(
        category="vector",
        geometry_type="Polygon",
        tags_all=["rasterization", "reprojection"],
        extra_filter=lambda meta: meta.crs == "EPSG:4326",
    )


def _rasterize_match_utm_polygon_geometry():
    return _load_unique_geometry(
        category="vector",
        geometry_type="Polygon",
        tags_all=["rasterization", "utm"],
        extra_filter=lambda meta: meta.crs == "EPSG:32633",
    )


def _first_valid_pixel(src: Any) -> tuple[int, int, float]:
    """Return the first unmasked raster pixel and its value."""
    data = src.read(1, masked=True)
    mask = data.mask

    if not hasattr(mask, "shape") or getattr(mask, "shape", ()) == ():
        return 0, 0, data[0, 0].item()

    for row in range(data.shape[0]):
        for col in range(data.shape[1]):
            if not mask[row, col]:
                return row, col, data[row, col].item()

    raise ValueError("Raster contains no valid sample pixels.")


def _longitude_delta(lon_a: float, lon_b: float) -> float:
    """Return the wrapped longitudinal difference in degrees."""
    return abs(((lon_a - lon_b + 180.0) % 360.0) - 180.0)


# Question 1: Reproject a point
def test_reproject_point_roundtrips_dateline_case() -> None:
    """Question 1: round-trip a dateline case point across EPSG:3857."""
    geom = _dateline_polygon_geometry()
    point = geom.representative_point()

    x, y = reproject_point(point.x, point.y, 4326, 3857)
    lon, lat = reproject_point(x, y, 3857, 4326)

    assert math.isfinite(x)
    assert math.isfinite(y)
    assert _longitude_delta(lon, point.x) < 1e-6
    assert lat == pytest.approx(point.y, abs=1e-6)


def test_reproject_point_identity_for_same_crs() -> None:
    """Question 1: keep coordinates unchanged when source and target CRS match."""
    geom = unary_union(list(_utm_polygon_case().load().geometry))
    point = geom.representative_point()
    x, y = reproject_point(point.x, point.y, 4326, 4326)

    assert x == pytest.approx(point.x)
    assert y == pytest.approx(point.y)


def test_reproject_point_normalizes_wrapped_longitude_fixture() -> None:
    """Question 1: expose missing longitude normalization for the wrapped-point GeoCase fixture."""
    case = _wrapped_longitude_point_case()
    point = case.load().geometry.iloc[0]

    lon, lat = reproject_point(point.x, point.y, 4326, 4326)

    assert lon == pytest.approx(case.params["normalized_lon"])
    assert lat == pytest.approx(case.params["source_lat"])


def test_reproject_point_perfect_normalizes_wrapped_longitude() -> None:
    """Question 1 perfect: normalize wrapped geographic longitudes back into the usual range."""
    geom = _dateline_polygon_geometry()
    point = geom.representative_point()
    wrapped_lon = point.x if point.x >= 0.0 else point.x + 360.0

    lon, lat = reproject_point_perfect(wrapped_lon, point.y, 4326, 4326)

    assert -180.0 <= lon <= 180.0
    assert _longitude_delta(lon, point.x) < 1e-6
    assert lat == pytest.approx(point.y, abs=1e-6)


def test_reproject_point_perfect_normalizes_wrapped_longitude_fixture() -> None:
    """Question 1 perfect: normalize the dedicated wrapped-longitude GeoCase point."""
    case = _wrapped_longitude_point_case()
    point = case.load().geometry.iloc[0]

    lon, lat = reproject_point_perfect(point.x, point.y, 4326, 4326)

    assert lon == pytest.approx(case.params["normalized_lon"])
    assert lat == pytest.approx(case.params["source_lat"])


@pytest.mark.parametrize("geocase", _VECTOR_POINT_CASE_PARAMS)
def test_reproject_point_handles_all_point_cases(geocase: Any) -> None:
    """Question 1: discover which bundled point fixtures break simple identity reprojection."""
    gdf = geocase.load()
    assert geocase.metadata.crs is not None

    src_epsg = CRS.from_user_input(geocase.metadata.crs).to_epsg()
    assert src_epsg is not None

    for point in gdf.geometry:
        x, y = reproject_point(point.x, point.y, src_epsg, src_epsg)
        assert math.isfinite(x)
        assert math.isfinite(y)
        if src_epsg == 4326:
            assert -180.0 <= x <= 180.0


@pytest.mark.parametrize("geocase", _VECTOR_POINT_CASE_PARAMS)
def test_reproject_point_perfect_handles_all_point_cases(geocase: Any) -> None:
    """Question 1 perfect: keep identity reprojection stable across bundled point fixtures."""
    gdf = geocase.load()
    assert geocase.metadata.crs is not None

    src_epsg = CRS.from_user_input(geocase.metadata.crs).to_epsg()
    assert src_epsg is not None

    for point in gdf.geometry:
        x, y = reproject_point_perfect(point.x, point.y, src_epsg, src_epsg)
        assert math.isfinite(x)
        assert math.isfinite(y)
        if src_epsg == 4326:
            assert -180.0 <= x <= 180.0


# Question 2: Check whether a point lies inside a polygon
def test_point_in_polygon_respects_hole_from_geocase() -> None:
    """Question 2: confirm points inside holes are excluded."""
    geom = _polygon_with_hole_geometry()
    assert isinstance(geom, Polygon)

    polygon_point = geom.representative_point()
    hole_polygon = Polygon(list(geom.interiors[0].coords))
    hole_point = hole_polygon.representative_point()

    assert point_in_polygon(polygon_point.wkt, geom.wkt) is True
    assert point_in_polygon(hole_point.wkt, geom.wkt) is False


def test_point_in_polygon_handles_simple_inside_and_outside_points() -> None:
    """Question 2: accept interior points and reject exterior ones for a simple polygon."""
    polygon = _baseline_polygon_geometry()
    inside_point = polygon.representative_point()
    minx, miny, maxx, maxy = polygon.bounds
    width = maxx - minx
    height = maxy - miny
    outside_point = Point(maxx + width, maxy + height)

    assert point_in_polygon(inside_point.wkt, polygon.wkt) is True
    assert point_in_polygon(outside_point.wkt, polygon.wkt) is False


def test_point_in_polygon_excludes_boundary_point() -> None:
    """Question 2: expose boundary-inclusion behavior in the original helper."""
    polygon = _baseline_polygon_geometry()
    assert isinstance(polygon, Polygon)
    boundary_point = Point(list(polygon.exterior.coords)[0])

    assert point_in_polygon(boundary_point.wkt, polygon.wkt) is False


def test_point_in_polygon_perfect_excludes_boundary_point() -> None:
    """Question 2 perfect: treat boundary points as outside strict interior checks."""
    polygon = _baseline_polygon_geometry()
    assert isinstance(polygon, Polygon)
    boundary_point = Point(list(polygon.exterior.coords)[0])

    assert point_in_polygon_perfect(boundary_point.wkt, polygon.wkt) is False


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_CASE_PARAMS)
def test_point_in_polygon_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 2: confirm simple point-in-polygon works across bundled polygon fixtures."""
    geom = _load_selected_geometry(geocase)
    if geom.is_empty:
        pytest.skip("Empty polygon fixtures have no interior representative point.")

    point = geom.representative_point()
    assert point_in_polygon(point.wkt, geom.wkt) is True


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_ALL_PARAMS)
def test_point_in_polygon_perfect_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 2 perfect: confirm robust point-in-polygon works across bundled polygon fixtures."""
    geom = _load_selected_geometry(geocase)
    if geom.is_empty:
        pytest.skip("Empty polygon fixtures have no interior representative point.")

    point = geom.representative_point()
    assert point_in_polygon_perfect(point.wkt, geom.wkt) is True


# Question 3: Compute the bounding box of a geometry
def test_get_bbox_returns_ordered_bounds_for_simple_case() -> None:
    """Question 3: verify normal bounds ordering for a simple polygon."""
    geom = _baseline_polygon_geometry()

    minx, miny, maxx, maxy = get_bbox(geom)

    assert minx < maxx
    assert miny < maxy


def test_get_bbox_matches_expected_bounds_for_manual_polygon() -> None:
    """Question 3: return exact bounds stored in GeoCase metadata."""
    case = _baseline_polygon_case()
    geom = case.load().geometry.iloc[0]
    expected_bounds = tuple(case.params["expected_bounds"])

    assert get_bbox(geom) == pytest.approx(expected_bounds)


def test_get_bbox_normalizes_dateline_crossing_span() -> None:
    """Question 3: expose overly wide bounds for a dateline-crossing polygon."""
    geom = _dateline_polygon_geometry()

    minx, _, maxx, _ = get_bbox(geom)

    assert (maxx - minx) <= 180.0


def test_get_bbox_classic_antimeridian_polygon_uses_minimal_span() -> None:
    """Question 3: expose over-wide raw bounds on a classic wrapped dateline polygon."""
    geom = _classic_antimeridian_polygon_geometry()

    minx, _, maxx, _ = get_bbox(geom)

    assert (maxx - minx) <= 180.0


def test_get_bbox_perfect_classic_antimeridian_polygon_uses_minimal_span() -> None:
    """Question 3 perfect: normalize classic wrapped dateline polygons to a compact span."""
    geom = _classic_antimeridian_polygon_geometry()

    minx, _, maxx, _ = get_bbox_perfect(geom)

    assert (maxx - minx) <= 180.0


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_CASE_PARAMS)
def test_get_bbox_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 3: discover which bundled polygon fixtures break the simple bbox helper."""
    geom = unary_union(list(geocase.load().geometry))
    minx, miny, maxx, maxy = get_bbox(geom)

    assert all(math.isfinite(value) for value in (minx, miny, maxx, maxy))
    if not geom.is_empty and geocase.metadata.crs == "EPSG:4326":
        assert (maxx - minx) <= 180.0


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_ALL_PARAMS)
def test_get_bbox_perfect_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 3 perfect: keep bbox handling correct across bundled polygon fixtures."""
    geom = unary_union(list(geocase.load().geometry))

    if not geom.is_valid:
        with pytest.raises(ValueError, match="valid"):
            get_bbox_perfect(geom)
        return

    minx, miny, maxx, maxy = get_bbox_perfect(geom)

    assert all(math.isfinite(value) for value in (minx, miny, maxx, maxy))
    if not geom.is_empty and geocase.metadata.crs == "EPSG:4326":
        assert (maxx - minx) <= 180.0


# Question 4: Buffer a geometry in metres
def test_buffer_in_meters_expands_polygon_with_hole() -> None:
    """Question 4: check that metric buffering expands the geometry."""
    geom = _polygon_with_hole_geometry()

    buffered = buffer_in_meters(geom, 500.0)

    assert not buffered.is_empty
    assert buffered.is_valid
    assert buffered.area > geom.area
    assert buffered.covers(geom.representative_point())


def test_buffer_in_meters_returns_empty_geometry_unchanged() -> None:
    """Question 4: keep an empty geometry empty when buffering."""
    empty_polygon = _empty_polygon_geometry()

    buffered = buffer_in_meters(empty_polygon, 100.0)

    assert buffered.is_empty


def test_buffer_in_meters_keeps_dateline_polygon_valid() -> None:
    """Question 4: expose buffering instability on dateline-crossing polygons."""
    geom = _dateline_polygon_geometry()

    buffered = buffer_in_meters(geom, 10_000.0)

    assert buffered.is_valid


def test_buffer_in_meters_perfect_keeps_dateline_polygon_valid() -> None:
    """Question 4 perfect: keep a dateline-crossing polygon valid after buffering."""
    geom = _dateline_polygon_geometry()

    buffered = buffer_in_meters_perfect(geom, 10_000.0)

    assert not buffered.is_empty
    assert buffered.is_valid
    assert buffered.area > geom.area


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_CASE_PARAMS)
def test_buffer_in_meters_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 4: discover which bundled polygon fixtures break the simple buffer helper."""
    context = describe_case_data(geocase)
    geom = unary_union(list(geocase.load().geometry))
    buffered = buffer_in_meters(geom, 1_000.0)

    if geom.is_empty:
        assert buffered.is_empty, failure_context(geocase, "Expected buffering to preserve empty geometry")
    else:
        assert not buffered.is_empty, f"Expected non-empty buffered output [{context}]"
        assert buffered.is_valid, f"Expected valid buffered output [{context}]"


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_ALL_PARAMS)
def test_buffer_in_meters_perfect_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 4 perfect: keep buffering correct across bundled polygon fixtures."""
    geom = _load_selected_geometry(geocase)

    if not geom.is_valid:
        with pytest.raises(ValueError, match="valid"):
            buffer_in_meters_perfect(geom, 1_000.0)
        return

    buffered = buffer_in_meters_perfect(geom, 1_000.0)

    if geom.is_empty:
        assert buffered.is_empty
    else:
        assert not buffered.is_empty
        assert buffered.is_valid


# Question 5: Find the UTM EPSG code from longitude/latitude
def test_get_utm_epsg_flips_across_antimeridian_edges() -> None:
    """Question 5: verify UTM zone selection near the antimeridian."""
    point_case = _dateline_points_pair_case()
    gdf = point_case.load()
    points = sorted(gdf.geometry, key=lambda geom: geom.x)
    west_point, east_point = points[0], points[-1]

    west_epsg = get_utm_epsg(west_point.x, west_point.y)
    east_epsg = get_utm_epsg(east_point.x, east_point.y)

    assert west_epsg == point_case.params["expected_west_utm_epsg"]
    assert east_epsg == point_case.params["expected_east_utm_epsg"]


def test_get_utm_epsg_returns_expected_zone_for_central_europe() -> None:
    """Question 5: return the expected EPSG for a standard northern UTM location."""
    case = _utm_polygon_case()
    geom = case.load().geometry.iloc[0]
    point = geom.representative_point()

    assert get_utm_epsg(point.x, point.y) == case.params["expected_utm_epsg"]


def test_get_utm_epsg_handles_svalbard_special_zone() -> None:
    """Question 5: expose missing Svalbard special-zone handling in the original helper."""
    case = _svalbard_polygon_case()
    point = case.load().geometry.iloc[0].representative_point()

    assert get_utm_epsg(point.x, point.y) == case.params["expected_utm_epsg"]


def test_get_utm_epsg_perfect_handles_svalbard_special_zone() -> None:
    """Question 5 perfect: apply Svalbard special-zone logic correctly."""
    case = _svalbard_polygon_case()
    point = case.load().geometry.iloc[0].representative_point()

    assert get_utm_epsg_perfect(point.x, point.y) == case.params["expected_utm_epsg"]


def test_get_utm_epsg_handles_all_utm_polygon_cases() -> None:
    """Question 5: discover which UTM-tagged polygon fixtures break simple zone lookup."""
    matches = _select_bundled_vector_cases(
        category="vector",
        geometry_type="Polygon",
        tags_any=["utm"],
    )
    assert matches
    tested = 0

    for meta in matches:
        if meta.crs != "EPSG:4326":
            continue
        geom = _load_geometry(meta.id)
        point = geom.representative_point()
        assert get_utm_epsg(point.x, point.y) == meta.params["expected_utm_epsg"], (
            failure_context(meta, "UTM lookup returned an unexpected EPSG code")
        )
        tested += 1

    assert tested > 0


def test_get_utm_epsg_perfect_handles_all_utm_polygon_cases() -> None:
    """Question 5 perfect: keep UTM-tagged polygon fixtures correct without handpicking ids."""
    matches = _select_bundled_vector_cases(
        category="vector",
        geometry_type="Polygon",
        tags_any=["utm"],
    )
    assert matches
    tested = 0

    for meta in matches:
        if meta.crs != "EPSG:4326":
            continue
        geom = _load_geometry(meta.id)
        point = geom.representative_point()
        assert get_utm_epsg_perfect(point.x, point.y) == meta.params["expected_utm_epsg"]
        tested += 1

    assert tested > 0


# Question 6: Calculate polygon area in square metres
def test_area_m2_detects_hole_area_loss() -> None:
    """Question 6: ensure holes reduce the measured polygon area."""
    geom = _polygon_with_hole_geometry()
    assert isinstance(geom, Polygon)

    shell_only = Polygon(list(geom.exterior.coords))

    assert area_m2(geom) > 0.0
    assert area_m2(shell_only) > area_m2(geom)


def test_area_m2_returns_zero_for_empty_polygon() -> None:
    """Question 6: return zero area for an empty polygon."""
    assert area_m2(_empty_polygon_geometry()) == 0.0


def test_area_m2_rejects_invalid_self_intersection() -> None:
    """Question 6: expose acceptance of invalid self-intersecting polygons."""
    geom = _self_intersecting_polygon_geometry()

    with pytest.raises((TypeError, ValueError)):
        area_m2(geom)


def test_area_m2_perfect_rejects_invalid_self_intersection() -> None:
    """Question 6 perfect: reject invalid self-intersecting polygons explicitly."""
    geom = _self_intersecting_polygon_geometry()

    with pytest.raises(ValueError, match="valid"):
        area_m2_perfect(geom)


def test_area_m2_perfect_matches_baseline_on_valid_polygon() -> None:
    """Question 6 perfect: match the baseline area result for valid input."""
    geom = _polygon_with_hole_geometry()

    assert area_m2_perfect(geom) == pytest.approx(area_m2(geom))


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_ALL_PARAMS)
def test_area_m2_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 6: discover which bundled polygon fixtures break simple area measurement."""
    geom = _load_selected_geometry(geocase)
    context = describe_case_data(geocase)

    if geom.is_empty:
        assert area_m2(geom) == 0.0, f"Expected empty geometry to have zero area [{context}]"
    elif not geom.is_valid:
        try:
            area_m2(geom)
        except (TypeError, ValueError):
            return
        pytest.fail(f"Expected invalid geometry to be rejected [{context}]")
    else:
        assert area_m2(geom) > 0.0, f"Expected valid polygon to have positive area [{context}]"


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_ALL_PARAMS)
def test_area_m2_perfect_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 6 perfect: keep area measurement behavior explicit across polygon fixtures."""
    geom = _load_selected_geometry(geocase)

    if geom.is_empty:
        assert area_m2_perfect(geom) == 0.0
    elif not geom.is_valid:
        with pytest.raises(ValueError, match="valid"):
            area_m2_perfect(geom)
    else:
        assert area_m2_perfect(geom) > 0.0


# Question 7: Merge overlapping polygons
def test_dissolve_polygons_merges_shifted_overlap() -> None:
    """Question 7: confirm overlapping polygons dissolve into one part."""
    geom = _baseline_polygon_geometry()
    shifted = translate(geom, xoff=0.05, yoff=0.05)

    dissolved = dissolve_polygons([geom, shifted])

    assert len(dissolved) == 1
    assert dissolved[0].area < geom.area + shifted.area


def test_dissolve_polygons_preserves_disjoint_parts() -> None:
    """Question 7: keep disjoint polygons as separate dissolved parts."""
    gdf = _disjoint_polygons_case().load()
    polygon_a, polygon_b = list(gdf.geometry)

    dissolved = dissolve_polygons([polygon_a, polygon_b])

    assert len(dissolved) == 2


def test_dissolve_polygons_repairs_invalid_inputs_before_union() -> None:
    """Question 7: expose dissolve failures on invalid polygon inputs."""
    invalid_geom = _self_intersecting_polygon_geometry()
    valid_geom = _baseline_polygon_geometry()

    dissolved = dissolve_polygons([invalid_geom, valid_geom])

    assert dissolved
    assert all(part.is_valid for part in dissolved)


def test_dissolve_polygons_perfect_repairs_invalid_inputs_before_union() -> None:
    """Question 7 perfect: repair invalid polygons before dissolving them."""
    invalid_geom = _self_intersecting_polygon_geometry()
    valid_geom = _baseline_polygon_geometry()

    dissolved = dissolve_polygons_perfect([invalid_geom, valid_geom])

    assert dissolved
    assert all(part.is_valid for part in dissolved)
    assert all(part.geom_type == "Polygon" for part in dissolved)


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_ALL_PARAMS)
def test_dissolve_polygons_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 7: discover which bundled polygon fixtures break simple dissolve logic."""
    context = describe_case_data(geocase)
    polygons = list(geocase.load().geometry)
    try:
        dissolved = dissolve_polygons(polygons)
    except Exception as exc:
        raise AssertionError(f"Dissolve raised an exception [{context}]") from exc

    if all(geom.is_empty for geom in polygons):
        assert dissolved == [], f"Expected empty polygon inputs to dissolve to an empty list [{context}]"
    else:
        assert dissolved, f"Expected dissolved output for non-empty polygons [{context}]"
        assert all(part.geom_type in {"Polygon", "MultiPolygon"} for part in dissolved), (
            f"Expected polygonal dissolved output [{context}]"
        )
        assert all(part.is_valid for part in dissolved), f"Expected valid dissolved output [{context}]"


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_ALL_PARAMS)
def test_dissolve_polygons_perfect_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 7 perfect: keep dissolve behavior stable across bundled polygon fixtures."""
    polygons = list(geocase.load().geometry)
    dissolved = dissolve_polygons_perfect(polygons)

    if all(geom.is_empty for geom in polygons):
        assert dissolved == []
    else:
        assert dissolved
        assert all(part.geom_type == "Polygon" for part in dissolved)
        assert all(part.is_valid for part in dissolved)


# Question 8: Clip a raster by a bounding box
def test_clip_raster_creates_smaller_subset(tmp_path: Path) -> None:
    """Question 8: verify clipping produces a smaller raster subset."""
    raster_case = _utm_boundary_raster_case()
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
    raster_case = _nodata_raster_case()
    output_path = tmp_path / "clipped_nodata_small.tif"

    with rasterio.open(raster_case.primary_path) as src:
        left, bottom, right, top = src.bounds
        bbox = (left, bottom + (top - bottom) * 0.5, right, top)

    clip_raster(str(raster_case.primary_path), str(output_path), bbox)

    with rasterio.open(output_path) as clipped:
        assert clipped.count == 1
        assert clipped.width > 0
        assert clipped.height > 0


def test_clip_raster_accepts_wgs84_bbox_for_projected_raster(tmp_path: Path) -> None:
    """Question 8: expose CRS assumptions when clipping a projected raster with WGS84 bounds."""
    raster_case = _utm_boundary_raster_case()
    vector_geom = _rasterize_match_wgs84_polygon_geometry()
    output_path = tmp_path / "clipped_wgs84_bbox_original.tif"

    clip_raster(str(raster_case.primary_path), str(output_path), vector_geom.bounds)

    with rasterio.open(output_path) as clipped:
        assert clipped.width > 1
        assert clipped.height > 1


def test_clip_raster_perfect_accepts_wgs84_bbox_for_projected_raster(tmp_path: Path) -> None:
    """Question 8 perfect: reproject a WGS84 bbox before clipping a projected raster."""
    raster_case = _utm_boundary_raster_case()
    vector_geom = _rasterize_match_wgs84_polygon_geometry()
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


@pytest.mark.parametrize("geocase", _RASTER_CASE_PARAMS)
def test_clip_raster_handles_all_raster_cases(geocase: Any, tmp_path: Path) -> None:
    """Question 8: clip every bundled raster with an in-bounds box chosen by category."""
    output_path = tmp_path / f"{geocase.id}_clip_simple.tif"

    with rasterio.open(geocase.primary_path) as src:
        if src.transform.b != 0.0 or src.transform.d != 0.0:
            pytest.skip("Rotated rasters are outside the helper's axis-aligned clipping contract.")
        left, bottom, right, top = src.bounds
        bbox = (
            left + (right - left) * 0.2,
            bottom + (top - bottom) * 0.2,
            right - (right - left) * 0.2,
            top - (top - bottom) * 0.2,
        )
        original_width = src.width
        original_height = src.height

    clip_raster(str(geocase.primary_path), str(output_path), bbox)

    with rasterio.open(output_path) as clipped:
        assert 0 < clipped.width <= original_width
        assert 0 < clipped.height <= original_height


@pytest.mark.parametrize("geocase", _RASTER_CASE_PARAMS)
def test_clip_raster_perfect_handles_all_raster_cases(geocase: Any, tmp_path: Path) -> None:
    """Question 8 perfect: clip every bundled raster with the robust helper too."""
    output_path = tmp_path / f"{geocase.id}_clip_perfect.tif"

    with rasterio.open(geocase.primary_path) as src:
        if src.transform.b != 0.0 or src.transform.d != 0.0:
            pytest.skip("Rotated rasters are outside the helper's axis-aligned clipping contract.")
        left, bottom, right, top = src.bounds
        bbox = (
            left + (right - left) * 0.2,
            bottom + (top - bottom) * 0.2,
            right - (right - left) * 0.2,
            top - (top - bottom) * 0.2,
        )
        original_width = src.width
        original_height = src.height

    clip_raster_perfect(str(geocase.primary_path), str(output_path), bbox)

    with rasterio.open(output_path) as clipped:
        assert 0 < clipped.width <= original_width
        assert 0 < clipped.height <= original_height


def _rotated_raster_clip_bbox(src: Any) -> tuple[float, float, float, float]:
    """An inset, axis-aligned bbox (raster CRS) for the rotated fixture."""
    left, bottom, right, top = src.bounds
    return (
        left + (right - left) * 0.2,
        bottom + (top - bottom) * 0.2,
        right - (right - left) * 0.2,
        top - (top - bottom) * 0.2,
    )


def test_clip_raster_fails_on_rotated_geotransform(tmp_path: Path) -> None:
    """Question 8: the naive helper cannot clip a rotated raster.

    gdal.Translate's -projWin rejects a geotransform with rotation/skew
    terms, so the simple answer raises on the rotated_two_islands fixture.
    """
    raster_case = _rotated_raster_case()
    output_path = tmp_path / "clipped_rotated_simple.tif"

    with rasterio.open(raster_case.primary_path) as src:
        assert src.transform.b != 0.0 or src.transform.d != 0.0
        bbox = _rotated_raster_clip_bbox(src)

    with pytest.raises(RuntimeError):
        clip_raster(str(raster_case.primary_path), str(output_path), bbox)


def test_clip_raster_perfect_handles_rotated_geotransform(tmp_path: Path) -> None:
    """Question 8 perfect: warp-based fallback clips a rotated raster.

    The robust helper detects the rotated geotransform and falls back to
    gdal.Warp with an output extent, resampling onto an axis-aligned grid.
    """
    raster_case = _rotated_raster_case()
    output_path = tmp_path / "clipped_rotated_perfect.tif"

    with rasterio.open(raster_case.primary_path) as src:
        assert src.transform.b != 0.0 or src.transform.d != 0.0
        bbox = _rotated_raster_clip_bbox(src)
        original_width = src.width
        original_height = src.height
        source_crs = src.crs

    clip_raster_perfect(str(raster_case.primary_path), str(output_path), bbox)

    with rasterio.open(output_path) as clipped:
        assert 0 < clipped.width <= original_width
        assert 0 < clipped.height <= original_height
        assert clipped.crs == source_crs
        # The warped output is axis-aligned even though the source was rotated.
        assert clipped.transform.b == 0.0 and clipped.transform.d == 0.0


# Question 9: Convert raster pixel coordinates to geographic coordinates
def test_pixel_to_world_matches_gdal_geotransform() -> None:
    """Question 9: match pixel-to-world output to the dataset geotransform."""
    from osgeo import gdal

    raster_case = _nodata_raster_case()
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

    raster_case = _nodata_raster_case()
    dataset = gdal.Open(str(raster_case.primary_path))

    assert dataset is not None

    gt = dataset.GetGeoTransform()
    x, y = pixel_to_world(dataset, 0, 0)

    assert x == pytest.approx(gt[0])
    assert y == pytest.approx(gt[3])

    dataset = None


def test_pixel_to_world_returns_pixel_center_coordinates() -> None:
    """Question 9: expose corner-versus-center ambiguity for pixel coordinates."""
    from osgeo import gdal

    raster_case = _nodata_raster_case()
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

    raster_case = _nodata_raster_case()
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


@pytest.mark.parametrize("geocase", _RASTER_CASE_PARAMS)
def test_pixel_to_world_handles_all_raster_cases(geocase: Any) -> None:
    """Question 9: match simple pixel-to-world math across bundled raster fixtures."""
    from osgeo import gdal

    dataset = gdal.Open(str(geocase.primary_path))
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


@pytest.mark.parametrize("geocase", _RASTER_CASE_PARAMS)
def test_pixel_to_world_perfect_handles_all_raster_cases(geocase: Any) -> None:
    """Question 9 perfect: return pixel centers across bundled raster fixtures."""
    from osgeo import gdal

    dataset = gdal.Open(str(geocase.primary_path))
    assert dataset is not None

    row = dataset.RasterYSize // 2
    col = dataset.RasterXSize // 2

    with rasterio.open(geocase.primary_path) as src:
        expected_x, expected_y = src.xy(row, col)

    observed_x, observed_y = pixel_to_world_perfect(dataset, row, col)

    assert observed_x == pytest.approx(expected_x)
    assert observed_y == pytest.approx(expected_y)

    dataset = None


# Question 10: Detect whether two rasters are aligned
def test_rasters_aligned_detects_clipped_output_as_not_aligned(tmp_path: Path) -> None:
    """Question 10: detect that a clipped raster no longer aligns."""
    from osgeo import gdal

    raster_case = _nodata_raster_case()
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


def test_rasters_aligned_accepts_shifted_raster_on_same_pixel_lattice() -> None:
    """Question 10: expose overly strict alignment checks for a one-pixel-shifted GeoCase raster."""
    from osgeo import gdal

    base_case = _nodata_raster_case()
    shifted_case = _shifted_nodata_raster_case()

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

    raster_case = _nodata_raster_case()
    dataset = gdal.Open(str(raster_case.primary_path))

    assert dataset is not None

    mem_copy = gdal.GetDriverByName("MEM").CreateCopy("", dataset)

    assert rasters_aligned_perfect(dataset, mem_copy) is True

    dataset = None
    mem_copy = None


def test_rasters_aligned_perfect_accepts_shifted_raster_on_same_pixel_lattice() -> None:
    """Question 10 perfect: accept GeoCase rasters aligned on the same pixel lattice with a one-pixel shift."""
    from osgeo import gdal

    base_case = _nodata_raster_case()
    shifted_case = _shifted_nodata_raster_case()

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

    raster_case = _nodata_raster_case()
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


@pytest.mark.parametrize("geocase", _RASTER_CASE_PARAMS)
def test_rasters_aligned_handles_all_raster_cases(geocase: Any) -> None:
    """Question 10: confirm simple alignment accepts identical raster datasets."""
    from osgeo import gdal

    dataset = gdal.Open(str(geocase.primary_path))
    assert dataset is not None

    assert rasters_aligned(dataset, dataset) is True

    dataset = None


@pytest.mark.parametrize("geocase", _RASTER_CASE_PARAMS)
def test_rasters_aligned_perfect_handles_all_raster_cases(geocase: Any) -> None:
    """Question 10 perfect: confirm robust alignment accepts identical raster datasets."""
    from osgeo import gdal

    dataset = gdal.Open(str(geocase.primary_path))
    assert dataset is not None

    mem_copy = gdal.GetDriverByName("MEM").CreateCopy("", dataset)

    assert rasters_aligned_perfect(dataset, mem_copy) is True

    dataset = None
    mem_copy = None


# Question 11: Reproject a geometry
def test_reproject_geometry_keeps_dateline_case_non_empty() -> None:
    """Question 11: confirm reprojection keeps the dateline geometry usable."""
    geom = _dateline_polygon_geometry()

    projected = reproject_geometry(geom, 4326, 3857)

    assert not projected.is_empty
    assert all(math.isfinite(value) for value in projected.bounds)


def test_reproject_geometry_identity_preserves_simple_polygon() -> None:
    """Question 11: preserve geometry coordinates when reprojection is identity."""
    geom = _baseline_polygon_geometry()

    projected = reproject_geometry(geom, 4326, 4326)

    assert projected.equals_exact(geom, tolerance=0.0)

@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_CASE_PARAMS)
def test_reproject_geometry_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 11: discover which bundled polygon fixtures break the simple helper."""
    context = describe_case_data(geocase)
    geom = unary_union(list(geocase.load().geometry))
    assert geocase.metadata.crs is not None

    src_epsg = CRS.from_user_input(geocase.metadata.crs).to_epsg()
    assert src_epsg is not None

    projected = reproject_geometry(geom, src_epsg, src_epsg)

    if geom.is_empty:
        assert projected.is_empty, f"Expected empty geometry to remain empty after identity reprojection [{context}]"
    else:
        assert projected.geom_type in {"Polygon", "MultiPolygon"}, (
            f"Expected polygonal output after identity reprojection [{context}]"
        )
        assert not projected.is_empty, f"Expected non-empty output after identity reprojection [{context}]"
        assert all(math.isfinite(value) for value in projected.bounds), (
            f"Expected finite bounds after identity reprojection [{context}]"
        )
        if src_epsg == 4326:
            assert projected.bounds[0] >= -180.0, (
                f"Expected normalized western bound after geographic identity reprojection [{context}]"
            )
            assert projected.bounds[2] <= 180.0, (
                f"Expected normalized eastern bound after geographic identity reprojection [{context}]"
            )


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_ALL_PARAMS)
def test_reproject_geometry_perfect_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 11 perfect: handle nearly all bundled polygon fixtures without handpicking ids."""
    geom = unary_union(list(geocase.load().geometry))
    assert geocase.metadata.crs is not None

    src_epsg = CRS.from_user_input(geocase.metadata.crs).to_epsg()
    assert src_epsg is not None

    if not geom.is_valid:
        with pytest.raises(ValueError, match="valid"):
            reproject_geometry_perfect(geom, src_epsg, src_epsg)
        return

    projected = reproject_geometry_perfect(geom, src_epsg, src_epsg)

    if geom.is_empty:
        assert projected.is_empty
    else:
        assert projected.geom_type in {"Polygon", "MultiPolygon"}
        assert not projected.is_empty
        assert all(math.isfinite(value) for value in projected.bounds)
        if src_epsg == 4326:
            assert projected.bounds[0] >= -180.0
            assert projected.bounds[2] <= 180.0


def test_reproject_geometry_normalizes_dateline_case_longitudes() -> None:
    """Question 11: expose missing longitude normalization for the wrapped dateline polygon."""
    geom = _dateline_polygon_geometry()

    projected = reproject_geometry(geom, 4326, 4326)

    assert projected.bounds[0] >= -180.0
    assert projected.bounds[2] <= 180.0


def test_reproject_geometry_perfect_normalizes_geographic_longitudes() -> None:
    """Question 11 perfect: normalize wrapped longitudes when output stays geographic."""
    geom = _dateline_polygon_geometry()

    projected = reproject_geometry_perfect(geom, 4326, 4326)

    assert not projected.is_empty
    assert projected.is_valid
    assert projected.bounds[0] >= -180.0
    assert projected.bounds[2] <= 180.0


def test_reproject_geometry_perfect_identity_preserves_simple_polygon() -> None:
    """Question 11 perfect: keep already-normalized identity reprojection unchanged."""
    geom = _baseline_polygon_geometry()

    projected = reproject_geometry_perfect(geom, 4326, 4326)

    assert projected.equals_exact(geom, tolerance=0.0)


# Question 12: Find intersections between input polygons and AOIs
def test_find_intersections_reports_overlap() -> None:
    """Question 12: verify overlap reporting includes area and geometry."""
    geom = _baseline_polygon_geometry()
    shifted = translate(geom, xoff=0.05, yoff=0.05)

    intersections = find_intersections([geom], [shifted])

    assert len(intersections) == 1
    assert intersections[0]["candidate_index"] == 0
    assert intersections[0]["aoi_index"] == 0
    assert intersections[0]["intersection_area"] > 0.0
    assert not intersections[0]["intersection_geom"].is_empty


def test_find_intersections_returns_empty_for_disjoint_polygons() -> None:
    """Question 12: return no matches for disjoint polygons."""
    gdf = _disjoint_polygons_case().load()
    polygon_a, polygon_b = list(gdf.geometry)

    assert find_intersections([polygon_a], [polygon_b]) == []


def test_find_intersections_reports_metric_area() -> None:
    """Question 12: expose that intersection area is computed in degrees, not metres."""
    geom = _baseline_polygon_geometry()
    shifted = translate(geom, xoff=0.05, yoff=0.05)

    intersections = find_intersections([geom], [shifted])
    assert len(intersections) == 1

    projected_intersection = reproject_geometry(intersections[0]["intersection_geom"], 4326, 3857)
    expected_area_m2 = projected_intersection.area

    assert intersections[0]["intersection_area"] == pytest.approx(expected_area_m2)


def test_find_intersections_perfect_reports_metric_area() -> None:
    """Question 12 perfect: report overlap area in square metres for WGS84 inputs."""
    geom = _baseline_polygon_geometry()
    shifted = translate(geom, xoff=0.05, yoff=0.05)

    intersections = find_intersections_perfect([geom], [shifted], geom_epsg=4326)
    assert len(intersections) == 1

    expected_area_m2 = area_m2_perfect(intersections[0]["intersection_geom"])

    assert intersections[0]["intersection_area"] == pytest.approx(expected_area_m2)


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_CASE_PARAMS)
def test_find_intersections_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 12: discover which bundled polygon fixtures break simple overlap reporting."""
    geom = _load_selected_geometry(geocase)
    context = describe_case_data(geocase)
    if geom.is_empty:
        assert find_intersections([geom], [geom]) == [], (
            f"Expected empty geometry to yield no intersections [{context}]"
        )
        return

    minx, miny, maxx, maxy = geom.bounds
    dx = max((maxx - minx) * 0.05, 1e-9)
    dy = max((maxy - miny) * 0.05, 1e-9)
    shifted = translate(geom, xoff=dx, yoff=dy)
    try:
        intersections = find_intersections([geom], [shifted])
    except Exception as exc:
        raise AssertionError(f"Intersection lookup raised an exception [{context}]") from exc

    assert intersections, f"Expected overlapping polygons to produce intersections [{context}]"
    assert all(not hit["intersection_geom"].is_empty for hit in intersections), (
        f"Expected non-empty intersection geometries [{context}]"
    )


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_ALL_PARAMS)
def test_find_intersections_perfect_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 12 perfect: keep overlap reporting usable across bundled polygon fixtures."""
    geom = fix_geometry_perfect(_load_selected_geometry(geocase))
    if geom.is_empty:
        assert find_intersections_perfect([geom], [geom]) == []
        return

    minx, miny, maxx, maxy = geom.bounds
    dx = max((maxx - minx) * 0.05, 1e-9)
    dy = max((maxy - miny) * 0.05, 1e-9)
    shifted = translate(geom, xoff=dx, yoff=dy)
    intersections = find_intersections_perfect([geom], [shifted], geom_epsg=4326)

    assert intersections
    assert all(not hit["intersection_geom"].is_empty for hit in intersections)
    assert all(hit["intersection_area"] >= 0.0 for hit in intersections)


# Question 13: Validate a geometry before DB insertion
def test_validate_polygon_geometry_flags_invalid_and_too_small_cases() -> None:
    """Question 13: flag invalid geometry and minimum-area failures."""
    invalid_geom = _self_intersecting_polygon_geometry()
    small_geom = _baseline_polygon_geometry()

    invalid_ok, invalid_errors = validate_polygon_geometry(invalid_geom, min_area_m2=1.0)
    small_ok, small_errors = validate_polygon_geometry(small_geom, min_area_m2=1e20)

    assert invalid_ok is False
    assert any("invalid" in error.lower() for error in invalid_errors)
    assert small_ok is False
    assert any("below minimum" in error.lower() for error in small_errors)


def test_validate_polygon_geometry_accepts_valid_polygon() -> None:
    """Question 13: accept a valid polygon that exceeds the minimum area."""
    geom = _baseline_polygon_geometry()

    ok, errors = validate_polygon_geometry(geom, min_area_m2=1.0)

    assert ok is True
    assert errors == []


def test_validate_polygon_geometry_accepts_repairable_invalid_polygon() -> None:
    """Question 13: expose lack of repair-before-validation for fixable invalid polygons."""
    geom = _self_intersecting_polygon_geometry()

    ok, errors = validate_polygon_geometry(geom, min_area_m2=1.0)

    assert ok is True
    assert errors == []


def test_validate_polygon_geometry_perfect_repairs_invalid_polygon() -> None:
    """Question 13 perfect: repair a fixable invalid polygon before validating it."""
    geom = _self_intersecting_polygon_geometry()

    ok, errors = validate_polygon_geometry_perfect(geom, min_area_m2=1.0)

    assert ok is True
    assert errors == []


def test_validate_polygon_geometry_perfect_accepts_valid_polygon() -> None:
    """Question 13 perfect: keep already-valid polygon inputs accepted."""
    geom = _baseline_polygon_geometry()

    ok, errors = validate_polygon_geometry_perfect(geom, min_area_m2=1.0)

    assert ok is True
    assert errors == []


def test_validate_polygon_geometry_perfect_keeps_minimum_area_check() -> None:
    """Question 13 perfect: still fail polygons that stay below the minimum area."""
    geom = _baseline_polygon_geometry()

    ok, errors = validate_polygon_geometry_perfect(geom, min_area_m2=1e20)

    assert ok is False
    assert any("below minimum" in error.lower() for error in errors)


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_ALL_PARAMS)
def test_validate_polygon_geometry_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 13: discover which bundled polygon fixtures fail simple validation rules."""
    geom = _load_selected_geometry(geocase)
    ok, errors = validate_polygon_geometry(geom, min_area_m2=0.0)

    if geom.is_empty or not geom.is_valid:
        assert ok is False
        assert errors
    else:
        assert ok is True
        assert errors == []


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_ALL_PARAMS)
def test_validate_polygon_geometry_perfect_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 13 perfect: keep validation behavior explicit across bundled polygon fixtures."""
    geom = _load_selected_geometry(geocase)
    ok, errors = validate_polygon_geometry_perfect(geom, min_area_m2=0.0)

    if geom.is_empty:
        assert ok is False
        assert errors
    else:
        repaired = fix_geometry_perfect(geom)
        if repaired.is_empty or not repaired.is_valid or repaired.geom_type not in {"Polygon", "MultiPolygon"}:
            assert ok is False
            assert errors
        else:
            assert ok is True
            assert errors == []


# Question 14: Extract raster value at a geographic point
def test_sample_raster_at_lonlat_matches_center_pixel_value() -> None:
    """Question 14: sample the same value seen at a raster center pixel."""
    from osgeo import gdal

    raster_case = _utm_boundary_raster_case()

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

    raster_case = _nodata_raster_case()

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


def test_sample_raster_at_lonlat_masks_nodata_pixel() -> None:
    """Question 14: expose that the original helper returns the raw NoData sentinel."""
    from osgeo import gdal

    raster_case = _nodata_raster_case()

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

    raster_case = _nodata_raster_case()

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


@pytest.mark.parametrize("geocase", _RASTER_CASE_PARAMS)
def test_sample_raster_at_lonlat_handles_all_raster_cases(geocase: Any) -> None:
    """Question 14: sample a valid pixel from every bundled raster fixture."""
    from osgeo import gdal

    with rasterio.open(geocase.primary_path) as src:
        row, col, expected = _first_valid_pixel(src)
        x, y = src.xy(row, col)
        lon, lat = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True).transform(x, y)

    dataset = gdal.Open(str(geocase.primary_path))
    assert dataset is not None

    observed = sample_raster_at_lonlat(dataset, lon, lat)
    assert observed == pytest.approx(expected)

    dataset = None


@pytest.mark.parametrize("geocase", _RASTER_CASE_PARAMS)
def test_sample_raster_at_lonlat_perfect_handles_all_raster_cases(geocase: Any) -> None:
    """Question 14 perfect: sample a valid pixel from every bundled raster fixture too."""
    from osgeo import gdal

    with rasterio.open(geocase.primary_path) as src:
        row, col, expected = _first_valid_pixel(src)
        x, y = src.xy(row, col)
        lon, lat = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True).transform(x, y)

    dataset = gdal.Open(str(geocase.primary_path))
    assert dataset is not None

    observed = sample_raster_at_lonlat_perfect(dataset, lon, lat)
    assert observed == pytest.approx(expected)

    dataset = None


# Question 15: Group nearby points into clusters
def test_cluster_points_groups_nearby_dateline_points() -> None:
    """Question 15: expose clustering issues for points split by the dateline."""
    gdf = _dateline_points_pair_case().load()
    points = list(gdf.geometry)

    clusters = cluster_points(points, max_distance_m=50_000.0)

    assert len(clusters) == 1


def test_cluster_points_groups_nearby_points_in_one_cluster() -> None:
    """Question 15: group nearby points together in a straightforward local case."""
    gdf = _nearby_points_cluster_case().load()
    points = list(gdf.geometry)

    clusters = cluster_points(points, max_distance_m=100.0)

    assert len(clusters) == 1
    assert len(clusters[0]) == 3


def test_cluster_points_keeps_dateline_chain_connected() -> None:
    """Question 15: expose failure to keep a transitive dateline chain in one cluster."""
    case = _dateline_chain_cluster_case()
    points = list(case.load().geometry)

    clusters = cluster_points(points, max_distance_m=case.params["max_distance_m"])

    assert len(clusters) == case.params["expected_cluster_count"]
    assert sorted(len(cluster) for cluster in clusters) == case.params["expected_cluster_sizes"]


def test_cluster_points_perfect_groups_nearby_dateline_points() -> None:
    """Question 15 perfect: cluster antimeridian-adjacent points geodesically."""
    gdf = _dateline_points_pair_case().load()
    points = list(gdf.geometry)

    clusters = cluster_points_perfect(points, max_distance_m=50_000.0)

    assert len(clusters) == 1
    assert len(clusters[0]) == 2


def test_cluster_points_perfect_groups_nearby_points_in_one_cluster() -> None:
    """Question 15 perfect: keep the simple local clustering case working too."""
    gdf = _nearby_points_cluster_case().load()
    points = list(gdf.geometry)

    clusters = cluster_points_perfect(points, max_distance_m=100.0)

    assert len(clusters) == 1
    assert len(clusters[0]) == 3


def test_cluster_points_perfect_keeps_dateline_chain_connected() -> None:
    """Question 15 perfect: keep the dateline chain fixture in one transitive cluster."""
    case = _dateline_chain_cluster_case()
    points = list(case.load().geometry)

    clusters = cluster_points_perfect(points, max_distance_m=case.params["max_distance_m"])

    assert len(clusters) == case.params["expected_cluster_count"]
    assert sorted(len(cluster) for cluster in clusters) == case.params["expected_cluster_sizes"]


@pytest.mark.parametrize("geocase", _VECTOR_POINT_CASE_PARAMS)
def test_cluster_points_handles_all_point_cases(geocase: Any) -> None:
    """Question 15: discover which bundled point fixtures break simple clustering."""
    points = list(geocase.load().geometry)
    max_distance_m = float(geocase.params.get("max_distance_m", 100_000.0))

    clusters = cluster_points(points, max_distance_m=max_distance_m)

    assert sum(len(cluster) for cluster in clusters) == len(points)
    if "expected_cluster_count" in geocase.params:
        assert len(clusters) == geocase.params["expected_cluster_count"]
    if "expected_cluster_sizes" in geocase.params:
        assert sorted(len(cluster) for cluster in clusters) == geocase.params["expected_cluster_sizes"]


@pytest.mark.parametrize("geocase", _VECTOR_POINT_CASE_PARAMS)
def test_cluster_points_perfect_handles_all_point_cases(geocase: Any) -> None:
    """Question 15 perfect: keep point clustering behavior correct across bundled fixtures."""
    points = list(geocase.load().geometry)
    max_distance_m = float(geocase.params.get("max_distance_m", 100_000.0))

    clusters = cluster_points_perfect(points, max_distance_m=max_distance_m)

    assert sum(len(cluster) for cluster in clusters) == len(points)
    if "expected_cluster_count" in geocase.params:
        assert len(clusters) == geocase.params["expected_cluster_count"]
    if "expected_cluster_sizes" in geocase.params:
        assert sorted(len(cluster) for cluster in clusters) == geocase.params["expected_cluster_sizes"]


# Question 16: Repair invalid polygons where possible
def test_fix_geometry_repairs_self_intersection_case() -> None:
    """Question 16: verify invalid self-intersections can be repaired."""
    geom = _self_intersecting_polygon_geometry()

    fixed = fix_geometry(geom)

    assert not fixed.is_empty
    assert fixed.is_valid


def test_fix_geometry_returns_valid_geometry_unchanged() -> None:
    """Question 16: leave already valid geometries usable and valid."""
    geom = _baseline_polygon_geometry()

    fixed = fix_geometry(geom)

    assert fixed.equals(geom)
    assert fixed.is_valid


def test_fix_geometry_returns_polygonal_output_for_spike_case() -> None:
    """Question 16: expose mixed-geometry repair output for the spike fixture."""
    geom = _spike_invalid_polygon_geometry()

    fixed = fix_geometry(geom)

    assert fixed.geom_type in {"Polygon", "MultiPolygon"}
    assert fixed.is_valid


def test_fix_geometry_perfect_repairs_self_intersection_case() -> None:
    """Question 16 perfect: return valid polygonal geometry for a fixable self-intersection."""
    geom = _self_intersecting_polygon_geometry()

    fixed = fix_geometry_perfect(geom)

    assert not fixed.is_empty
    assert fixed.is_valid
    assert fixed.geom_type in {"Polygon", "MultiPolygon"}


def test_fix_geometry_perfect_returns_valid_geometry_unchanged() -> None:
    """Question 16 perfect: leave already-valid polygon geometry untouched."""
    geom = _baseline_polygon_geometry()

    fixed = fix_geometry_perfect(geom)

    assert fixed.equals(geom)
    assert fixed.is_valid


def test_fix_geometry_perfect_returns_polygonal_output_for_spike_case() -> None:
    """Question 16 perfect: keep only polygonal output when spike repair yields mixed geometry."""
    geom = _spike_invalid_polygon_geometry()

    fixed = fix_geometry_perfect(geom)

    assert fixed.geom_type in {"Polygon", "MultiPolygon"}
    assert fixed.is_valid


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_ALL_PARAMS)
def test_fix_geometry_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 16: discover which bundled polygon fixtures break simple geometry repair."""
    geom = _load_selected_geometry(geocase)
    fixed = fix_geometry(geom)

    if geom.is_empty:
        assert fixed.is_empty
    else:
        assert not fixed.is_empty
        assert fixed.is_valid


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_ALL_PARAMS)
def test_fix_geometry_perfect_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 16 perfect: keep geometry repair polygonal across bundled fixtures."""
    geom = _load_selected_geometry(geocase)
    fixed = fix_geometry_perfect(geom)

    if geom.is_empty:
        assert fixed.is_empty
    else:
        assert not fixed.is_empty
        assert fixed.is_valid
        assert fixed.geom_type in {"Polygon", "MultiPolygon"}


# Question 17: Rasterize vector geometries onto a reference raster grid
def test_rasterize_geometries_burns_pixels_for_geocase_polygon(tmp_path: Path) -> None:
    """Question 17: expose missing reprojection during rasterization."""
    vector_geom = _baseline_polygon_geometry()
    raster_case = _utm_boundary_raster_case()
    output_path = tmp_path / "rasterized_polygon.tif"

    rasterize_geometries([vector_geom], str(raster_case.primary_path), str(output_path))

    with rasterio.open(output_path) as src:
        data = src.read(1)

    assert data.max() == 1


def test_rasterize_geometries_burns_pixels_when_geometry_matches_raster_crs(tmp_path: Path) -> None:
    """Question 17: rasterize successfully when input geometry is preprojected to raster CRS."""
    raster_case = _utm_boundary_raster_case()
    vector_geom = _rasterize_match_utm_polygon_geometry()
    output_path = tmp_path / "rasterized_polygon_projected.tif"

    rasterize_geometries([vector_geom], str(raster_case.primary_path), str(output_path))

    with rasterio.open(output_path) as src:
        data = src.read(1)

    assert data.max() == 1


def test_rasterize_geometries_perfect_reprojects_wgs84_geometry(tmp_path: Path) -> None:
    """Question 17 perfect: reproject WGS84 polygons onto the raster CRS before burning."""
    raster_case = _utm_boundary_raster_case()
    vector_geom = _rasterize_match_wgs84_polygon_geometry()
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


def test_rasterize_geometries_handles_all_rasterization_polygon_cases(tmp_path: Path) -> None:
    """Question 17: discover which rasterization-tagged polygon fixtures break the simple helper."""
    raster_case = _load_selected_case(category="raster", tags_any=["utm", "boundary"])
    matches = _select_bundled_vector_cases(
        category="vector",
        geometry_type="Polygon",
        tags_any=["rasterization"],
    )
    assert matches

    for index, meta in enumerate(matches):
        context = f"vector[{describe_case_data(meta)}], raster[{describe_case_data(raster_case)}]"
        output_path = tmp_path / f"rasterized_simple_{index}.tif"
        geom = _load_geometry(meta.id)
        try:
            rasterize_geometries([geom], str(raster_case.primary_path), str(output_path))
        except Exception as exc:
            raise AssertionError(f"Rasterization raised an exception [{context}]") from exc

        with rasterio.open(output_path) as src:
            data = src.read(1)

        assert data.max() == 1, f"Expected rasterized output to burn at least one pixel [{context}]"


def test_rasterize_geometries_perfect_handles_all_rasterization_polygon_cases(
    tmp_path: Path,
) -> None:
    """Question 17 perfect: keep rasterization-tagged polygon fixtures working without handpicked ids."""
    raster_case = _load_selected_case(category="raster", tags_any=["utm", "boundary"])
    matches = _select_bundled_vector_cases(
        category="vector",
        geometry_type="Polygon",
        tags_any=["rasterization"],
    )
    assert matches

    for index, meta in enumerate(matches):
        output_path = tmp_path / f"rasterized_perfect_{index}.tif"
        geom = _load_geometry(meta.id)
        src_epsg = CRS.from_user_input(meta.crs).to_epsg()
        assert src_epsg is not None

        rasterize_geometries_perfect(
            [geom],
            str(raster_case.primary_path),
            str(output_path),
            src_epsg=src_epsg,
        )

        with rasterio.open(output_path) as src:
            data = src.read(1)

        assert data.max() == 1


# Question 18: Determine whether a polygon crosses the antimeridian
@pytest.mark.parametrize(
    ("geometry_loader", "expected"),
    [
        (_dateline_polygon_geometry, True),
        (_baseline_polygon_geometry, False),
    ],
)
def test_crosses_antimeridian_matches_case_expectation(
    geometry_loader: Callable[[], Any],
    expected: bool,
) -> None:
    """Question 18: verify antimeridian detection on simple and dateline cases."""
    geom = geometry_loader()

    assert crosses_antimeridian(geom) is expected


def test_crosses_antimeridian_detects_classic_wrapped_polygon() -> None:
    """Question 18: detect a polygon whose longitudes jump from 179 to -179 degrees."""
    geom = _classic_antimeridian_polygon_geometry()

    assert crosses_antimeridian(geom) is True


@pytest.mark.parametrize(
    ("geometry_loader", "expected"),
    [
        (_dateline_polygon_geometry, True),
        (_baseline_polygon_geometry, False),
        (_classic_antimeridian_polygon_geometry, True),
    ],
)
def test_crosses_antimeridian_perfect_matches_case_expectation(
    geometry_loader: Callable[[], Any],
    expected: bool,
) -> None:
    """Question 18 perfect: detect both wrapped and >180° dateline encodings."""
    geom = geometry_loader()

    assert crosses_antimeridian_perfect(geom) is expected


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_CASE_PARAMS)
def test_crosses_antimeridian_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 18: discover which bundled polygon fixtures break simple dateline detection."""
    geom = _load_selected_geometry(geocase)
    expected = bool(geocase.params.get("crosses_dateline", False))
    assert crosses_antimeridian(geom) is expected, (
        failure_context(geocase, "Antimeridian heuristic returned the wrong classification")
    )


@pytest.mark.parametrize("geocase", _VECTOR_POLYGON_CASE_PARAMS)
def test_crosses_antimeridian_perfect_handles_all_polygon_cases(geocase: Any) -> None:
    """Question 18 perfect: keep bundled polygon dateline detection aligned with metadata."""
    geom = _load_selected_geometry(geocase)
    expected = bool(geocase.params.get("crosses_dateline", False))

    assert crosses_antimeridian_perfect(geom) is expected


# Question 19: Detect Null Island (geocoding failure indicator)
def test_detect_null_island_returns_true_for_origin_point() -> None:
    """Question 19: verify (0, 0) is detected as Null Island."""
    point = Point(0.0, 0.0)
    assert detect_null_island(point) is True


def test_detect_null_island_returns_false_for_non_origin_point() -> None:
    """Question 19: verify non-origin points are not flagged."""
    point = Point(1.0, 1.0)
    assert detect_null_island(point) is False


def test_detect_null_island_perfect_returns_true_for_origin_point() -> None:
    """Question 19 perfect: verify (0, 0) is detected as Null Island with tolerance."""
    point = Point(0.0, 0.0)
    assert detect_null_island_perfect(point) is True


def test_detect_null_island_perfect_returns_true_for_near_origin_point() -> None:
    """Question 19 perfect: verify near-origin points are flagged with tolerance."""
    point = Point(1e-7, 1e-7)
    assert detect_null_island_perfect(point, tolerance=1e-6) is True


def test_detect_null_island_perfect_returns_false_for_non_origin_point() -> None:
    """Question 19 perfect: verify non-origin points are not flagged."""
    point = Point(1.0, 1.0)
    assert detect_null_island_perfect(point) is False


@pytest.mark.parametrize("geocase", _VECTOR_POINT_ALL_PARAMS)
def test_detect_null_island_handles_all_point_cases(geocase: Any) -> None:
    """Question 19: test null island detection on all point cases including invalid."""
    geom = _load_selected_geometry(geocase)
    if geom.is_empty:
        pytest.skip("Empty point fixtures cannot be checked for Null Island.")
    if not isinstance(geom, Point):
        pytest.skip("Multi-point fixtures cannot be checked with single-point detect_null_island.")
    expected = bool(geocase.params.get("is_null_island", False))
    result = detect_null_island(geom)
    assert result is expected, (
        failure_context(geocase, f"Expected is_null_island={expected}, got {result}")
    )


@pytest.mark.parametrize("geocase", _VECTOR_POINT_ALL_PARAMS)
def test_detect_null_island_perfect_handles_all_point_cases(geocase: Any) -> None:
    """Question 19 perfect: test null island detection on all point cases including invalid."""
    geom = _load_selected_geometry(geocase)
    if geom.is_empty:
        pytest.skip("Empty point fixtures cannot be checked for Null Island.")
    if not isinstance(geom, Point):
        pytest.skip("Multi-point fixtures cannot be checked with single-point detect_null_island_perfect.")
    expected = bool(geocase.params.get("is_null_island", False))
    result = detect_null_island_perfect(geom)
    assert result is expected, (
        failure_context(geocase, f"Expected is_null_island={expected}, got {result}")
    )


# Question 20: Validate coordinate bounds
def test_validate_coordinate_bounds_returns_true_for_valid_coordinates() -> None:
    """Question 20: verify valid coordinates pass validation."""
    geom = Point(-122.4194, 37.7749)  # San Francisco
    is_valid, errors = validate_coordinate_bounds(geom)
    assert is_valid is True
    assert len(errors) == 0


def test_validate_coordinate_bounds_returns_false_for_out_of_bounds_latitude() -> None:
    """Question 20: verify latitude > 90 fails validation."""
    geom = Point(-0.1, 100.0)  # Invalid latitude
    is_valid, errors = validate_coordinate_bounds(geom)
    assert is_valid is False
    assert any("Latitude out of bounds" in e for e in errors)


def test_validate_coordinate_bounds_perfect_returns_true_for_valid_coordinates() -> None:
    """Question 20 perfect: verify valid coordinates pass validation."""
    geom = Point(-122.4194, 37.7749)  # San Francisco
    is_valid, errors = validate_coordinate_bounds_perfect(geom)
    assert is_valid is True
    assert len(errors) == 0


def test_validate_coordinate_bounds_perfect_detects_lat_lon_swap() -> None:
    """Question 20 perfect: verify lat/lon swap heuristic triggers."""
    geom = Point(-0.1, 100.0)  # Latitude 100 - invalid but valid as longitude
    is_valid, errors = validate_coordinate_bounds_perfect(geom)
    assert is_valid is False
    assert any("lat/lon swap" in e.lower() for e in errors)


@pytest.mark.parametrize("geocase", _VECTOR_POINT_ALL_PARAMS)
def test_validate_coordinate_bounds_handles_all_point_cases(geocase: Any) -> None:
    """Question 20: test coordinate validation on all point cases including invalid."""
    geom = _load_selected_geometry(geocase)
    if geom.is_empty:
        pytest.skip("Empty point fixtures cannot be validated for bounds.")

    is_valid, errors = validate_coordinate_bounds(geom)

    # Check if case is marked as out_of_bounds
    coord_error_type = geocase.params.get("coordinate_error_type", None)
    if coord_error_type == "out_of_bounds":
        assert is_valid is False, (
            failure_context(geocase, "Expected out_of_bounds case to fail validation")
        )
    # Valid cases should pass
    elif geocase.assertions.expect_valid_geometry is not False and "invalid" not in geocase.tags:
        # Don't assert anything for cases not explicitly marked - just ensure it doesn't crash
        pass


@pytest.mark.parametrize("geocase", _VECTOR_POINT_ALL_PARAMS)
def test_validate_coordinate_bounds_perfect_handles_all_point_cases(geocase: Any) -> None:
    """Question 20 perfect: test coordinate validation on all point cases including invalid."""
    geom = _load_selected_geometry(geocase)
    if geom.is_empty:
        pytest.skip("Empty point fixtures cannot be validated for bounds.")

    is_valid, errors = validate_coordinate_bounds_perfect(geom)

    # Check if case is marked as out_of_bounds
    coord_error_type = geocase.params.get("coordinate_error_type", None)
    if coord_error_type == "out_of_bounds":
        assert is_valid is False, (
            failure_context(geocase, "Expected out_of_bounds case to fail validation")
        )
        # Perfect version should also detect lat/lon swap
        assert any("lat/lon swap" in e.lower() for e in errors), (
            failure_context(geocase, "Expected lat/lon swap detection in errors")
        )


# =============================================================================
# Invalid Geometry Rejection Tests
# =============================================================================
# These tests verify that _perfect functions properly reject invalid geometry
# with explicit ValueError messages, rather than silently producing wrong results.


@pytest.mark.parametrize("geocase", _INVALID_POLYGON_PARAMS)
def test_area_m2_perfect_rejects_all_invalid_polygons(geocase: Any) -> None:
    """Verify area_m2_perfect explicitly rejects ALL invalid polygon cases.

    This ensures functions don't silently accept invalid geometry and produce
    wrong results. Invalid geometry should be explicitly rejected with a
    meaningful error message.
    """
    geom = _load_selected_geometry(geocase)
    context = describe_case_data(geocase)

    # Some parsers auto-repair geometry on load (e.g., unclosed rings)
    if geom.is_valid:
        pytest.skip(f"Geometry was auto-repaired on load [{context}]")

    with pytest.raises(ValueError, match="valid"):
        area_m2_perfect(geom)


@pytest.mark.parametrize("geocase", _INVALID_POLYGON_PARAMS)
def test_buffer_in_meters_perfect_rejects_all_invalid_polygons(geocase: Any) -> None:
    """Verify buffer_in_meters_perfect explicitly rejects ALL invalid polygon cases."""
    geom = _load_selected_geometry(geocase)
    context = describe_case_data(geocase)

    if geom.is_valid:
        pytest.skip(f"Geometry was auto-repaired on load [{context}]")

    with pytest.raises(ValueError, match="valid"):
        buffer_in_meters_perfect(geom, 100)


@pytest.mark.parametrize("geocase", _INVALID_POLYGON_PARAMS)
def test_get_bbox_perfect_rejects_all_invalid_polygons(geocase: Any) -> None:
    """Verify get_bbox_perfect explicitly rejects ALL invalid polygon cases."""
    geom = _load_selected_geometry(geocase)
    context = describe_case_data(geocase)

    if geom.is_valid:
        pytest.skip(f"Geometry was auto-repaired on load [{context}]")

    with pytest.raises(ValueError, match="valid"):
        get_bbox_perfect(geom)


@pytest.mark.parametrize("geocase", _INVALID_POLYGON_PARAMS)
def test_reproject_geometry_perfect_rejects_all_invalid_polygons(geocase: Any) -> None:
    """Verify reproject_geometry_perfect explicitly rejects ALL invalid polygon cases."""
    geom = _load_selected_geometry(geocase)
    context = describe_case_data(geocase)

    if geom.is_valid:
        pytest.skip(f"Geometry was auto-repaired on load [{context}]")

    with pytest.raises(ValueError, match="valid"):
        reproject_geometry_perfect(geom, "EPSG:4326", "EPSG:32633")


@pytest.mark.parametrize("geocase", _INVALID_POINT_PARAMS)
def test_buffer_in_meters_perfect_rejects_all_invalid_points(geocase: Any) -> None:
    """Verify buffer_in_meters_perfect explicitly rejects ALL invalid point cases."""
    geom = _load_selected_geometry(geocase)
    context = describe_case_data(geocase)

    if geom.is_valid:
        pytest.skip(f"Geometry was auto-repaired on load [{context}]")

    with pytest.raises(ValueError, match="valid"):
        buffer_in_meters_perfect(geom, 100)


@pytest.mark.parametrize("geocase", _INVALID_POINT_PARAMS)
def test_get_bbox_perfect_rejects_all_invalid_points(geocase: Any) -> None:
    """Verify get_bbox_perfect explicitly rejects ALL invalid point cases."""
    geom = _load_selected_geometry(geocase)
    context = describe_case_data(geocase)

    if geom.is_valid:
        pytest.skip(f"Geometry was auto-repaired on load [{context}]")

    with pytest.raises(ValueError, match="valid"):
        get_bbox_perfect(geom)


@pytest.mark.parametrize("geocase", _INVALID_POINT_PARAMS)
def test_reproject_geometry_perfect_rejects_all_invalid_points(geocase: Any) -> None:
    """Verify reproject_geometry_perfect explicitly rejects ALL invalid point cases."""
    geom = _load_selected_geometry(geocase)
    context = describe_case_data(geocase)

    if geom.is_valid:
        pytest.skip(f"Geometry was auto-repaired on load [{context}]")

    with pytest.raises(ValueError, match="valid"):
        reproject_geometry_perfect(geom, "EPSG:4326", "EPSG:32633")


# =============================================================================
# Repair Functions Should Accept Invalid Geometry
# =============================================================================
# Repair/validation functions are the exception - they SHOULD accept invalid
# geometry and either fix it or report the issues.


@pytest.mark.parametrize("geocase", _INVALID_POLYGON_PARAMS)
def test_fix_geometry_perfect_accepts_all_invalid_polygons(geocase: Any) -> None:
    """Verify fix_geometry_perfect repairs (not rejects) ALL invalid polygon cases.

    Unlike other functions, fix_geometry should accept invalid input and
    return a valid geometry.
    """
    geom = _load_selected_geometry(geocase)
    context = describe_case_data(geocase)

    if geom.is_valid:
        pytest.skip(f"Geometry was auto-repaired on load [{context}]")

    # Should NOT raise - should repair
    result = fix_geometry_perfect(geom)
    assert result.is_valid, f"Expected fix_geometry_perfect to return valid geometry [{context}]"


@pytest.mark.parametrize("geocase", _INVALID_POLYGON_PARAMS)
def test_validate_polygon_geometry_perfect_handles_all_invalid_polygons(geocase: Any) -> None:
    """Verify validate_polygon_geometry_perfect handles ALL invalid polygon cases.

    Validation functions should accept invalid input and either:
    1. Repair it and return success (repairable invalid geometry), OR
    2. Return failure with issues (unrepairable invalid geometry)

    This test just ensures the function doesn't crash on invalid input.
    """
    geom = _load_selected_geometry(geocase)
    context = describe_case_data(geocase)

    if geom.is_valid:
        pytest.skip(f"Geometry was auto-repaired on load [{context}]")

    # Should NOT raise - should return validation results
    is_ok, issues = validate_polygon_geometry_perfect(geom, min_area_m2=0.0)

    # Function either repairs successfully or reports issues
    if not is_ok:
        assert len(issues) > 0, f"Expected issues list to be non-empty when validation fails [{context}]"
    # If is_ok is True, the function successfully repaired the geometry - that's valid behavior
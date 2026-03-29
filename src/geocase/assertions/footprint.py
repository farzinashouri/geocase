"""Footprint assertions — validate raster footprint geometry quality."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shapely.ops import unary_union

if TYPE_CHECKING:
    import geopandas as gpd


def _merged_geometry(gdf: gpd.GeoDataFrame):
    if len(gdf) == 0:
        raise AssertionError("Footprint GeoDataFrame is empty")

    geom = unary_union(list(gdf.geometry))
    if geom.is_empty:
        raise AssertionError("Footprint geometry is empty")

    return geom


def _hole_count(geom) -> int:
    if geom.geom_type == "Polygon":
        return len(geom.interiors)
    if geom.geom_type == "MultiPolygon":
        return sum(len(poly.interiors) for poly in geom.geoms)
    return 0


def assert_footprint_no_holes(
    footprint_gdf: gpd.GeoDataFrame,
    *,
    msg: str | None = None,
) -> None:
    """Assert that footprint polygons contain no interior rings."""
    total_holes = sum(_hole_count(geom) for geom in footprint_gdf.geometry)
    if total_holes > 0:
        raise AssertionError(msg or f"Footprint has {total_holes} hole(s)")


def assert_footprint_rectangularity(
    footprint_gdf: gpd.GeoDataFrame,
    min_ratio: float = 0.9,
    *,
    msg: str | None = None,
) -> None:
    """Assert footprint is reasonably close to a rectangle.

    The ratio is defined as:
        footprint_area / minimum_rotated_rectangle_area
    and lies in (0, 1]. Closer to 1 means more rectangle-like.
    """
    merged = _merged_geometry(footprint_gdf)
    area = float(merged.area)
    if area <= 0:
        raise AssertionError(msg or "Footprint has non-positive area")

    mrr_area = float(merged.minimum_rotated_rectangle.area)
    if mrr_area <= 0:
        raise AssertionError(msg or "Minimum rotated rectangle has non-positive area")

    ratio = area / mrr_area
    if ratio < min_ratio:
        raise AssertionError(
            msg
            or (
                f"Footprint rectangularity ratio {ratio:.4f} is below minimum "
                f"{min_ratio:.4f}"
            )
        )


def assert_footprint_similar_to_expected(
    footprint_gdf: gpd.GeoDataFrame,
    expected_gdf: gpd.GeoDataFrame,
    max_diff_ratio: float = 1e-6,
    *,
    msg: str | None = None,
) -> None:
    """Assert footprint geometry is close to expected geometry.

    Uses normalized symmetric-difference area:
        sym_diff_area / expected_area
    """
    actual = _merged_geometry(footprint_gdf)
    expected = _merged_geometry(expected_gdf)

    expected_area = float(expected.area)
    if expected_area <= 0:
        raise AssertionError("Expected footprint has non-positive area")

    diff_ratio = float(actual.symmetric_difference(expected).area) / expected_area
    if diff_ratio > max_diff_ratio:
        raise AssertionError(
            msg
            or (
                f"Footprint differs from expected by ratio {diff_ratio:.8f}, "
                f"max allowed {max_diff_ratio:.8f}"
            )
        )

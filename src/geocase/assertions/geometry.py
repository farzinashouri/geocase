"""Geometry assertions — validate vector geometry properties.

All functions raise :class:`AssertionError` on failure, so they
integrate naturally with pytest (no special imports needed).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import geopandas as gpd


def assert_valid_geometry(
    gdf: gpd.GeoDataFrame,
    *,
    msg: str | None = None,
) -> None:
    """Assert every geometry in the GeoDataFrame is valid (OGC).

    Raises:
        AssertionError: If any geometry is invalid.
    """
    invalid = gdf[~gdf.geometry.is_valid]
    if len(invalid) > 0:
        detail = msg or (
            f"{len(invalid)} invalid geometr{'y' if len(invalid) == 1 else 'ies'} "
            f"found (rows: {list(invalid.index[:10])})"
        )
        raise AssertionError(detail)


def assert_invalid_geometry(
    gdf: gpd.GeoDataFrame,
    *,
    msg: str | None = None,
) -> None:
    """Assert that at least one geometry is *invalid* (OGC).

    Useful for cases that are *expected* to contain invalid geometry.

    Raises:
        AssertionError: If all geometries are valid.
    """
    invalid = gdf[~gdf.geometry.is_valid]
    if len(invalid) == 0:
        raise AssertionError(
            msg or "Expected at least one invalid geometry, but all are valid"
        )


def assert_geometry_type(
    gdf: gpd.GeoDataFrame,
    expected_types: str | list[str],
    *,
    msg: str | None = None,
) -> None:
    """Assert all geometries match one of the expected type names.

    Args:
        gdf: GeoDataFrame to check.
        expected_types: A single type name (e.g. ``"Polygon"``) or a
            list of acceptable types.
    """
    if isinstance(expected_types, str):
        expected_types = [expected_types]

    expected_set = set(expected_types)
    actual_types = set(gdf.geometry.geom_type)
    unexpected = actual_types - expected_set

    if unexpected:
        raise AssertionError(
            msg or (
                f"Unexpected geometry type(s): {unexpected}. "
                f"Expected: {expected_set}"
            )
        )


def assert_has_holes(
    gdf: gpd.GeoDataFrame,
    *,
    msg: str | None = None,
) -> None:
    """Assert that at least one polygon has an interior ring (hole).

    Raises:
        AssertionError: If no polygon has a hole.
    """
    for geom in gdf.geometry:
        if hasattr(geom, "interiors") and len(list(geom.interiors)) > 0:
            return
    raise AssertionError(
        msg or "Expected at least one polygon with a hole, found none"
    )


def assert_no_holes(
    gdf: gpd.GeoDataFrame,
    *,
    msg: str | None = None,
) -> None:
    """Assert that no polygon has interior rings.

    Raises:
        AssertionError: If any polygon has a hole.
    """
    for idx, geom in enumerate(gdf.geometry):
        if hasattr(geom, "interiors") and len(list(geom.interiors)) > 0:
            raise AssertionError(
                msg or f"Polygon at index {idx} has interior rings"
            )


def assert_feature_count(
    gdf: gpd.GeoDataFrame,
    expected: int,
    *,
    msg: str | None = None,
) -> None:
    """Assert the GeoDataFrame has exactly *expected* features.

    Raises:
        AssertionError: If the count does not match.
    """
    actual = len(gdf)
    if actual != expected:
        raise AssertionError(
            msg or f"Expected {expected} features, got {actual}"
        )

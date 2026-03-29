"""Topology assertions — validate spatial relationships and integrity.

These checks go beyond simple validity (OGC ``is_valid``) to detect
topological issues like self-intersections, duplicate vertices, and
overlapping features.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import geopandas as gpd


def assert_no_self_intersections(
    gdf: gpd.GeoDataFrame,
    *,
    msg: str | None = None,
) -> None:
    """Assert no geometry has a self-intersection.

    Uses ``shapely.is_valid`` under the hood — a self-intersecting
    polygon is by definition invalid.  This function provides a
    clearer error message focused on the self-intersection aspect.

    Raises:
        AssertionError: If any geometry is self-intersecting.
    """
    from shapely.validation import explain_validity

    bad_rows: list[tuple[int, str]] = []
    for idx, geom in enumerate(gdf.geometry):
        if geom is None:
            continue
        if not geom.is_valid:
            reason = explain_validity(geom)
            if "self-intersection" in reason.lower():
                bad_rows.append((idx, reason))

    if bad_rows:
        details = "; ".join(f"row {r}: {m}" for r, m in bad_rows[:5])
        raise AssertionError(
            msg or (
                f"{len(bad_rows)} self-intersecting geometr"
                f"{'y' if len(bad_rows) == 1 else 'ies'} found. "
                f"{details}"
            )
        )


def assert_no_duplicates(
    gdf: gpd.GeoDataFrame,
    *,
    msg: str | None = None,
) -> None:
    """Assert no two features have identical geometry.

    Raises:
        AssertionError: If any duplicate geometries exist.
    """
    n = len(gdf)
    for i in range(n):
        for j in range(i + 1, n):
            if gdf.geometry.iloc[i].equals(gdf.geometry.iloc[j]):
                raise AssertionError(
                    msg or (
                        f"Duplicate geometry found at rows {i} and {j}"
                    )
                )


def assert_no_null_geometries(
    gdf: gpd.GeoDataFrame,
    *,
    msg: str | None = None,
) -> None:
    """Assert no features have a null/None geometry.

    Raises:
        AssertionError: If any geometry is None.
    """
    null_mask = gdf.geometry.isna() | gdf.geometry.is_empty
    null_count = int(null_mask.sum())
    if null_count > 0:
        raise AssertionError(
            msg or (
                f"{null_count} feature(s) have null or empty geometry "
                f"(rows: {list(gdf.index[null_mask][:10])})"
            )
        )

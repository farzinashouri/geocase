"""CRS assertions — validate coordinate reference system properties.

Works with both geopandas GeoDataFrames (which have a ``.crs``
attribute) and rasterio dataset readers.
"""

from __future__ import annotations

from typing import Any


def assert_has_crs(
    obj: Any,
    *,
    msg: str | None = None,
) -> None:
    """Assert the object has a non-null CRS.

    *obj* can be a GeoDataFrame, a rasterio DatasetReader, or anything
    with a ``.crs`` attribute.

    Raises:
        AssertionError: If ``.crs`` is None or missing.
    """
    crs = getattr(obj, "crs", None)
    if crs is None:
        raise AssertionError(msg or "Object has no CRS (crs is None)")


def assert_epsg(
    obj: Any,
    expected_epsg: int,
    *,
    msg: str | None = None,
) -> None:
    """Assert the object's CRS matches the given EPSG code.

    Args:
        obj: Object with a ``.crs`` attribute.
        expected_epsg: The EPSG code to expect (e.g. 4326).

    Raises:
        AssertionError: If the CRS is missing or the EPSG differs.
    """
    crs = getattr(obj, "crs", None)
    if crs is None:
        raise AssertionError(
            msg or f"Expected EPSG:{expected_epsg}, but object has no CRS"
        )

    actual = crs.to_epsg()
    if actual != expected_epsg:
        raise AssertionError(msg or f"Expected EPSG:{expected_epsg}, got EPSG:{actual}")


def assert_crs_units(
    obj: Any,
    expected_unit: str,
    *,
    msg: str | None = None,
) -> None:
    """Assert the CRS linear/angular unit contains *expected_unit*.

    Performs a case-insensitive substring match, so
    ``assert_crs_units(gdf, "metre")`` matches ``"metre"`` or
    ``"US survey metre"``.

    Args:
        obj: Object with a ``.crs`` attribute.
        expected_unit: Substring to match (e.g. ``"metre"``,
            ``"degree"``).

    Raises:
        AssertionError: If the CRS is missing or the unit doesn't match.
    """
    crs = getattr(obj, "crs", None)
    if crs is None:
        raise AssertionError(
            msg or f"Expected unit containing '{expected_unit}', but no CRS"
        )

    # Convert rasterio CRS → pyproj CRS if needed so we can
    # access axis_info uniformly.
    try:
        axis_info = crs.axis_info
    except AttributeError:
        # rasterio.crs.CRS — convert to pyproj first
        import pyproj

        crs = pyproj.CRS(crs)
        axis_info = crs.axis_info

    unit_names = [ax.unit_name.lower() for ax in axis_info if ax.unit_name]

    expected_lower = expected_unit.lower()
    if not any(expected_lower in u for u in unit_names):
        raise AssertionError(
            msg or (f"Expected CRS unit containing '{expected_unit}', got {unit_names}")
        )

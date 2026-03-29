"""Metadata assertions — validate a case against its own assertion hints.

These are higher-level checks that read the ``assertions:`` block from
a case's metadata and run the appropriate low-level assertion functions
automatically.
"""

from __future__ import annotations

from typing import Any

from geocase.catalog.models import AssertionHints
from geocase.cases.base import BaseCase


def assert_case_loadable(case: BaseCase) -> None:
    """Assert the case's primary data file exists on disk.

    Raises:
        AssertionError: If the file is missing.
    """
    if not case.primary_exists():
        raise AssertionError(
            f"Case '{case.id}': primary file not found at "
            f"{case.primary_path}"
        )


def assert_matches_vector_hints(
    case: BaseCase,
    gdf: Any,
) -> None:
    """Validate a loaded GeoDataFrame against the case's assertion hints.

    Runs whichever checks are specified (non-None) in the case's
    ``assertions`` block:

    * ``expect_valid_geometry`` → geometry validity
    * ``expect_crs`` → CRS presence
    * ``expected_epsg`` → EPSG code
    * ``expected_geometry_types`` → geometry type check

    Args:
        case: The case instance (provides metadata + hints).
        gdf: The loaded GeoDataFrame.
    """
    from geocase.assertions.crs import assert_epsg, assert_has_crs
    from geocase.assertions.geometry import (
        assert_geometry_type,
        assert_invalid_geometry,
        assert_valid_geometry,
    )

    hints: AssertionHints = case.assertions

    if hints.expect_valid_geometry is True:
        assert_valid_geometry(gdf)
    elif hints.expect_valid_geometry is False:
        assert_invalid_geometry(gdf)

    if hints.expect_crs is True:
        assert_has_crs(gdf)

    if hints.expected_epsg is not None:
        assert_epsg(gdf, hints.expected_epsg)

    if hints.expected_geometry_types:
        assert_geometry_type(gdf, hints.expected_geometry_types)


def assert_matches_raster_hints(
    case: BaseCase,
    src: Any,
) -> None:
    """Validate an open rasterio dataset against the case's assertion hints.

    Runs whichever checks are specified (non-None) in the case's
    ``assertions`` block:

    * ``expect_crs`` → CRS presence
    * ``expected_epsg`` → EPSG code
    * ``expect_nodata`` → NoData value presence

    Args:
        case: The case instance.
        src: An open rasterio DatasetReader.
    """
    from geocase.assertions.crs import assert_epsg, assert_has_crs
    from geocase.assertions.raster import assert_nodata_value

    hints: AssertionHints = case.assertions

    if hints.expect_crs is True:
        assert_has_crs(src)

    if hints.expected_epsg is not None:
        assert_epsg(src, hints.expected_epsg)

    if hints.expect_nodata is True:
        assert_nodata_value(src)

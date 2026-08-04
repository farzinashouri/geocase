"""Metadata assertions — validate a case against its own assertion hints.

These are higher-level checks that read the ``assertions:`` block from
a case's metadata and run the appropriate low-level assertion functions
automatically.
"""

from __future__ import annotations

from typing import Any

from geocase.cases.base import BaseCase
from geocase.catalog.models import AssertionHints


def assert_case_loadable(case: BaseCase) -> None:
    """Assert the case's primary data file exists on disk.

    Raises:
        AssertionError: If the file is missing.
    """
    if not case.primary_exists():
        raise AssertionError(
            f"Case '{case.id}': primary file not found at {case.primary_path}"
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
    * ``expected_nodata_value`` → explicit NoData sentinel
    * ``nodata_convention`` → ``"nan"`` triggers a NaN-nodata check
    * ``expected_band_count`` → band count
    * ``expected_dtype`` → band dtype
    * ``expected_shape`` → (height, width)
    * ``expected_compression`` → compression codec
    * ``expected_overviews`` → overview presence
    * ``expected_band_names`` → per-band descriptions
    * ``expected_colormap_present`` → colormap presence
    * ``is_cog`` → COG-style structural check

    Args:
        case: The case instance.
        src: An open rasterio DatasetReader.
    """
    from geocase.assertions.crs import assert_epsg, assert_has_crs
    from geocase.assertions.raster import (
        assert_band_count,
        assert_band_names,
        assert_colormap_present,
        assert_compression,
        assert_dtype,
        assert_has_overviews,
        assert_is_cog,
        assert_nan_nodata,
        assert_nodata_value,
        assert_shape,
    )

    hints: AssertionHints = case.assertions

    if hints.expect_crs is True:
        assert_has_crs(src)

    if hints.expected_epsg is not None:
        assert_epsg(src, hints.expected_epsg)

    if hints.expect_nodata is True:
        assert_nodata_value(src)

    if hints.expected_nodata_value is not None:
        assert_nodata_value(src, hints.expected_nodata_value)

    if hints.nodata_convention == "nan":
        assert_nan_nodata(src)

    if hints.expected_band_count is not None:
        assert_band_count(src, hints.expected_band_count)

    if hints.expected_dtype is not None:
        assert_dtype(src, hints.expected_dtype)

    if hints.expected_shape is not None:
        height, width = hints.expected_shape
        assert_shape(src, height, width)

    if hints.expected_compression is not None:
        assert_compression(src, hints.expected_compression)

    if hints.expected_overviews is True:
        assert_has_overviews(src)

    if hints.expected_band_names:
        assert_band_names(src, hints.expected_band_names)

    if hints.expected_colormap_present is True:
        assert_colormap_present(src)

    if hints.is_cog is True:
        assert_is_cog(src)

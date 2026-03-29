"""Raster assertions — validate raster dataset properties.

Works with rasterio ``DatasetReader`` objects (i.e. the context-managed
handle from ``rasterio.open()``).
"""

from __future__ import annotations

from typing import Any

import numpy as np


def assert_band_count(
    src: Any,
    expected: int,
    *,
    msg: str | None = None,
) -> None:
    """Assert the raster has exactly *expected* bands.

    Raises:
        AssertionError: If ``src.count != expected``.
    """
    actual = src.count
    if actual != expected:
        raise AssertionError(
            msg or f"Expected {expected} band(s), got {actual}"
        )


def assert_nodata_value(
    src: Any,
    expected_nodata: float | int | None = None,
    *,
    msg: str | None = None,
) -> None:
    """Assert the raster has a NoData value set.

    If *expected_nodata* is given, also checks that the value matches.

    Raises:
        AssertionError: If nodata is None or doesn't match.
    """
    actual = src.nodata
    if actual is None:
        raise AssertionError(
            msg or "Raster has no NoData value set (nodata is None)"
        )
    if expected_nodata is not None and actual != expected_nodata:
        raise AssertionError(
            msg or f"Expected NoData={expected_nodata}, got {actual}"
        )


def assert_dtype(
    src: Any,
    expected_dtype: str,
    *,
    band: int = 1,
    msg: str | None = None,
) -> None:
    """Assert the raster dtype matches *expected_dtype*.

    Args:
        src: A rasterio DatasetReader.
        expected_dtype: e.g. ``"float32"``, ``"uint8"``.
        band: Band index (1-based) to check.

    Raises:
        AssertionError: If the dtype doesn't match.
    """
    actual = src.dtypes[band - 1]
    if actual != expected_dtype:
        raise AssertionError(
            msg or f"Expected dtype '{expected_dtype}', got '{actual}'"
        )


def assert_shape(
    src: Any,
    expected_height: int,
    expected_width: int,
    *,
    msg: str | None = None,
) -> None:
    """Assert the raster dimensions match.

    Raises:
        AssertionError: If height or width don't match.
    """
    if src.height != expected_height or src.width != expected_width:
        raise AssertionError(
            msg or (
                f"Expected shape ({expected_height}, {expected_width}), "
                f"got ({src.height}, {src.width})"
            )
        )


def assert_nodata_masked(
    data: np.ndarray,
    nodata: float | int,
    *,
    msg: str | None = None,
) -> None:
    """Assert that *data* contains at least one pixel equal to *nodata*.

    This confirms the NoData sentinel is actually present in the data,
    which is a prerequisite for masking logic.

    Args:
        data: A 2-D numpy array (single band).
        nodata: The NoData sentinel value.

    Raises:
        AssertionError: If no pixel matches the nodata value.
    """
    if not np.any(data == nodata):
        raise AssertionError(
            msg or f"No pixels equal to NoData value {nodata} found in data"
        )


def assert_no_nodata_pixels(
    data: np.ndarray,
    nodata: float | int,
    *,
    msg: str | None = None,
) -> None:
    """Assert that *data* has no pixels equal to *nodata*.

    Useful after masking or filling operations.

    Raises:
        AssertionError: If any pixel matches the nodata value.
    """
    count = int(np.sum(data == nodata))
    if count > 0:
        raise AssertionError(
            msg or f"Found {count} pixel(s) equal to NoData value {nodata}"
        )

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
        raise AssertionError(msg or f"Expected {expected} band(s), got {actual}")


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
        raise AssertionError(msg or "Raster has no NoData value set (nodata is None)")
    if expected_nodata is not None and actual != expected_nodata:
        raise AssertionError(msg or f"Expected NoData={expected_nodata}, got {actual}")


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
            msg
            or (
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


def assert_compression(
    src: Any,
    expected: str,
    *,
    msg: str | None = None,
) -> None:
    """Assert the raster uses *expected* compression.

    Comparison is case-insensitive (``"DEFLATE"`` == ``"deflate"``).

    Raises:
        AssertionError: If compression is absent or does not match.
    """
    compression = src.profile.get("compress")
    actual = str(compression).lower() if compression is not None else None
    if actual != expected.lower():
        raise AssertionError(
            msg or f"Expected compression '{expected}', got '{compression}'"
        )


def assert_has_overviews(
    src: Any,
    *,
    band: int = 1,
    msg: str | None = None,
) -> None:
    """Assert the raster has overviews (pyramids) for *band*.

    Raises:
        AssertionError: If the band has no overviews.
    """
    overviews = src.overviews(band)
    if not overviews:
        raise AssertionError(msg or f"Raster band {band} has no overviews")


def assert_nan_nodata(
    src: Any,
    *,
    msg: str | None = None,
) -> None:
    """Assert the raster encodes NoData using the NaN convention.

    Raises:
        AssertionError: If the nodata value is not NaN.
    """
    actual = src.nodata
    if actual is None or not np.isnan(actual):
        raise AssertionError(msg or f"Expected NaN NoData value, got {actual}")


def assert_is_cog(
    src: Any,
    *,
    msg: str | None = None,
) -> None:
    """Assert the raster is structured as a Cloud-Optimized GeoTIFF.

    Applies a lightweight structural check: the dataset must be tiled and
    expose overviews. This is intentionally shallow (see open question 3 in
    the raster action plan) and not a full COG validator.

    Raises:
        AssertionError: If the raster is not tiled or lacks overviews.
    """
    is_tiled = bool(src.profile.get("tiled", False))
    if not is_tiled:
        raise AssertionError(
            msg or "Raster is not internally tiled (not COG-structured)"
        )
    if not src.overviews(1):
        raise AssertionError(msg or "Raster has no overviews (not COG-structured)")


def assert_band_names(
    src: Any,
    expected: list[str],
    *,
    msg: str | None = None,
) -> None:
    """Assert the raster band descriptions match *expected* names in order.

    Raises:
        AssertionError: If band descriptions do not match.
    """
    actual = list(src.descriptions)
    if actual != list(expected):
        raise AssertionError(msg or f"Expected band names {expected}, got {actual}")


def assert_colormap_present(
    src: Any,
    *,
    band: int = 1,
    msg: str | None = None,
) -> None:
    """Assert the raster band has a colormap.

    Raises:
        AssertionError: If the band has no colormap.
    """
    try:
        src.colormap(band)
    except (ValueError, KeyError):
        raise AssertionError(msg or f"Raster band {band} has no colormap") from None


def assert_scale_factor(
    src: Any,
    expected: float,
    *,
    band: int = 1,
    msg: str | None = None,
) -> None:
    """Assert the band declares a scale factor of *expected*.

    Values stored packed (an ``int16`` NDVI scaled by 1e-4, say) are physically
    meaningless until the scale is applied. A consumer that ignores it reads
    plausible integers and never notices — which is why the declaration is
    worth gating.

    Raises:
        AssertionError: If the band's scale differs from *expected*.
    """
    actual = src.scales[band - 1]
    if float(actual) != float(expected):
        raise AssertionError(
            msg or f"Expected scale factor {expected} on band {band}, got {actual}"
        )


def transform_signs(src: Any) -> list[str]:
    """Describe a raster's affine transform as a list of sign properties.

    Returns some of ``"positive_e"``, ``"negative_e"`` and ``"rotated"``. A
    rotated affine carries non-zero ``b``/``d`` in addition to a ``e`` sign,
    which is why this is a list and not a single value.
    """
    transform = src.transform
    signs = ["positive_e" if transform.e > 0 else "negative_e"]
    if transform.b != 0 or transform.d != 0:
        signs.append("rotated")
    return signs


def assert_transform_signs(
    src: Any,
    expected: list[str],
    *,
    msg: str | None = None,
) -> None:
    """Assert the raster's affine transform has the declared sign properties.

    ``rasterio.transform.from_origin`` always produces a negative ``e``
    (north-up, row 0 northernmost), so a consumer that hardcodes that
    assumption passes every fixture built with it. A bottom-up raster — one
    with positive ``e``, origin at the bottom-left — then loads mirrored
    vertically, producing a plausible image of the wrong place.

    Raises:
        AssertionError: If the observed sign properties differ.
    """
    actual = transform_signs(src)
    if sorted(actual) != sorted(expected):
        raise AssertionError(
            msg
            or f"Expected transform signs {sorted(expected)}, got {sorted(actual)} "
            f"(transform={src.transform!r})"
        )


def assert_pixel_anchor(
    src: Any,
    expected: str,
    *,
    msg: str | None = None,
) -> None:
    """Assert the raster's ``AREA_OR_POINT`` convention is *expected*.

    ``"area"`` means the transform's coordinates name pixel *corners*;
    ``"point"`` means they name pixel *centres*. The difference is half a
    pixel, and it is invisible to a shape, CRS or checksum check.

    GDAL omits the tag entirely for the area convention, so the default here is
    load-bearing: reading the tag without one yields ``None`` and a guess.

    Raises:
        AssertionError: If the file's convention differs from *expected*.
    """
    actual = str(src.tags().get("AREA_OR_POINT", "Area")).lower()
    if actual != str(expected).lower():
        raise AssertionError(
            msg or f"Expected pixel anchor {expected!r}, got {actual!r}"
        )

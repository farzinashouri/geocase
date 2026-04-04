"""Real geospatial utility functions for testable workflows."""

from __future__ import annotations

from typing import Any

import numpy as np


def compute_projected_shape_metrics(
    geodataframe: Any,
    *,
    target_epsg: int = 3857,
) -> dict[str, float]:
    """Project geometries and return area/perimeter summary metrics.

    Args:
        geodataframe: A GeoDataFrame-like object with ``to_crs`` and ``geometry``.
        target_epsg: EPSG code for projected metric calculations.

    Returns:
        Dict with ``feature_count``, ``area_sum``, and ``perimeter_sum``.

    Raises:
        ValueError: If CRS is missing or dataframe is empty.
    """
    if getattr(geodataframe, "crs", None) is None:
        raise ValueError("Input GeoDataFrame must have a CRS")

    if len(geodataframe) == 0:
        raise ValueError("Input GeoDataFrame is empty")

    projected = geodataframe.to_crs(epsg=target_epsg)

    return {
        "feature_count": float(len(projected)),
        "area_sum": float(projected.area.sum()),
        "perimeter_sum": float(projected.length.sum()),
    }


def compute_masked_raster_stats(
    data: np.ndarray,
    nodata: float | int | None,
) -> dict[str, float]:
    """Compute summary statistics on valid pixels only.

    Args:
        data: Raster band array.
        nodata: Nodata value (or ``None`` if no nodata is defined).

    Returns:
        Dict with valid pixel count, nodata ratio, min/max/mean/std.

    Raises:
        ValueError: If no valid pixels remain after masking.
    """
    finite_mask = np.isfinite(data)
    if nodata is None:
        valid_mask = finite_mask
    else:
        valid_mask = finite_mask & (data != nodata)

    valid_values = data[valid_mask]
    if valid_values.size == 0:
        raise ValueError("Raster has no valid pixels after nodata masking")

    nodata_ratio = 1.0 - (float(valid_values.size) / float(data.size))

    return {
        "valid_pixel_count": float(valid_values.size),
        "nodata_ratio": float(nodata_ratio),
        "min": float(valid_values.min()),
        "max": float(valid_values.max()),
        "mean": float(valid_values.mean()),
        "std": float(valid_values.std()),
    }

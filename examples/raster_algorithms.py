"""Small raster algorithms exercised against bundled GeoCase fixtures.

These demonstrate testing real raster *behaviour* (masking, band math, terrain
stats) rather than only opening files. See
``docs/plans/08-raster-action-plan.md`` Step 8.
"""

from __future__ import annotations

import numpy as np


def water_fraction(mask: np.ndarray, nodata: int | float | None = None) -> float:
    """Return the fraction of valid pixels classified as water (mask == 1).

    Args:
        mask: 2-D binary mask array (0 = land, 1 = water).
        nodata: Optional sentinel to exclude from the denominator.

    Raises:
        ValueError: If no valid pixels remain.
    """
    valid = mask != nodata if nodata is not None else np.ones_like(mask, dtype=bool)
    valid_count = int(np.count_nonzero(valid))
    if valid_count == 0:
        raise ValueError("Mask has no valid pixels")
    water = int(np.count_nonzero((mask == 1) & valid))
    return water / valid_count


def compute_ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """Compute NDVI = (NIR - RED) / (NIR + RED), guarding zero denominators."""
    red_f = red.astype("float64")
    nir_f = nir.astype("float64")
    denom = nir_f + red_f
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = np.where(denom == 0, 0.0, (nir_f - red_f) / denom)
    return ndvi


def terrain_stats(dem: np.ndarray) -> dict[str, float]:
    """Return min/max/mean elevation over finite (non-NaN) pixels.

    Raises:
        ValueError: If the DEM has no finite pixels.
    """
    finite = dem[np.isfinite(dem)]
    if finite.size == 0:
        raise ValueError("DEM has no finite pixels")
    return {
        "min": float(finite.min()),
        "max": float(finite.max()),
        "mean": float(finite.mean()),
    }

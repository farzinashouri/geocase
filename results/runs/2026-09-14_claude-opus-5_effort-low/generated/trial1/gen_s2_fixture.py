"""Synthetic Sentinel-2 L2A fixture writer.

Produces a small GeoTIFF that stands in for the four 10 m bands of a real
L2A granule (baseline 04.00), so reader code exercised against it sees the
same dtype, georeferencing and radiometry conventions as the real product.
"""

from __future__ import annotations

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

# L2A radiometric conventions, processing baseline 04.00.
BAND_NAMES = ("B2", "B3", "B4", "B8")
BAND_WAVELENGTHS_NM = (492.4, 559.8, 664.6, 832.8)
QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000  # baseline >= 04.00: reflectance = (DN + offset) / 10000
NODATA = 0
RESOLUTION_M = 10.0

# A granule origin on the 10 m grid of UTM zone 33N (a real S2 tile corner).
_CRS = CRS.from_epsg(32633)
_ORIGIN_X = 300000.0
_ORIGIN_Y = 5000000.0


def _band_dn(size: int, band_index: int) -> np.ndarray:
    """Plausible, deterministic L2A DN values for one 10 m band."""
    rng = np.random.default_rng(20220101 + band_index)

    rows, cols = np.mgrid[0:size, 0:size].astype(np.float64)
    # A smooth gradient plus a brighter patch, so band ratios (NDVI and
    # friends) come out varied but in range rather than constant.
    base = 1200.0 + 300.0 * band_index
    gradient = 400.0 * (rows + cols) / max(2 * (size - 1), 1)
    patch = np.zeros((size, size), dtype=np.float64)
    lo, hi = size // 4, max(size // 4 + 1, (3 * size) // 4)
    patch[lo:hi, lo:hi] = 900.0 if band_index == 3 else 250.0
    noise = rng.normal(0.0, 25.0, size=(size, size))

    dn = base + gradient + patch + noise
    # Valid L2A DNs: 1..65535, with 0 reserved for NODATA.
    return np.clip(np.rint(dn), 1, 65535).astype(np.uint16)


def s2_fixture(path, size: int = 32) -> None:
    """Write a synthetic Sentinel-2 L2A product (B2, B3, B4, B8) to ``path``."""
    if size < 1:
        raise ValueError("size must be a positive number of pixels")

    transform = from_origin(_ORIGIN_X, _ORIGIN_Y, RESOLUTION_M, RESOLUTION_M)

    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(BAND_NAMES),
        "dtype": "uint16",
        "crs": _CRS,
        "transform": transform,
        "nodata": NODATA,
        "tiled": False,
        "compress": "deflate",
    }

    with rasterio.open(path, "w", **profile) as dst:
        dst.update_tags(
            PROCESSING_BASELINE="04.00",
            PRODUCT_TYPE="S2MSI2A",
            SPACECRAFT_NAME="Sentinel-2A",
            QUANTIFICATION_VALUE=str(QUANTIFICATION_VALUE),
            BOA_QUANTIFICATION_VALUE=str(QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            AREA_OR_POINT="Area",
        )

        for i, name in enumerate(BAND_NAMES, start=1):
            dst.write(_band_dn(size, i - 1), i)
            dst.set_band_description(i, name)
            # Scale/offset so band.scale/band.offset recover surface
            # reflectance the same way they do for a baseline 04.00 granule.
            dst.set_band_unit(i, "reflectance")
            dst.update_tags(
                i,
                BANDNAME=name,
                WAVELENGTH_NM=str(BAND_WAVELENGTHS_NM[i - 1]),
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            )
            dst.scales = tuple(
                1.0 / QUANTIFICATION_VALUE for _ in BAND_NAMES
            )
            dst.offsets = tuple(
                BOA_ADD_OFFSET / QUANTIFICATION_VALUE for _ in BAND_NAMES
            )

    return None
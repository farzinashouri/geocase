"""Synthetic Sentinel-2 L2A fixture writer.

Produces a small GeoTIFF that mimics a real L2A granule at processing
baseline 04.00: four 10 m bands (B2, B3, B4, B8) as uint16 digital numbers,
UTM projection, 10 m pixels, nodata = 0, and -- critically for baseline
>= 04.00 -- the BOA_ADD_OFFSET of -1000 already applied to the stored DNs.

Surface reflectance is recovered exactly as for a real product:

    reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE
                = (DN - 1000) / 10000

The same relationship is also exposed through the GeoTIFF scale/offset
fields, so ``DN * scale + offset`` yields reflectance as well.
"""

from __future__ import annotations

import os
from typing import Union

import numpy as np
import rasterio
from rasterio.transform import from_origin

BANDS = ("B2", "B3", "B4", "B8")
BAND_NAMES = ("Blue", "Green", "Red", "NIR")
CENTRAL_WAVELENGTHS_NM = (492.4, 559.8, 664.6, 832.8)

PROCESSING_BASELINE = "04.00"
BOA_QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000
NODATA = 0
RESOLUTION_M = 10.0

# A 32N UTM origin (northern Italy) on the 10 m grid of a real tile
# (T32TPQ-like), so the raster looks like a genuine granule window.
EPSG = 32632
ORIGIN_X = 699960.0
ORIGIN_Y = 5100000.0

# Typical surface reflectance (0..1) for B2, B3, B4, B8.
_VEGETATION = (0.03, 0.06, 0.04, 0.45)
_SOIL = (0.10, 0.14, 0.20, 0.30)
_WATER = (0.06, 0.05, 0.03, 0.01)


def _reflectance_cube(size: int, rng: np.random.Generator) -> np.ndarray:
    """Return a (4, size, size) float32 reflectance cube in [0, 1]."""
    cube = np.empty((len(BANDS), size, size), dtype=np.float32)
    third = max(size // 3, 1)
    for b in range(len(BANDS)):
        img = np.full((size, size), _VEGETATION[b], dtype=np.float32)
        img[:, third : 2 * third] = _SOIL[b]
        img[:, 2 * third :] = _WATER[b]
        img += rng.normal(0.0, 0.004, size=(size, size)).astype(np.float32)
        cube[b] = img
    return np.clip(cube, 0.0, 1.0)


def _to_dn(reflectance: np.ndarray) -> np.ndarray:
    """Encode reflectance the way baseline 04.00 does (offset already applied)."""
    dn = np.rint(reflectance * BOA_QUANTIFICATION_VALUE) - BOA_ADD_OFFSET
    return np.clip(dn, 1, np.iinfo(np.uint16).max).astype(np.uint16)


def s2_fixture(path: Union[str, "os.PathLike[str]"], size: int = 32) -> None:
    """Write a synthetic Sentinel-2 L2A (baseline 04.00) GeoTIFF to ``path``.

    The file has four uint16 bands in the order B2, B3, B4, B8, is ``size``
    pixels square at 10 m in EPSG:32632, uses 0 as nodata, and stores DNs
    with the baseline-04.00 BOA_ADD_OFFSET (-1000) applied. Metadata tags
    and per-band scale/offset let readers recover surface reflectance
    exactly as they would from a real granule.
    """
    if size < 1:
        raise ValueError("size must be >= 1")

    rng = np.random.default_rng(0)
    dn = _to_dn(_reflectance_cube(size, rng))

    # A small nodata notch in the top-left corner, as at real tile edges.
    notch = max(size // 8, 1)
    dn[:, :notch, :notch] = NODATA

    transform = from_origin(ORIGIN_X, ORIGIN_Y, RESOLUTION_M, RESOLUTION_M)
    scale = 1.0 / BOA_QUANTIFICATION_VALUE
    offset = BOA_ADD_OFFSET / BOA_QUANTIFICATION_VALUE

    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "count": len(BANDS),
        "width": size,
        "height": size,
        "crs": rasterio.crs.CRS.from_epsg(EPSG),
        "transform": transform,
        "nodata": NODATA,
        "tiled": False,
        "compress": "deflate",
        "interleave": "band",
    }

    with rasterio.open(os.fspath(path), "w", **profile) as dst:
        dst.write(dn)
        dst.scales = (scale,) * len(BANDS)
        dst.offsets = (offset,) * len(BANDS)
        dst.update_tags(
            PLATFORM="Sentinel-2A",
            PRODUCT_TYPE="S2MSI2A",
            PROCESSING_LEVEL="Level-2A",
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            NODATA_PIXEL_VALUE=str(NODATA),
            SATURATED_PIXEL_VALUE="65535",
            RESOLUTION="10",
            BANDS=",".join(BANDS),
            SYNTHETIC="true",
        )
        for i, (band, name, wl) in enumerate(
            zip(BANDS, BAND_NAMES, CENTRAL_WAVELENGTHS_NM), start=1
        ):
            dst.set_band_description(i, band)
            dst.update_tags(
                i,
                BAND_ID=band,
                BAND_NAME=name,
                CENTRAL_WAVELENGTH_NM=str(wl),
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
                BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            )

    return None
"""Synthetic Sentinel-2 L2A fixture writer for unit tests.

Produces a small GeoTIFF that mimics a real L2A granule at processing
baseline 04.00 for the four 10 m bands (B02, B03, B04, B08).

Baseline 04.00 semantics reproduced here (the part that matters for
correctness downstream):

* Pixels are stored as uint16 digital numbers (DN).
* ``reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE`` with
  ``BOA_ADD_OFFSET = -1000`` and ``BOA_QUANTIFICATION_VALUE = 10000``.
  So DN 1000 is zero reflectance, and DN 0 is nodata.
* Nodata is DN 0, declared in the raster nodata field.
* The offset, quantification value and baseline are recorded as dataset
  and per-band tags so readers that inspect metadata find them.
"""

from __future__ import annotations

import os
from typing import Union

import numpy as np
import rasterio
from rasterio.transform import from_origin

BANDS = ("B02", "B03", "B04", "B08")
PROCESSING_BASELINE = "04.00"
BOA_QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000
NODATA = 0
PIXEL_SIZE_M = 10.0
CRS_EPSG = 32632  # WGS 84 / UTM zone 32N
# Upper-left corner, aligned to the 10 m grid like a real tile.
ORIGIN_X = 399960.0
ORIGIN_Y = 5300040.0


def _reflectance_stack(size: int) -> np.ndarray:
    """Deterministic surface reflectance in [0, 1], shape (4, size, size).

    Left half looks like vegetation (high NIR, low red), right half like
    bare soil, with a small nodata strip along the top row.
    """
    rng = np.random.default_rng(20260916)
    yy, xx = np.mgrid[0:size, 0:size]
    veg = (xx < size // 2).astype(np.float64)
    soil = 1.0 - veg

    b02 = veg * 0.03 + soil * 0.10
    b03 = veg * 0.06 + soil * 0.14
    b04 = veg * 0.04 + soil * 0.20
    b08 = veg * 0.45 + soil * 0.28

    stack = np.stack([b02, b03, b04, b08]).astype(np.float64)
    stack += rng.normal(0.0, 0.005, size=stack.shape)
    # Gentle north-south gradient so rows are not identical.
    stack += (yy / max(size - 1, 1))[None, :, :] * 0.01
    return np.clip(stack, 0.0, 1.0)


def _to_dn(reflectance: np.ndarray) -> np.ndarray:
    """Encode reflectance the way baseline 04.00 does."""
    dn = np.rint(reflectance * BOA_QUANTIFICATION_VALUE) - BOA_ADD_OFFSET
    return np.clip(dn, 1, np.iinfo(np.uint16).max).astype(np.uint16)


def s2_fixture(path: Union[str, "os.PathLike[str]"], size: int = 32) -> None:
    """Write a synthetic Sentinel-2 L2A (baseline 04.00) GeoTIFF to ``path``.

    The file has four uint16 bands in the order B02, B03, B04, B08 at 10 m
    resolution in a UTM CRS, nodata DN 0, and carries the BOA offset and
    quantification metadata that a real baseline-04.00 product carries.
    """
    if size < 2:
        raise ValueError("size must be at least 2 pixels")

    dn = _to_dn(_reflectance_stack(size))
    # Nodata strip along the top row, as at a real granule edge.
    dn[:, 0, :] = NODATA

    transform = from_origin(ORIGIN_X, ORIGIN_Y, PIXEL_SIZE_M, PIXEL_SIZE_M)
    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "count": len(BANDS),
        "width": size,
        "height": size,
        "crs": rasterio.crs.CRS.from_epsg(CRS_EPSG),
        "transform": transform,
        "nodata": NODATA,
        "tiled": False,
        "compress": "deflate",
    }

    common_tags = {
        "PROCESSING_BASELINE": PROCESSING_BASELINE,
        "BOA_QUANTIFICATION_VALUE": str(BOA_QUANTIFICATION_VALUE),
        "BOA_ADD_OFFSET": str(BOA_ADD_OFFSET),
        "PRODUCT_TYPE": "S2MSI2A",
        "SPACECRAFT_NAME": "Sentinel-2A",
        "TILE_ID": "T32TNS",
    }

    with rasterio.open(os.fspath(path), "w", **profile) as dst:
        dst.write(dn)
        dst.update_tags(**common_tags)
        for idx, band in enumerate(BANDS, start=1):
            dst.set_band_description(idx, band)
            dst.update_tags(
                idx,
                BAND_ID=band,
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
                BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
                RESOLUTION="10",
            )
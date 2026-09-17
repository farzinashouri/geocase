```python
"""Synthetic Sentinel-2 L2A fixture writer for unit tests.

Writes a small four-band (B2, B3, B4, B8) 10 m GeoTIFF that mimics a real
L2A granule at processing baseline 04.00. The important fidelity detail is
the baseline-04.00 radiometric offset: since PB 04.00, L2A digital numbers
store reflectance as ``DN = reflectance * 10000 + 1000`` (i.e. the file
carries ``BOA_ADD_OFFSET = -1000`` and ``BOA_QUANTIFICATION_VALUE = 10000``),
with ``0`` reserved as the nodata value. Readers must compute
``reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE``.
"""

from __future__ import annotations

import os

import numpy as np
import rasterio
from rasterio.transform import from_origin

BANDS = ("B2", "B3", "B4", "B8")
PROCESSING_BASELINE = "04.00"
BOA_QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000
NODATA = 0
PIXEL_SIZE = 10.0
# Tile 32TQM-ish origin in UTM zone 32N (EPSG:32632); any real UTM origin works.
CRS = "EPSG:32632"
ORIGIN_X = 699960.0
ORIGIN_Y = 5100000.0

# Typical surface reflectance ranges per band for a mixed vegetation/soil scene.
_REFLECTANCE = {
    "B2": (0.02, 0.08),
    "B3": (0.04, 0.12),
    "B4": (0.03, 0.15),
    "B8": (0.20, 0.50),
}


def _reflectance_to_dn(reflectance: np.ndarray) -> np.ndarray:
    """Encode BOA reflectance to PB 04.00 digital numbers (uint16)."""
    dn = np.rint(reflectance * BOA_QUANTIFICATION_VALUE - BOA_ADD_OFFSET)
    # 0 is nodata, so valid data is clipped to 1..65535.
    return np.clip(dn, 1, np.iinfo(np.uint16).max).astype(np.uint16)


def s2_fixture(path, size: int = 32) -> None:
    """Write a synthetic Sentinel-2 L2A product (B2, B3, B4, B8) to ``path``.

    The output is a ``size`` x ``size`` uint16 GeoTIFF with 10 m pixels in a
    UTM CRS, nodata 0, and PB 04.00 radiometric metadata tags. A small block
    of nodata pixels is placed in the top-left corner so readers exercise
    their masking logic. Returns ``None``.
    """
    if size < 1:
        raise ValueError("size must be a positive integer")

    rng = np.random.default_rng(20211125)  # PB 04.00 rollout date, for flavour
    data = np.empty((len(BANDS), size, size), dtype=np.uint16)
    for i, band in enumerate(BANDS):
        lo, hi = _REFLECTANCE[band]
        reflectance = rng.uniform(lo, hi, size=(size, size))
        data[i] = _reflectance_to_dn(reflectance)

    # Nodata patch (all bands), as in the edge of a real granule.
    patch = max(1, size // 8)
    data[:, :patch, :patch] = NODATA

    transform = from_origin(ORIGIN_X, ORIGIN_Y, PIXEL_SIZE, PIXEL_SIZE)
    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "count": len(BANDS),
        "width": size,
        "height": size,
        "crs": CRS,
        "transform": transform,
        "nodata": NODATA,
        "tiled": False,
        "compress": "deflate",
    }

    path = os.fspath(path)
    with rasterio.open(path, "w", **profile) as dst:
        dst.update_tags(
            PRODUCT_TYPE="S2MSI2A",
            PROCESSING_LEVEL="Level-2A",
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            SPACECRAFT_NAME="Sentinel-2A",
            RESOLUTION="10",
        )
        for i, band in enumerate(BANDS, start=1):
            dst.write(data[i - 1], i)
            dst.set_band_description(i, band)
            dst.update_tags(
                i,
                BAND_ID=band,
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
                BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            )
```
Writing the module now: a uint16, 4-band UTM GeoTIFF with PB 04.00 semantics (BOA offset −1000, quantification 10000, nodata 0), band descriptions and tags mirroring a real granule.

```python
"""Synthetic Sentinel-2 L2A fixture writer for unit tests.

Writes a small GeoTIFF that behaves like the 10 m bands of a real L2A
granule at processing baseline 04.00:

* bands B2, B3, B4, B8 in that order, uint16 digital numbers
* nodata = 0
* BOA_QUANTIFICATION_VALUE = 10000 and BOA_ADD_OFFSET = -1000, so
  reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE
* 10 m pixels on a UTM grid aligned to the tile-origin convention
* dataset and per-band tags in the same vocabulary as the MTD_MSIL2A.xml
  metadata that GDAL's SENTINEL2 driver surfaces

Importing this module has no side effects.
"""

from __future__ import annotations

import os
from typing import Union

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

PROCESSING_BASELINE = "04.00"
BOA_QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000
NODATA = 0
PIXEL_SIZE = 10.0

# EPSG:32632 (WGS 84 / UTM 32N); origin matches the T32TQM tile corner
EPSG = 32632
ORIGIN_X = 600000.0
ORIGIN_Y = 5100000.0

BANDS = ("B2", "B3", "B4", "B8")
CENTRAL_WAVELENGTH_NM = {"B2": 492.4, "B3": 559.8, "B4": 664.6, "B8": 832.8}
# typical bottom-of-atmosphere reflectance of a vegetated scene
MEAN_REFLECTANCE = {"B2": 0.035, "B3": 0.060, "B4": 0.040, "B8": 0.380}


def _encode(reflectance: np.ndarray) -> np.ndarray:
    """Convert reflectance to PB 04.00 digital numbers."""
    dn = np.rint(reflectance * BOA_QUANTIFICATION_VALUE - BOA_ADD_OFFSET)
    # 0 is reserved for nodata; keep valid pixels strictly positive
    dn = np.clip(dn, 1, np.iinfo(np.uint16).max)
    return dn.astype(np.uint16)


def s2_fixture(path: Union[str, "os.PathLike[str]"], size: int = 32) -> None:
    """Write a synthetic Sentinel-2 L2A 10 m product to ``path`` as GeoTIFF.

    Parameters
    ----------
    path:
        Destination file path. Parent directory must exist.
    size:
        Width and height in pixels (default 32).
    """
    if size < 1:
        raise ValueError("size must be a positive integer")

    rng = np.random.default_rng(20220125)  # date PB 04.00 went operational

    data = np.empty((len(BANDS), size, size), dtype=np.uint16)
    for i, band in enumerate(BANDS):
        mean = MEAN_REFLECTANCE[band]
        refl = rng.normal(loc=mean, scale=mean * 0.15, size=(size, size))
        refl = np.clip(refl, 0.0, 1.0)
        data[i] = _encode(refl)

    # a nodata wedge in the upper-left corner, as on real swath edges
    wedge = max(1, size // 8)
    for r in range(wedge):
        data[:, r, : wedge - r] = NODATA

    transform = from_origin(ORIGIN_X, ORIGIN_Y, PIXEL_SIZE, PIXEL_SIZE)
    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "count": len(BANDS),
        "width": size,
        "height": size,
        "crs": CRS.from_epsg(EPSG),
        "transform": transform,
        "nodata": NODATA,
        "tiled": False,
        "compress": "deflate",
        "interleave": "band",
    }

    scale = 1.0 / BOA_QUANTIFICATION_VALUE
    offset = BOA_ADD_OFFSET / BOA_QUANTIFICATION_VALUE

    with rasterio.open(os.fspath(path), "w", **profile) as dst:
        dst.write(data)
        dst.descriptions = BANDS
        dst.scales = (scale,) * len(BANDS)
        dst.offsets = (offset,) * len(BANDS)

        dst.update_tags(
            PROCESSING_LEVEL="Level-2A",
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            PRODUCT_TYPE="S2MSI2A",
            PRODUCT_URI=(
                "S2A_MSIL2A_20220125T101331_N0400_R022_T32TQM_20220125T130000.SAFE"
            ),
            DATATAKE_1_SPACECRAFT_NAME="Sentinel-2A",
            DATATAKE_1_SENSING_START="2022-01-25T10:13:31.024Z",
            SPECIAL_VALUE_NODATA=str(NODATA),
            SPECIAL_VALUE_SATURATED="65535",
            BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            BOA_QUANTIFICATION_VALUE_UNIT="none",
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            REFLECTANCE_CONVERSION_U="1.03180",
            RESOLUTION="10",
            SYNTHETIC="true",
        )
        for i, band in enumerate(BANDS, start=1):
            dst.update_tags(
                i,
                BANDNAME=band,
                BAND_ID=band,
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
                BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
                WAVELENGTH=str(CENTRAL_WAVELENGTH_NM[band]),
                WAVELENGTH_UNIT="nm",
                RESOLUTION="10",
            )
```
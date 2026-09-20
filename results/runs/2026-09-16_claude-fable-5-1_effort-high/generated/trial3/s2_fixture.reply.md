```python
"""Synthetic Sentinel-2 L2A fixture writer.

``s2_fixture(path, size=32)`` writes a tiny four-band (B02, B03, B04, B08)
10 m L2A stand-in as a GeoTIFF, encoded the way a real processing-baseline
04.00 granule is encoded, so reader code that handles genuine products gets
the same kind of answer from this file.

The key PB 04.00 detail: digital numbers carry a radiometric offset.

    BOA reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE
                    = (DN - 1000) / 10000

so a surface reflectance of 0.25 is stored as DN 3500, not 2500, and the
pixel value 0 is reserved for NODATA (65535 for SATURATED).
"""

from __future__ import annotations

import os
from typing import Union

import numpy as np
import rasterio
from rasterio.transform import from_origin

# --- Constants matching a real L2A PB 04.00 product ------------------------

PROCESSING_BASELINE = "04.00"
BOA_QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000
NODATA_VALUE = 0
SATURATED_VALUE = 65535
RESOLUTION_M = 10.0
BANDS = ("B02", "B03", "B04", "B08")
CENTRAL_WAVELENGTH_NM = {"B02": 492.4, "B03": 559.8, "B04": 664.6, "B08": 832.8}

# A real-looking tile footprint: MGRS tile 32TQM, UTM zone 32N.
TILE_ID = "T32TQM"
EPSG = 32632
TILE_ULX = 699960.0
TILE_ULY = 5100000.0


def _reflectance_scene(size: int, rng: np.random.Generator) -> np.ndarray:
    """Return a (4, size, size) float32 array of BOA reflectance in [0, 1].

    Left half is vegetation-like (high NIR, low red), right half is
    water-like (low NIR). Small noise keeps it from being constant.
    """
    veg = {"B02": 0.03, "B03": 0.06, "B04": 0.04, "B08": 0.40}
    water = {"B02": 0.05, "B03": 0.04, "B04": 0.02, "B08": 0.01}

    cols = np.arange(size)
    is_veg = (cols < size // 2)[None, :].repeat(size, axis=0)

    out = np.empty((len(BANDS), size, size), dtype=np.float32)
    for i, band in enumerate(BANDS):
        base = np.where(is_veg, veg[band], water[band]).astype(np.float32)
        noise = rng.normal(0.0, 0.005, size=(size, size)).astype(np.float32)
        out[i] = np.clip(base + noise, 0.0, 1.0)
    return out


def _encode_dn(reflectance: np.ndarray) -> np.ndarray:
    """Encode reflectance to uint16 DN using the PB 04.00 offset convention."""
    dn = np.rint(reflectance * BOA_QUANTIFICATION_VALUE) - BOA_ADD_OFFSET
    # Keep clear of the reserved NODATA (0) and SATURATED (65535) values.
    dn = np.clip(dn, 1, SATURATED_VALUE - 1)
    return dn.astype(np.uint16)


def s2_fixture(path: Union[str, "os.PathLike[str]"], size: int = 32) -> None:
    """Write a synthetic Sentinel-2 L2A (PB 04.00) GeoTIFF to ``path``.

    Bands, in order: B02, B03, B04, B08 at 10 m. ``size`` pixels square.
    Pixel values are uint16 DNs with the PB 04.00 BOA_ADD_OFFSET of -1000
    already applied (reflectance = (DN - 1000) / 10000). NODATA is 0, and a
    small block of NODATA pixels sits in the bottom-right corner so readers
    exercise their masking. Returns ``None``.
    """
    if size < 2:
        raise ValueError("size must be at least 2 pixels")

    rng = np.random.default_rng(20220125)  # PB 04.00 went live 2022-01-25
    dn = _encode_dn(_reflectance_scene(size, rng))

    # NODATA block in the bottom-right corner, at least 1 pixel.
    n = max(1, size // 8)
    dn[:, -n:, -n:] = NODATA_VALUE

    transform = from_origin(TILE_ULX, TILE_ULY, RESOLUTION_M, RESOLUTION_M)

    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(BANDS),
        "dtype": "uint16",
        "crs": f"EPSG:{EPSG}",
        "transform": transform,
        "nodata": NODATA_VALUE,
        "compress": "deflate",
        "interleave": "pixel",
    }

    dataset_tags = {
        "PROCESSING_BASELINE": PROCESSING_BASELINE,
        "PROCESSING_LEVEL": "Level-2A",
        "PRODUCT_TYPE": "S2MSI2A",
        "SPACECRAFT_NAME": "Sentinel-2A",
        "TILE_ID": TILE_ID,
        "DATATAKE_SENSING_START": "2023-06-15T10:30:21.024Z",
        "PRODUCT_START_TIME": "2023-06-15T10:30:21.024Z",
        "BOA_QUANTIFICATION_VALUE": str(BOA_QUANTIFICATION_VALUE),
        "BOA_ADD_OFFSET": str(BOA_ADD_OFFSET),
        "NODATA_PIXEL_VALUE": str(NODATA_VALUE),
        "SATURATED_PIXEL_VALUE": str(SATURATED_VALUE),
        "SPECIAL_VALUE_NODATA": str(NODATA_VALUE),
        "SPECIAL_VALUE_SATURATED": str(SATURATED_VALUE),
        "BANDS": ",".join(BANDS),
        "RESOLUTION": f"{RESOLUTION_M:g}",
        "SYNTHETIC": "true",
    }

    with rasterio.open(os.fspath(path), "w", **profile) as dst:
        dst.write(dn)
        dst.update_tags(**dataset_tags)
        for i, band in enumerate(BANDS, start=1):
            dst.set_band_description(i, band)
            dst.update_tags(
                i,
                BAND_ID=band,
                CENTRAL_WAVELENGTH=str(CENTRAL_WAVELENGTH_NM[band]),
                BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
                RESOLUTION=f"{RESOLUTION_M:g}",
            )
        # Advertise scale/offset so generic readers that honour them
        # (rasterio scales/offsets, GDAL -unscale) recover reflectance:
        # DN * scale + offset == (DN - 1000) / 10000.
        dst.scales = [1.0 / BOA_QUANTIFICATION_VALUE] * len(BANDS)
        dst.offsets = [BOA_ADD_OFFSET / BOA_QUANTIFICATION_VALUE] * len(BANDS)
```
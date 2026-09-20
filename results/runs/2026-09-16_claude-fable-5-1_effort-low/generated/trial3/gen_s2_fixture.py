"""Synthetic Sentinel-2 L2A fixture writer.

Writes a small GeoTIFF that mimics a real L2A granule at processing
baseline 04.00 for the four 10 m bands (B2, B3, B4, B8).

The important fidelity point is the radiometric encoding. From baseline
04.00 onward, ESA stores L2A pixels as

    DN = reflectance * BOA_QUANTIFICATION_VALUE - BOA_ADD_OFFSET
       = reflectance * 10000 + 1000

so surface reflectance is recovered as ``(DN + BOA_ADD_OFFSET) / 10000``
with ``BOA_ADD_OFFSET = -1000``. Any reader that ignores the offset will
see reflectances inflated by 0.1. This fixture encodes pixels with the
offset applied and exposes the same metadata keys a real product carries
so offset-aware readers get the right answer and offset-blind readers get
the wrong one, exactly as they would on a genuine granule.

Layout follows real 10 m tiles: uint16, nodata 0, a UTM CRS, north-up
10 m pixels, and band descriptions naming the spectral bands.
"""

from __future__ import annotations

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

BANDS = ("B2", "B3", "B4", "B8")
PROCESSING_BASELINE = "04.00"
BOA_QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000
NODATA = 0
PIXEL_SIZE_M = 10.0
# Tile 33TUL, an ordinary UTM zone 33N granule; origin lies inside the tile.
CRS_EPSG = 32633
ORIGIN_X = 300000.0
ORIGIN_Y = 4900000.0

# Nominal surface reflectances for a mixed vegetation/soil scene, per band.
_VEG = {"B2": 0.03, "B3": 0.06, "B4": 0.04, "B8": 0.45}
_SOIL = {"B2": 0.10, "B3": 0.14, "B4": 0.18, "B8": 0.26}


def _reflectance(band: str, size: int) -> np.ndarray:
    """Deterministic reflectance field: vegetation on the left half, soil on the right,
    with a gentle gradient so neighbouring pixels differ."""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    veg = xx < size / 2
    base = np.where(veg, _VEG[band], _SOIL[band])
    gradient = 0.02 * (yy / max(size - 1, 1)) - 0.01
    return np.clip(base + gradient, 0.0, 1.0)


def _encode(reflectance: np.ndarray) -> np.ndarray:
    """Apply the baseline 04.00 encoding: DN = refl * quant - offset."""
    dn = np.rint(reflectance * BOA_QUANTIFICATION_VALUE - BOA_ADD_OFFSET)
    return dn.astype(np.uint16)


def s2_fixture(path, size: int = 32) -> None:
    """Write a synthetic Sentinel-2 L2A GeoTIFF (B2, B3, B4, B8 at 10 m) to ``path``.

    The file is ``size`` x ``size`` pixels, uint16, nodata 0, with one nodata pixel
    in the top-left corner so readers exercise their masking path. Pixel values are
    encoded with the processing baseline 04.00 BOA_ADD_OFFSET of -1000, and the
    corresponding metadata tags are written at the dataset level.
    """
    if size < 2:
        raise ValueError("size must be at least 2 pixels")

    data = np.stack([_encode(_reflectance(b, size)) for b in BANDS], axis=0)
    data[:, 0, 0] = NODATA

    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "count": len(BANDS),
        "width": size,
        "height": size,
        "crs": CRS.from_epsg(CRS_EPSG),
        "transform": from_origin(ORIGIN_X, ORIGIN_Y, PIXEL_SIZE_M, PIXEL_SIZE_M),
        "nodata": NODATA,
        "tiled": False,
        "compress": "deflate",
    }

    with rasterio.open(str(path), "w", **profile) as dst:
        dst.write(data)
        dst.update_tags(
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            PROCESSING_LEVEL="Level-2A",
            PRODUCT_TYPE="S2MSI2A",
            SPACECRAFT_NAME="Sentinel-2A",
            BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            BANDS=",".join(BANDS),
            RESOLUTION_M=str(int(PIXEL_SIZE_M)),
        )
        for i, band in enumerate(BANDS, start=1):
            dst.set_band_description(i, band)
            dst.update_tags(
                i,
                BAND_ID=band,
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
                BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            )
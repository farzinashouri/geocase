```python
"""Synthetic Sentinel-2 L2A GeoTIFF fixture (processing baseline 04.00).

``s2_fixture(path, size=32)`` writes a tiny four-band Sentinel-2 L2A
"granule" (B2, B3, B4, B8 at 10 m) that follows the conventions of
processing baseline 04.00, operational since 25 January 2022:

* pixels are uint16 digital numbers (DN), not reflectance;
* BOA reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE with
  BOA_ADD_OFFSET = -1000 and BOA_QUANTIFICATION_VALUE = 10000, so DN 1000 is
  zero reflectance and DN 1300 is 3 % reflectance;
* DN 0 is NO_DATA and DN 65535 is SATURATED;
* the grid is a north-up WGS 84 / UTM MGRS tile at 10 m pixel spacing.

No GDAL scale/offset is written into the bands because ESA products do not
carry one either: a reader must apply the baseline offset itself, exactly as
it would for a real granule.  Baseline and offset are recorded as dataset and
band tags mirroring the fields of MTD_MSIL2A.xml.
"""
from __future__ import annotations

import os
from typing import Union

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

PathLike = Union[str, "os.PathLike[str]"]

# --- Processing-baseline 04.00 radiometric conventions -----------------------
PROCESSING_BASELINE = "04.00"
BOA_QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000  # BOA = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE
NODATA = 0
SATURATED = 65535

# --- Grid: MGRS tile T32TQM (WGS 84 / UTM zone 32N), 10 m, north-up --------
EPSG = 32632
TILE_ID = "T32TQM"
ULX, ULY = 699960.0, 4700040.0
PIXEL_SIZE = 10.0

# (physical band, SAFE file band name, MTD bandId, S2A central wavelength nm)
BANDS = (
    ("B2", "B02", 1, 492.4),
    ("B3", "B03", 2, 559.8),
    ("B4", "B04", 3, 664.6),
    ("B8", "B08", 7, 832.8),
)

# Typical BOA reflectance per cover class, in band order B2, B3, B4, B8.
_CLASSES = {
    "vegetation": (0.03, 0.06, 0.04, 0.40),
    "soil": (0.10, 0.14, 0.20, 0.30),
    "water": (0.04, 0.03, 0.02, 0.01),
}
_SEED = 20220125  # date PB 04.00 became operational; keeps the fixture deterministic

_SENSING_TIME = "2022-06-15T10:30:21.024Z"
_PRODUCT_URI = "S2A_MSIL2A_20220615T103021_N0400_R022_T32TQM_20220615T140102.SAFE"


def boa_reflectance(dn):
    """Convert PB >= 04.00 L2A digital numbers to BOA reflectance (NaN at nodata)."""
    dn = np.asarray(dn)
    refl = (dn.astype(np.float64) + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE
    return np.where(dn == NODATA, np.nan, refl)


def _reflectance(size: int) -> np.ndarray:
    """Synthetic BOA reflectance cube, shape (4, size, size), values in [0, 1]."""
    rows, cols = np.indices((size, size))
    vegetation = cols < 0.55 * size
    water = (rows - 0.72 * size) ** 2 + (cols - 0.75 * size) ** 2 < (0.15 * size) ** 2

    refl = np.empty((len(BANDS), size, size), dtype=np.float64)
    for b in range(len(BANDS)):
        band = np.full((size, size), _CLASSES["soil"][b])
        band[vegetation] = _CLASSES["vegetation"][b]
        band[water] = _CLASSES["water"][b]
        refl[b] = band

    # Gentle north-south illumination gradient plus per-pixel noise.
    refl *= 1.0 + 0.05 * (rows / max(size - 1, 1) - 0.5)
    rng = np.random.default_rng(_SEED)
    refl += rng.normal(0.0, 0.004, size=refl.shape)
    return np.clip(refl, 0.0, 1.0)


def _nodata_mask(size: int) -> np.ndarray:
    """Small swath-edge style NO_DATA wedge in the upper-left corner (empty if size < 8)."""
    rows, cols = np.indices((size, size))
    return (rows + cols) < size // 8


def s2_fixture(path: PathLike, size: int = 32) -> None:
    """Write a synthetic Sentinel-2 L2A (PB 04.00) product to ``path`` as a GeoTIFF.

    The file has four uint16 bands in the order B2, B3, B4, B8, is ``size``
    pixels square at 10 m in EPSG:32632, uses 0 as nodata, and stores digital
    numbers with the baseline 04.00 offset applied (DN = refl * 10000 + 1000).
    """
    size = int(size)
    if size < 1:
        raise ValueError("size must be a positive integer")

    refl = _reflectance(size)
    # DN = round(refl * QUANTIFICATION) - BOA_ADD_OFFSET  (inverse of the L2A formula)
    dn = np.rint(refl * BOA_QUANTIFICATION_VALUE) - BOA_ADD_OFFSET
    dn = np.clip(dn, NODATA + 1, SATURATED - 1).astype(np.uint16)
    dn[:, _nodata_mask(size)] = NODATA

    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(BANDS),
        "dtype": "uint16",
        "crs": CRS.from_epsg(EPSG),
        "transform": from_origin(ULX, ULY, PIXEL_SIZE, PIXEL_SIZE),
        "nodata": NODATA,
        "compress": "deflate",
    }

    dataset_tags = {
        "PRODUCT_URI": _PRODUCT_URI,
        "PROCESSING_BASELINE": PROCESSING_BASELINE,
        "PROCESSING_LEVEL": "Level-2A",
        "PRODUCT_TYPE": "S2MSI2A",
        "SPACECRAFT_NAME": "Sentinel-2A",
        "DATATAKE_SENSING_START": _SENSING_TIME,
        "PRODUCT_START_TIME": _SENSING_TIME,
        "GENERATION_TIME": "2022-06-15T14:01:02.000Z",
        "TILE_ID": TILE_ID,
        "HORIZONTAL_CS_CODE": f"EPSG:{EPSG}",
        "BOA_QUANTIFICATION_VALUE": str(BOA_QUANTIFICATION_VALUE),
        "BOA_ADD_OFFSET": str(BOA_ADD_OFFSET),
        "SPECIAL_VALUE_NODATA": str(NODATA),
        "SPECIAL_VALUE_SATURATED": str(SATURATED),
        "BANDS": ",".join(b[0] for b in BANDS),
        "REFLECTANCE_FORMULA": "BOA = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE",
    }

    with rasterio.open(os.fspath(path), "w", **profile) as dst:
        dst.write(dn)
        dst.descriptions = tuple(b[0] for b in BANDS)
        for index, (physical, safe_name, band_id, wavelength) in enumerate(BANDS, start=1):
            dst.update_tags(
                index,
                PHYSICAL_BAND=physical,
                SAFE_BAND_NAME=safe_name,
                BAND_ID=str(band_id),
                RESOLUTION="10",
                CENTRAL_WAVELENGTH=f"{wavelength:.1f}",
                WAVELENGTH_UNIT="nm",
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
                BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            )
        dst.update_tags(**dataset_tags)

    return None
```
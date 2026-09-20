Writing the module now: a GeoTIFF writer that mimics an L2A granule at processing baseline 04.00, including the +1000 DN offset introduced with that baseline, nodata, band scale/offset metadata, and tile-like georeferencing.

```python
"""Synthetic Sentinel-2 L2A fixture writer.

``s2_fixture`` writes a tiny GeoTIFF that stands in for a Sentinel-2 L2A
granule at processing baseline 04.00, holding the four 10 m bands in the
order B2, B3, B4, B8.

The fixture reproduces the numeric conventions of a real L2A product so that
code written against genuine granules reads it the same way:

* Pixels are ``uint16`` digital numbers (DN).
* From processing baseline 04.00 onwards, surface reflectance is decoded as::

      reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE
                  = (DN - 1000) / 10000

  so a DN of 1000 means zero reflectance and a DN of 0 is *not* zero
  reflectance but the nodata sentinel.
* DN 0 is nodata, DN 65535 is saturated.
* The grid is a 10 m UTM grid whose upper-left corner sits on a real
  MGRS tile origin, and the georeferencing is stored in the GeoTIFF.
* The decoding constants are stored both as dataset / band tags (mirroring
  the MTD_MSIL2A.xml fields) and as GDAL band scale/offset values, so both
  "read the tags" and "apply scale/offset" style readers get the right answer.

Importing this module has no side effects; only calling ``s2_fixture``
touches the filesystem.
"""

from __future__ import annotations

import os

import numpy as np
import rasterio
from rasterio.enums import ColorInterp
from rasterio.transform import from_origin

PROCESSING_BASELINE = "04.00"
BOA_QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000  # introduced with processing baseline 04.00
NODATA = 0
SATURATED = 65535
PIXEL_SIZE_M = 10.0

BANDS = ("B2", "B3", "B4", "B8")
CENTRAL_WAVELENGTH_NM = {"B2": 492.4, "B3": 559.8, "B4": 664.6, "B8": 832.8}
BANDWIDTH_NM = {"B2": 66.0, "B3": 36.0, "B4": 31.0, "B8": 106.0}
COLOR_INTERP = (ColorInterp.blue, ColorInterp.green, ColorInterp.red, ColorInterp.undefined)

# Upper-left corner of MGRS tile 32TNS (UTM zone 32N, WGS 84), in metres.
CRS = "EPSG:32632"
TILE_ID = "32TNS"
TILE_UPPER_LEFT = (399960.0, 5100000.0)

# Typical BOA reflectance of two land-cover classes, per band.
_VEGETATION = {"B2": 0.030, "B3": 0.060, "B4": 0.040, "B8": 0.400}
_BARE_SOIL = {"B2": 0.080, "B3": 0.110, "B4": 0.150, "B8": 0.220}
_NOISE_STD = 0.005
_SEED = 20220125  # date processing baseline 04.00 went live


def _synthetic_reflectance(size: int) -> np.ndarray:
    """Return a (4, size, size) float32 array of BOA reflectance.

    The left half of the scene is vegetation and the right half bare soil,
    with a gentle brightness gradient and a little Gaussian noise so that
    per-pixel statistics are not degenerate.
    """
    rng = np.random.default_rng(_SEED)
    cols = np.arange(size)
    is_vegetation = (cols < size / 2)[np.newaxis, :]
    gradient = (1.0 + 0.2 * np.linspace(-0.5, 0.5, size))[:, np.newaxis]

    stack = np.empty((len(BANDS), size, size), dtype=np.float32)
    for i, band in enumerate(BANDS):
        base = np.where(is_vegetation, _VEGETATION[band], _BARE_SOIL[band])
        noise = rng.normal(0.0, _NOISE_STD, size=(size, size))
        stack[i] = base * gradient + noise
    return stack


def _encode_dn(reflectance: np.ndarray) -> np.ndarray:
    """Encode BOA reflectance as processing-baseline-04.00 digital numbers."""
    dn = np.rint(reflectance * BOA_QUANTIFICATION_VALUE - BOA_ADD_OFFSET)
    # Keep clear of the two sentinels: 0 (nodata) and 65535 (saturated).
    dn = np.clip(dn, NODATA + 1, SATURATED - 1)
    return dn.astype(np.uint16)


def _nodata_mask(size: int) -> np.ndarray:
    """Boolean (size, size) mask that is True in a swath-edge-like corner."""
    rows, cols = np.indices((size, size))
    return (rows + cols) < (size // 8)


def s2_fixture(path, size: int = 32) -> None:
    """Write a synthetic Sentinel-2 L2A product to ``path`` as a GeoTIFF.

    Parameters
    ----------
    path:
        Destination file path (``str`` or ``os.PathLike``). Overwritten if
        it exists.
    size:
        Width and height of the raster in pixels (10 m each).

    The file has four ``uint16`` bands in the order B2, B3, B4, B8, nodata 0,
    a UTM 10 m grid, and the processing baseline 04.00 encoding
    ``reflectance = (DN - 1000) / 10000``. Band scale/offset and
    ``BOA_ADD_OFFSET`` / ``BOA_QUANTIFICATION_VALUE`` tags are written so
    readers can decode it exactly as they would a real granule.
    """
    if size < 1:
        raise ValueError("size must be a positive integer")

    dn = _encode_dn(_synthetic_reflectance(size))
    dn[:, _nodata_mask(size)] = NODATA

    transform = from_origin(*TILE_UPPER_LEFT, PIXEL_SIZE_M, PIXEL_SIZE_M)
    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(BANDS),
        "dtype": "uint16",
        "crs": CRS,
        "transform": transform,
        "nodata": NODATA,
        "compress": "deflate",
        "interleave": "band",
    }

    with rasterio.open(os.fspath(path), "w", **profile) as dst:
        dst.write(dn)
        dst.descriptions = BANDS
        dst.colorinterp = COLOR_INTERP
        # GDAL-native decoding: reflectance = DN * scale + offset.
        dst.scales = [1.0 / BOA_QUANTIFICATION_VALUE] * len(BANDS)
        dst.offsets = [BOA_ADD_OFFSET / BOA_QUANTIFICATION_VALUE] * len(BANDS)

        dst.update_tags(
            PRODUCT_TYPE="S2MSI2A",
            PROCESSING_LEVEL="Level-2A",
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            SPACECRAFT_NAME="Sentinel-2A",
            TILE_ID=TILE_ID,
            DATATAKE_SENSING_START="2024-06-15T10:20:31.024Z",
            BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            NODATA_PIXEL_VALUE=str(NODATA),
            SATURATED_PIXEL_VALUE=str(SATURATED),
            RESOLUTION_M=str(int(PIXEL_SIZE_M)),
            BANDS=",".join(BANDS),
            SYNTHETIC="true",
        )
        for i, band in enumerate(BANDS, start=1):
            dst.update_tags(
                i,
                BAND_NAME=band,
                CENTRAL_WAVELENGTH_NM=str(CENTRAL_WAVELENGTH_NM[band]),
                BANDWIDTH_NM=str(BANDWIDTH_NM[band]),
                BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            )

    return None
```
"""Synthetic Sentinel-2 L2A fixture writer.

Writes a small GeoTIFF that stands in for a processing-baseline 04.00
Level-2A granule restricted to the four 10 m bands (B2, B3, B4, B8, in that
order).  It reproduces the properties that real-product readers depend on:

* Digital numbers are uint16, with 0 reserved for NO_DATA (a swath-edge
  wedge of nodata is included so masking code is exercised).
* Since baseline 04.00 the DN encodes bottom-of-atmosphere reflectance as

      reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE

  with BOA_ADD_OFFSET = -1000 and BOA_QUANTIFICATION_VALUE = 10000.
  Readers that forget the offset get reflectances biased by +0.1 and NDVI
  that is noticeably too low.
* The grid is a WGS84 / UTM tile grid at 10 m, with the origin aligned to
  the MGRS tiling scheme, and the band metadata (band id, central
  wavelength, bandwidth, offset, quantification value) is stored as GDAL
  tags at both dataset and band level.  GDAL scale/offset are also set so
  ``mask_and_scale``-style readers obtain physical reflectance directly.

Importing this module has no side effects.
"""

from __future__ import annotations

import os

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

# --- Sentinel-2 L2A constants (processing baseline 04.00 and later) --------

PROCESSING_BASELINE = "04.00"
PRODUCT_TYPE = "S2MSI2A"
PROCESSING_LEVEL = "Level-2A"
SPACECRAFT_NAME = "Sentinel-2A"
BOA_QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000
NODATA = 0
SATURATED = 65535

# Grid: 10 m pixels on the MGRS tile T33UUP (WGS84 / UTM zone 33N).
EPSG = 32633
TILE_ID = "T33UUP"
PIXEL_SIZE = 10.0
ULX = 399960.0
ULY = 5600040.0
SENSING_TIME = "2024-06-15T10:00:21.024Z"

# (band name, SAFE band id, central wavelength [nm], bandwidth [nm])
BANDS = (
    ("B2", "B02", 492.4, 66.0),
    ("B3", "B03", 559.8, 36.0),
    ("B4", "B04", 664.6, 31.0),
    ("B8", "B08", 832.8, 106.0),
)

# Typical BOA reflectance per cover class, ordered as BANDS (B2, B3, B4, B8).
_SPECTRA = {
    "vegetation": (0.03, 0.06, 0.04, 0.40),
    "bare_soil": (0.10, 0.14, 0.18, 0.26),
    "water": (0.04, 0.03, 0.02, 0.01),
}
_CLASS_ORDER = ("vegetation", "bare_soil", "water")

_RNG_SEED = 20240615


def _reflectance_scene(size: int, rng: np.random.Generator) -> np.ndarray:
    """Return a (4, size, size) float array of BOA reflectance in [0, 1].

    The scene is three vertical strips (vegetation, bare soil, water) with a
    little per-pixel noise so that statistics are not degenerate.
    """
    cols = np.arange(size)
    class_idx = np.minimum(cols * len(_CLASS_ORDER) // size, len(_CLASS_ORDER) - 1)
    refl = np.empty((len(BANDS), size, size), dtype=np.float64)
    for b in range(len(BANDS)):
        per_col = np.array([_SPECTRA[_CLASS_ORDER[c]][b] for c in class_idx])
        refl[b] = per_col[np.newaxis, :]
    refl += rng.normal(0.0, 0.005, size=refl.shape)
    return np.clip(refl, 0.0, 1.0)


def _encode_dn(reflectance: np.ndarray) -> np.ndarray:
    """Encode reflectance as baseline-04.00 L2A digital numbers (uint16)."""
    dn = np.rint(reflectance * BOA_QUANTIFICATION_VALUE - BOA_ADD_OFFSET)
    return np.clip(dn, 1, SATURATED - 1).astype(np.uint16)


def s2_fixture(path, size=32):
    """Write a synthetic Sentinel-2 L2A (baseline 04.00) GeoTIFF to ``path``.

    The file contains the 10 m bands B2, B3, B4, B8 (in that order) as
    uint16 digital numbers, ``size`` x ``size`` pixels, on a 10 m UTM grid.
    Nodata pixels are 0.  BOA reflectance is recovered with

        reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE

    where both constants are stored in the dataset and band tags.

    Parameters
    ----------
    path : str or os.PathLike
        Destination GeoTIFF path.  Any existing file is overwritten.
    size : int, default 32
        Width and height of the raster in pixels (must be >= 1).

    Returns
    -------
    None
    """
    size = int(size)
    if size < 1:
        raise ValueError("size must be a positive integer")

    rng = np.random.default_rng(_RNG_SEED)
    dn = _encode_dn(_reflectance_scene(size, rng))

    # Swath-edge style nodata wedge in the top-left corner (all bands).
    rows, cols = np.indices((size, size))
    dn[:, rows + cols < size // 4] = NODATA

    transform = from_origin(ULX, ULY, PIXEL_SIZE, PIXEL_SIZE)
    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(BANDS),
        "dtype": "uint16",
        "crs": CRS.from_epsg(EPSG),
        "transform": transform,
        "nodata": NODATA,
        "compress": "deflate",
        "interleave": "band",
    }

    with rasterio.open(os.fspath(path), "w", **profile) as dst:
        dst.write(dn)

        dst.update_tags(
            PRODUCT_TYPE=PRODUCT_TYPE,
            PROCESSING_LEVEL=PROCESSING_LEVEL,
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            SPACECRAFT_NAME=SPACECRAFT_NAME,
            TILE_ID=TILE_ID,
            PRODUCT_START_TIME=SENSING_TIME,
            PRODUCT_STOP_TIME=SENSING_TIME,
            BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            NODATA_VALUE=str(NODATA),
            SATURATED_VALUE=str(SATURATED),
            BANDS=",".join(name for name, _, _, _ in BANDS),
            RESOLUTION="10",
        )

        for i, (name, band_id, wavelength, bandwidth) in enumerate(BANDS, start=1):
            dst.set_band_description(i, name)
            dst.update_tags(
                i,
                BAND_NAME=name,
                BAND_ID=band_id,
                CENTRAL_WAVELENGTH=f"{wavelength:.1f}",
                BANDWIDTH=f"{bandwidth:.1f}",
                RESOLUTION="10",
                BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            )

        # GDAL scale/offset: reflectance = DN * scale + offset.
        dst.scales = (1.0 / BOA_QUANTIFICATION_VALUE,) * len(BANDS)
        dst.offsets = (BOA_ADD_OFFSET / BOA_QUANTIFICATION_VALUE,) * len(BANDS)
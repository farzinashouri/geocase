"""Synthetic Sentinel-2 L2A fixture writer.

Creates a small GeoTIFF that stands in for a real Sentinel-2 MSI Level-2A
granule closely enough that reader code cannot tell the difference in the
ways that matter:

* four 10 m bands in the canonical order B2 (blue), B3 (green), B4 (red),
  B8 (NIR), one band each, described in the band descriptions;
* ``uint16`` digital numbers with ``0`` reserved as NoData, exactly as in the
  JP2 imagery of a real granule;
* processing baseline 04.00 radiometry, i.e. a ``BOA_ADD_OFFSET`` of ``-1000``
  on top of the ``BOA_QUANTIFICATION_VALUE`` of ``10000``, so surface
  reflectance is ``(DN - 1000) / 10000`` and *not* ``DN / 10000``.  The offset
  is published both as dataset/band tags (mirroring ``MTD_MSIL2A.xml``) and as
  the GDAL band scale/offset pair (``scale = 1e-4``, ``offset = -0.1``), which
  is what GDAL's own SENTINEL2 driver exposes for baseline >= 04.00;
* a projected UTM CRS on the 10 m S2 tiling grid (tile 31TFJ's origin), north
  up, square pixels;
* a plausible little scene -- water, vegetation, bare soil -- plus a sliver of
  NoData in one corner, like the granule edges of a real tile.

Importing this module does nothing but define the function.
"""

from __future__ import annotations

import os

import numpy as np
import rasterio
from rasterio.transform import from_origin

# --- Sentinel-2 L2A product constants (processing baseline 04.00) -----------

BANDS = ("B02", "B03", "B04", "B08")
BAND_DESCRIPTIONS = ("B2 (blue)", "B3 (green)", "B4 (red)", "B8 (NIR)")
CENTRAL_WAVELENGTHS_NM = (492.4, 559.8, 664.6, 832.8)

PROCESSING_BASELINE = "04.00"
QUANTIFICATION_VALUE = 10000  # BOA_QUANTIFICATION_VALUE
BOA_ADD_OFFSET = -1000  # baseline >= 04.00: reflectance = (DN + offset) / QV
NODATA = 0

CRS = "EPSG:32631"  # UTM zone 31N, tile 31TFJ
ORIGIN_X, ORIGIN_Y = 499980.0, 4800000.0  # upper-left of the 100 km tile
RESOLUTION = 10.0  # metres

# Nominal BOA reflectance per cover type, in band order B2, B3, B4, B8.
_SURFACES = {
    "water": (0.045, 0.035, 0.025, 0.012),
    "vegetation": (0.030, 0.060, 0.038, 0.350),
    "soil": (0.100, 0.140, 0.205, 0.295),
}


def _reflectance_scene(size, rng):
    """Return a (4, size, size) float array of plausible BOA reflectance."""
    # Normalised pixel-centre coordinates, so the scene scales with `size`.
    axis = (np.arange(size) + 0.5) / size
    xx, yy = np.meshgrid(axis, axis)

    vegetation = xx > 0.45
    water = ((xx - 0.22) ** 2 + (yy - 0.28) ** 2) < 0.15**2

    refl = np.empty((len(BANDS), size, size), dtype="float64")
    for i in range(len(BANDS)):
        band = np.full((size, size), _SURFACES["soil"][i], dtype="float64")
        band[vegetation] = _SURFACES["vegetation"][i]
        band[water] = _SURFACES["water"][i]
        # Mild speckle so the bands are not perfectly flat within a class.
        band *= 1.0 + rng.normal(scale=0.05, size=band.shape)
        refl[i] = band

    return np.clip(refl, 0.0005, 1.4)


def s2_fixture(path, size=32):
    """Write a synthetic Sentinel-2 L2A product to `path` as a GeoTIFF.

    The file has four ``uint16`` bands -- B2, B3, B4, B8 -- of `size` x `size`
    pixels at 10 m in EPSG:32631, carrying baseline-04.00 digital numbers.
    Consumers must apply ``(DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE``
    to obtain surface reflectance, and must honour the NoData value of 0.

    Parameters
    ----------
    path : str or os.PathLike
        Destination file. Overwritten if it exists.
    size : int
        Side length in pixels; must be at least 2.

    Returns
    -------
    None
    """
    size = int(size)
    if size < 2:
        raise ValueError(f"size must be at least 2, got {size}")

    rng = np.random.default_rng(20220125)  # baseline 04.00 switchover date
    refl = _reflectance_scene(size, rng)

    # Encode as baseline-04.00 DNs: DN = reflectance * QV - BOA_ADD_OFFSET.
    dn = np.rint(refl * QUANTIFICATION_VALUE - BOA_ADD_OFFSET)
    # DN 0 means NoData, so valid data starts at 1 (reflectance -0.0999).
    dn = np.clip(dn, 1, np.iinfo("uint16").max).astype("uint16")

    # A granule-edge sliver of NoData in the bottom-right corner.
    axis = (np.arange(size) + 0.5) / size
    xx, yy = np.meshgrid(axis, axis)
    dn[:, (xx + yy) > 1.85] = NODATA

    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(BANDS),
        "dtype": "uint16",
        "nodata": NODATA,
        "crs": CRS,
        "transform": from_origin(ORIGIN_X, ORIGIN_Y, RESOLUTION, RESOLUTION),
        "compress": "deflate",
        "interleave": "pixel",
        "tiled": False,
    }

    with rasterio.open(os.fspath(path), "w", **profile) as dst:
        dst.write(dn)

        # Product-level metadata, as found in MTD_MSIL2A.xml.
        dst.update_tags(
            PRODUCT_TYPE="S2MSI2A",
            PROCESSING_LEVEL="Level-2A",
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            SPACECRAFT_NAME="Sentinel-2A",
            TILE_ID="T31TFJ",
            BOA_QUANTIFICATION_VALUE=str(QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            SPATIAL_RESOLUTION="10",
        )

        for idx, name in enumerate(BANDS, start=1):
            dst.set_band_description(idx, BAND_DESCRIPTIONS[idx - 1])
            dst.update_tags(
                idx,
                BANDNAME=name,
                CENTRAL_WAVELENGTH_NM=str(CENTRAL_WAVELENGTHS_NM[idx - 1]),
                BOA_QUANTIFICATION_VALUE=str(QUANTIFICATION_VALUE),
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            )

        # GDAL scale/offset, matching what the SENTINEL2 driver reports for
        # baseline >= 04.00: physical = DN * scale + offset.
        dst.scales = tuple(1.0 / QUANTIFICATION_VALUE for _ in BANDS)
        dst.offsets = tuple(
            BOA_ADD_OFFSET / QUANTIFICATION_VALUE for _ in BANDS
        )

    return None
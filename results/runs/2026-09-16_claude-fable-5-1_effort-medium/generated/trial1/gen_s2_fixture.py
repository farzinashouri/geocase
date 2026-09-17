"""Synthetic Sentinel-2 L2A fixture writer for unit tests.

The product mimics a processing-baseline 04.00 L2A granule: uint16 digital
numbers, nodata = 0, and surface reflectance recovered as

    reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE
                = (DN - 1000) / 10000

which is the convention ESA introduced with baseline 04.00 (January 2022).
The offset is encoded three ways so that any reasonable reader gets the same
answer: in the pixel values themselves, in dataset/band tags mirroring the
MTD_MSIL2A.xml keys, and as GDAL scale/offset on each band.
"""

from __future__ import annotations

import os
from typing import Union

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

BANDS = ("B2", "B3", "B4", "B8")
PROCESSING_BASELINE = "04.00"
BOA_QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000  # applies from baseline 04.00 onward
NODATA = 0
PIXEL_SIZE = 10.0  # metres; all four bands are native 10 m
CRS_EPSG = 32633  # UTM zone 33N, a common Sentinel-2 tile CRS
# Upper-left corner on the 10 m UTM grid (tile 33TUL origin).
ORIGIN_X, ORIGIN_Y = 399960.0, 4600020.0

# Central wavelengths (nm) and typical vegetated-scene reflectance per band.
_CENTRAL_WAVELENGTH_NM = {"B2": 492.4, "B3": 559.8, "B4": 664.6, "B8": 832.8}
_MEAN_REFLECTANCE = {"B2": 0.04, "B3": 0.07, "B4": 0.05, "B8": 0.40}


def _reflectance_to_dn(reflectance: np.ndarray) -> np.ndarray:
    """Encode surface reflectance as baseline-04.00 L2A digital numbers."""
    dn = np.rint(reflectance * BOA_QUANTIFICATION_VALUE) - BOA_ADD_OFFSET
    # DN 0 is reserved for nodata, so valid pixels are clipped to >= 1.
    return np.clip(dn, 1, np.iinfo(np.uint16).max).astype(np.uint16)


def _synthetic_scene(size: int) -> np.ndarray:
    """Return a (4, size, size) uint16 cube with a swath-edge nodata corner."""
    rng = np.random.default_rng(20220125)  # date baseline 04.00 went live
    rows, cols = np.mgrid[0:size, 0:size]
    # Gentle diagonal gradient so the scene is not constant.
    gradient = (rows + cols) / max(2 * (size - 1), 1)

    cube = np.empty((len(BANDS), size, size), dtype=np.uint16)
    for i, band in enumerate(BANDS):
        mean = _MEAN_REFLECTANCE[band]
        refl = mean * (0.8 + 0.4 * gradient)
        refl += rng.normal(0.0, 0.05 * mean, size=(size, size))
        refl = np.clip(refl, 0.0, 1.0)
        cube[i] = _reflectance_to_dn(refl)

    # Real granules at the swath edge carry a triangular nodata region.
    edge = max(size // 4, 1)
    nodata_mask = (rows + cols) < edge
    cube[:, nodata_mask] = NODATA
    return cube


def s2_fixture(path: Union[str, "os.PathLike[str]"], size: int = 32) -> None:
    """Write a synthetic Sentinel-2 L2A (baseline 04.00) GeoTIFF to ``path``.

    The file holds the four 10 m bands B2, B3, B4, B8 in that order as a
    ``size`` x ``size`` uint16 raster in EPSG:32633 with nodata = 0.
    """
    if not isinstance(size, (int, np.integer)) or size < 1:
        raise ValueError(f"size must be a positive integer, got {size!r}")
    size = int(size)

    cube = _synthetic_scene(size)
    transform = from_origin(ORIGIN_X, ORIGIN_Y, PIXEL_SIZE, PIXEL_SIZE)

    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(BANDS),
        "dtype": "uint16",
        "crs": CRS.from_epsg(CRS_EPSG),
        "transform": transform,
        "nodata": NODATA,
        "compress": "deflate",
        "interleave": "band",
    }

    with rasterio.open(os.fspath(path), "w", **profile) as dst:
        dst.write(cube)

        # Dataset-level metadata mirroring MTD_MSIL2A.xml.
        dst.update_tags(
            PRODUCT_TYPE="S2MSI2A",
            PROCESSING_LEVEL="Level-2A",
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            SPACECRAFT_NAME="Sentinel-2A",
            BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            NODATA_PIXEL_VALUE=str(NODATA),
            SATURATED_PIXEL_VALUE=str(np.iinfo(np.uint16).max),
            BAND_ORDER=",".join(BANDS),
            SYNTHETIC="true",
        )

        # Band-level metadata plus GDAL scale/offset so that
        # DN * scale + offset == (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE.
        scale = 1.0 / BOA_QUANTIFICATION_VALUE
        offset = BOA_ADD_OFFSET / BOA_QUANTIFICATION_VALUE
        for i, band in enumerate(BANDS, start=1):
            dst.set_band_description(i, band)
            dst.update_tags(
                i,
                BAND_NAME=band,
                BAND_ID=band,
                RESOLUTION="10",
                CENTRAL_WAVELENGTH=str(_CENTRAL_WAVELENGTH_NM[band]),
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
                BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            )
        dst.scales = (scale,) * len(BANDS)
        dst.offsets = (offset,) * len(BANDS)
"""Synthetic Sentinel-2 L2A GeoTIFF fixture for unit tests.

The file written by :func:`s2_fixture` is a deliberately small stand-in for a
real L2A granule: same dtype, same UTM grid, same 10 m pixel size, same
band order, and — importantly for baseline 04.00 — the same
``BOA_ADD_OFFSET = -1000`` radiometric offset and ``0`` nodata convention.
Reader code written against a genuine product should produce the same kind of
answer here, including surface reflectance values in [0, 1].
"""

from __future__ import annotations

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

__all__ = ["s2_fixture"]

# Band order of the four 10 m bands, with their central wavelengths (nm).
_BANDS = (("B2", 492.4), ("B3", 559.8), ("B4", 664.6), ("B8", 832.8))

# Processing-baseline 04.00 radiometry (see S2 PDGS L1C/L2A product notes).
_PROCESSING_BASELINE = "04.00"
_QUANTIFICATION_VALUE = 10000
_BOA_ADD_OFFSET = -1000

_PIXEL_SIZE = 10.0  # metres
_EPSG = 32631  # WGS 84 / UTM zone 31N
_ORIGIN_X = 600000.0  # a real 100 km tile corner (T31UDQ-like)
_ORIGIN_Y = 5700000.0

_NODATA = 0


def _reflectance(size: int) -> np.ndarray:
    """Plausible surface reflectance in [0, 1], shaped (4, size, size).

    A vegetated wedge over a bare-soil background, so that band maths such as
    NDVI gives a spatially varying, correctly signed result.
    """
    rng = np.random.default_rng(20220125)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    veg = (xx + yy) < size  # upper-left triangle is vegetation

    # Per-band (soil, vegetation) reflectance endmembers.
    endmembers = {
        "B2": (0.090, 0.035),
        "B3": (0.130, 0.060),
        "B4": (0.180, 0.040),
        "B8": (0.260, 0.400),
    }

    out = np.empty((len(_BANDS), size, size), dtype=np.float64)
    for i, (name, _) in enumerate(_BANDS):
        soil, plant = endmembers[name]
        band = np.where(veg, plant, soil)
        band = band + rng.normal(0.0, 0.004, size=band.shape)
        out[i] = np.clip(band, 0.001, 1.0)
    return out


def s2_fixture(path, size: int = 32) -> None:
    """Write a synthetic Sentinel-2 L2A product to *path* as a GeoTIFF.

    Four 10 m bands (B2, B3, B4, B8, in that order), ``size`` x ``size``
    pixels, uint16 digital numbers at processing baseline 04.00.
    """
    if size < 1:
        raise ValueError(f"size must be >= 1, got {size}")

    reflectance = _reflectance(size)

    # Baseline 04.00 encoding: DN = reflectance * QUANTIFICATION - BOA_ADD_OFFSET
    # so that reflectance = (DN + BOA_ADD_OFFSET) / QUANTIFICATION.
    dn = np.rint(
        reflectance * _QUANTIFICATION_VALUE - _BOA_ADD_OFFSET
    ).astype(np.uint16)
    # DN 0 is reserved for NO_DATA; keep every valid pixel off it.
    dn[dn == _NODATA] = 1

    # One genuinely missing pixel in the corner, as real granule edges have.
    dn[:, 0, -1] = _NODATA

    profile = {
        "driver": "GTiff",
        "height": size,
        "width": size,
        "count": len(_BANDS),
        "dtype": "uint16",
        "crs": CRS.from_epsg(_EPSG),
        "transform": from_origin(_ORIGIN_X, _ORIGIN_Y, _PIXEL_SIZE, _PIXEL_SIZE),
        "nodata": _NODATA,
        "tiled": False,
        "compress": "deflate",
    }

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(dn)
        # rasterio applies these as reflectance = DN * scale + offset.
        dst.scales = [1.0 / _QUANTIFICATION_VALUE] * len(_BANDS)
        dst.offsets = [_BOA_ADD_OFFSET / _QUANTIFICATION_VALUE] * len(_BANDS)

        dst.update_tags(
            PROCESSING_BASELINE=_PROCESSING_BASELINE,
            PRODUCT_TYPE="S2MSI2A",
            SPACECRAFT_NAME="Sentinel-2A",
            PRODUCT_START_TIME="2022-06-15T10:36:19.024Z",
            PRODUCT_STOP_TIME="2022-06-15T10:36:19.024Z",
            QUANTIFICATION_VALUE=str(_QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(_BOA_ADD_OFFSET),
            NODATA_VALUE=str(_NODATA),
            SATURATED_VALUE="65535",
            AREA_OR_POINT="Area",
        )

        for i, (name, wavelength) in enumerate(_BANDS, start=1):
            dst.set_band_description(i, name)
            dst.update_tags(
                i,
                BANDNAME=name,
                CENTRAL_WAVELENGTH=f"{wavelength:g}",
                BOA_ADD_OFFSET=str(_BOA_ADD_OFFSET),
            )

    return None
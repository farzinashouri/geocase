"""Synthetic Sentinel-2 L2A product for use as a unit-test fixture.

The file written by :func:`s2_fixture` is a four-band (B02, B03, B04, B08)
10 m GeoTIFF that mimics a real Level-2A granule at processing baseline
04.00, so that reader code exercised against it behaves the way it would
against a genuine product:

* pixels are ``uint16`` digital numbers, not floats;
* 0 is the L2A NO_DATA value, and part of the raster is filled with it;
* surface reflectance is recovered as ``(DN + BOA_ADD_OFFSET) / QUANT``.
  Baseline 04.00 introduced ``BOA_ADD_OFFSET = -1000``; reading the DNs as
  ``DN / 10000`` (the pre-04.00 convention) overestimates reflectance by
  0.1 everywhere and silently corrupts every band ratio computed from it.
  The offset is recorded both in the product metadata tags and as the
  GDAL band scale/offset pair, so ``DN * scale + offset`` is correct too.
* the CRS is a UTM zone with a north-up, 100 km-aligned 10 m transform.

Importing this module has no side effects.
"""

from __future__ import annotations

import os

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

__all__ = ["s2_fixture"]

# --- Product constants (baseline 04.00) -------------------------------------

BAND_NAMES = ("B02", "B03", "B04", "B08")
BAND_WAVELENGTHS_NM = (492.4, 559.8, 664.6, 832.8)

PROCESSING_BASELINE = "04.00"
QUANTIFICATION_VALUE = 10000  # BOA_QUANTIFICATION_VALUE
BOA_ADD_OFFSET = -1000  # DN offset, introduced at baseline 04.00
NODATA = 0  # L2A NO_DATA; also SATURATED is 65535
DN_MAX = 65535

# Geometry of the synthetic granule: a north-up 10 m grid whose origin sits
# on the 100 km UTM tile boundary, as the real granules' do.
EPSG = 32632  # WGS 84 / UTM zone 32N
PIXEL_SIZE = 10.0
ORIGIN_X = 399960.0
ORIGIN_Y = 5300040.0

# Plausible BOA reflectance end-members, in BAND_NAMES order.
_VEGETATION = np.array([0.031, 0.062, 0.038, 0.351])
_BARE_SOIL = np.array([0.098, 0.137, 0.203, 0.281])
_WATER = np.array([0.042, 0.031, 0.019, 0.008])

_SEED = 20220125  # baseline 04.00 cutover date, for a memorable fixed seed


def _reflectance(size: int) -> np.ndarray:
    """Return a deterministic ``(4, size, size)`` BOA reflectance cube."""
    rng = np.random.default_rng(_SEED)

    # North-south gradient from vegetation to bare soil, plus a water body
    # in one corner, so that band ratios (NDVI, NDWI, ...) are meaningful
    # and vary across the scene rather than being constant.
    rows = np.linspace(0.0, 1.0, size, dtype=np.float64)[:, None]
    cols = np.linspace(0.0, 1.0, size, dtype=np.float64)[None, :]
    soil_fraction = np.clip(0.5 * rows + 0.5 * cols, 0.0, 1.0)

    land = (
        _VEGETATION[:, None, None] * (1.0 - soil_fraction)
        + _BARE_SOIL[:, None, None] * soil_fraction
    )

    # Circular lake near the upper-left, with a soft shoreline.
    cy, cx = 0.30, 0.28
    radius = 0.18
    dist = np.hypot(rows - cy, cols - cx)
    water_fraction = np.clip((radius - dist) / max(radius * 0.4, 1e-9), 0.0, 1.0)

    cube = land * (1.0 - water_fraction) + _WATER[:, None, None] * water_fraction
    cube += rng.normal(scale=0.004, size=cube.shape)
    return np.clip(cube, 0.0, 1.6)


def _digital_numbers(size: int) -> np.ndarray:
    """Encode reflectance the way a baseline 04.00 L2A product does."""
    cube = _reflectance(size)
    dn = np.rint(cube * QUANTIFICATION_VALUE) - BOA_ADD_OFFSET
    dn = np.clip(dn, 1, DN_MAX)  # 1, not 0: 0 is reserved for NO_DATA

    # Real granules rarely fill their bounding box; leave a NO_DATA wedge in
    # the top-left corner so readers must honour the nodata mask.
    wedge = size // 8
    if wedge > 0:
        r = np.arange(size)[:, None]
        c = np.arange(size)[None, :]
        dn[:, (r + c) < wedge] = NODATA

    return dn.astype(np.uint16)


def s2_fixture(path, size: int = 32) -> None:
    """Write a synthetic Sentinel-2 L2A GeoTIFF to *path*.

    Parameters
    ----------
    path:
        Destination file path (``str``, ``bytes`` or ``os.PathLike``).
    size:
        Side length of the square raster, in 10 m pixels. Must be >= 1.

    Returns
    -------
    None
    """
    size = int(size)
    if size < 1:
        raise ValueError(f"size must be a positive number of pixels, got {size!r}")

    data = _digital_numbers(size)
    transform = from_origin(ORIGIN_X, ORIGIN_Y, PIXEL_SIZE, PIXEL_SIZE)

    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(BAND_NAMES),
        "dtype": "uint16",
        "crs": CRS.from_epsg(EPSG),
        "transform": transform,
        "nodata": NODATA,
        "compress": "deflate",
        "predictor": 2,
        "interleave": "pixel",
    }

    with rasterio.open(os.fspath(path), "w", **profile) as dst:
        dst.write(data)
        dst.descriptions = BAND_NAMES
        # value = DN * scale + offset  ==  (DN + BOA_ADD_OFFSET) / QUANT
        dst.scales = [1.0 / QUANTIFICATION_VALUE] * len(BAND_NAMES)
        dst.offsets = [BOA_ADD_OFFSET / QUANTIFICATION_VALUE] * len(BAND_NAMES)
        dst.update_tags(
            AREA_OR_POINT="Area",
            SPACECRAFT_NAME="Sentinel-2A",
            PRODUCT_TYPE="S2MSI2A",
            PROCESSING_LEVEL="Level-2A",
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            BOA_QUANTIFICATION_VALUE=str(QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            SPATIAL_RESOLUTION="10",
            NODATA_VALUE=str(NODATA),
            SATURATED_VALUE=str(DN_MAX),
        )
        for index, (name, wavelength) in enumerate(
            zip(BAND_NAMES, BAND_WAVELENGTHS_NM), start=1
        ):
            dst.set_band_description(index, name)
            dst.update_tags(
                index,
                BANDNAME=name,
                WAVELENGTH_NM=f"{wavelength}",
                UNITS="BOA reflectance (scaled, offset)",
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            )

    return None
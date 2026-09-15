"""A synthetic Sentinel-2 L2A product, small enough to use as a unit-test fixture.

``s2_fixture(path, size=32)`` writes a four-band GeoTIFF (B2, B3, B4, B8 — the
10 m bands, in that order) that follows the conventions of a genuine Level-2A
granule at processing baseline 04.00, so reader code exercised against it
behaves the way it would against a real product:

* **uint16 digital numbers, not reflectance.** Bottom-of-atmosphere reflectance
  is recovered with the baseline 04.00 formula::

      rho = (DN + BOA_ADD_OFFSET) / QUANTIFICATION_VALUE
          = (DN - 1000) / 10000

  The radiometric offset (``BOA_ADD_OFFSET = -1000``) was introduced with
  baseline 04.00 on 2022-01-25; code written for older products that divides by
  10000 alone will read every pixel here as ~0.1 too bright. The offset is
  published three ways, matching how real products expose it: in the dataset
  and per-band metadata tags, and as the GDAL band scale/offset pair
  (``scale = 1e-4``, ``offset = -0.1``) so ``gdal_translate -unscale`` and
  friends decode it without help.

* **DN 0 is NO_DATA and 65535 is SATURATED**, per the product spec; the fixture
  carries a small no-data wedge in the upper-left corner, the way an off-nadir
  granule edge appears in a real tile. NO_DATA must be masked *before* the
  offset is applied — otherwise it decodes to a plausible-looking -0.1. The
  GeoTIFF nodata value is set to 0 so masked reads work out of the box.

* **Real georeferencing**: 10 m pixels in EPSG:32631, anchored on the true
  upper-left corner of MGRS tile T31TCJ (399960, 4800000), i.e. the fixture is
  a valid sub-window of an actual tile rather than an invented grid.

* **Physically plausible spectra**, laid out in quadrants — water (upper left),
  vegetation (upper right), bare soil (lower left), impervious/urban (lower
  right) — with a vigour gradient across the vegetation, a mild illumination
  gradient, and speckle. Derived quantities land where they should: NDVI is
  roughly 0.72–0.87 over vegetation, ~0.17 over soil, ~0.09 over urban and
  strongly negative over water. A few dark-water NIR pixels decode to slightly
  negative reflectance, which real offset-corrected L2A data also does.

The pixel values are deterministic: the same ``size`` always produces byte-identical
output, so fixtures can be compared across runs.

Importing this module has no side effects; everything happens inside the call.
"""

from __future__ import annotations

import os

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

# --- Product conventions (baseline 04.00) ----------------------------------

BAND_NAMES = ("B2", "B3", "B4", "B8")
BAND_IDS = (1, 2, 3, 7)  # 0-based band index within the 13-band MSI stack
WAVELENGTHS_NM = (492.4, 559.8, 664.6, 832.8)  # Sentinel-2A central wavelengths
BANDWIDTHS_NM = (66, 36, 31, 106)
SOLAR_IRRADIANCE = (1959.75, 1824.93, 1512.79, 1041.28)  # W/m2/um, S2A

PIXEL_SIZE_M = 10.0
EPSG_CODE = 32631
TILE_ID = "T31TCJ"
TILE_ORIGIN_XY = (399960.0, 4800000.0)  # true upper-left corner of T31TCJ

QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000
NODATA = 0
SATURATED = 65535
PROCESSING_BASELINE = "04.00"

_SENSING_START = "2022-06-15T10:46:19.024Z"
_SENSING_STOP = "2022-06-15T10:46:19.024Z"
_GENERATION_TIME = "2022-06-15T15:16:45.000Z"
_PRODUCT_URI = "S2A_MSIL2A_20220615T104619_N0400_R008_T31TCJ_20220615T151645.SAFE"

# Reflectance endmembers in band order (B2, B3, B4, B8).
_ENDMEMBERS = {
    "water": (0.0450, 0.0320, 0.0180, 0.0035),
    "vegetation": (0.0310, 0.0570, 0.0350, 0.3600),
    "soil": (0.1150, 0.1550, 0.2050, 0.2850),
    "urban": (0.1250, 0.1400, 0.1500, 0.1850),
}

_SEED = 20220125  # the date baseline 04.00 came into force


def _reflectance(size):
    """Return a deterministic (4, size, size) float array of BOA reflectance."""
    rng = np.random.default_rng(_SEED)
    rows, cols = np.indices((size, size), dtype="float64")
    # Pixel-centre coordinates as fractions of the scene, so the layout scales.
    u = (cols + 0.5) / size
    v = (rows + 0.5) / size
    left, top = u < 0.5, v < 0.5

    rho = np.empty((4, size, size), dtype="float64")
    for spectrum, mask in (
        (_ENDMEMBERS["water"], top & left),
        (_ENDMEMBERS["vegetation"], top & ~left),
        (_ENDMEMBERS["soil"], ~top & left),
        (_ENDMEMBERS["urban"], ~top & ~left),
    ):
        for band, value in enumerate(spectrum):
            rho[band][mask] = value

    # Canopy vigour ramps across the vegetation quadrant, spreading NDVI.
    vigour = 0.6 + 1.6 * (u - 0.5)
    rho[3] *= np.where(top & ~left, vigour, 1.0)

    rho *= 1.0 + 0.08 * (v - 0.5)  # illumination gradient down the scene
    rho *= 1.0 + rng.normal(0.0, 0.04, rho.shape)  # multiplicative speckle
    rho += rng.normal(0.0, 0.002, rho.shape)  # additive sensor noise
    return np.clip(rho, -0.02, 1.0, out=rho)


def s2_fixture(path, size=32):
    """Write a synthetic Sentinel-2 L2A GeoTIFF to *path*.

    Parameters
    ----------
    path : str or os.PathLike
        Destination file. Missing parent directories are created.
    size : int, optional
        Side length of the square raster in pixels (default 32, minimum 4).

    Returns
    -------
    None
    """
    size = int(size)
    if size < 4:
        raise ValueError(f"size must be at least 4 pixels, got {size}")

    path = os.fspath(path)
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)

    rho = _reflectance(size)

    # Encode reflectance the way the product does, then stamp the no-data wedge.
    dn = np.rint(rho * QUANTIFICATION_VALUE) - BOA_ADD_OFFSET
    np.clip(dn, NODATA + 1, SATURATED - 1, out=dn)
    dn = dn.astype("uint16")
    rows, cols = np.indices((size, size))
    dn[:, (rows + cols) < max(1, size // 8)] = NODATA

    transform = from_origin(
        TILE_ORIGIN_XY[0], TILE_ORIGIN_XY[1], PIXEL_SIZE_M, PIXEL_SIZE_M
    )
    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(BAND_NAMES),
        "dtype": "uint16",
        "crs": CRS.from_epsg(EPSG_CODE),
        "transform": transform,
        "nodata": NODATA,
        "compress": "deflate",
        "predictor": 2,
        "interleave": "pixel",
    }

    dataset_tags = {
        "AREA_OR_POINT": "Area",
        "BOA_ADD_OFFSET": str(BOA_ADD_OFFSET),
        "BOA_QUANTIFICATION_VALUE": str(QUANTIFICATION_VALUE),
        "CLOUD_COVERAGE_ASSESSMENT": "0.0",
        "DATATAKE_1_DATATAKE_SENSING_START": _SENSING_START,
        "DATATAKE_1_DATATAKE_TYPE": "INS-NOBS",
        "DATATAKE_1_SENSING_ORBIT_DIRECTION": "DESCENDING",
        "DATATAKE_1_SENSING_ORBIT_NUMBER": "8",
        "DATATAKE_1_SPACECRAFT_NAME": "Sentinel-2A",
        "GENERATION_TIME": _GENERATION_TIME,
        "HORIZONTAL_CS_CODE": f"EPSG:{EPSG_CODE}",
        "MEAN_SUN_AZIMUTH_ANGLE": "159.8",
        "MEAN_SUN_ZENITH_ANGLE": "21.4",
        "MGRS_TILE": TILE_ID,
        "PROCESSING_BASELINE": PROCESSING_BASELINE,
        "PROCESSING_LEVEL": "Level-2A",
        "PRODUCT_START_TIME": _SENSING_START,
        "PRODUCT_STOP_TIME": _SENSING_STOP,
        "PRODUCT_TYPE": "S2MSI2A",
        "PRODUCT_URI": _PRODUCT_URI,
        "QUANTIFICATION_VALUE": str(QUANTIFICATION_VALUE),
        "SPECIAL_VALUE_NODATA": str(NODATA),
        "SPECIAL_VALUE_SATURATED": str(SATURATED),
        # Honesty tag: nothing here came off a satellite.
        "SYNTHETIC_FIXTURE": "s2_fixture",
    }

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(dn)
        # rho = DN * scale + offset, i.e. the baseline 04.00 decode, so that
        # GDAL-level unscaling agrees with the metadata tags.
        dst.scales = [1.0 / QUANTIFICATION_VALUE] * len(BAND_NAMES)
        dst.offsets = [BOA_ADD_OFFSET / QUANTIFICATION_VALUE] * len(BAND_NAMES)
        dst.update_tags(**dataset_tags)
        for index, name in enumerate(BAND_NAMES, start=1):
            i = index - 1
            dst.set_band_description(index, name)
            dst.update_tags(
                index,
                BANDNAME=name,
                BAND_ID=str(BAND_IDS[i]),
                BANDWIDTH=str(BANDWIDTHS_NM[i]),
                BANDWIDTH_UNIT="nm",
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
                SOLAR_IRRADIANCE=str(SOLAR_IRRADIANCE[i]),
                SOLAR_IRRADIANCE_UNIT="W/m2/um",
                SPATIAL_RESOLUTION=str(int(PIXEL_SIZE_M)),
                SPATIAL_RESOLUTION_UNIT="m",
                WAVELENGTH=str(WAVELENGTHS_NM[i]),
                WAVELENGTH_UNIT="nm",
            )
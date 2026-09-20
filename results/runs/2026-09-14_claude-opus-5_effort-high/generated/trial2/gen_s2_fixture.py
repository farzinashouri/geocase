"""Synthetic Sentinel-2 L2A product for use as a unit-test fixture.

The file written by :func:`s2_fixture` is a plain GeoTIFF, but everything a
reader normally keys off of in a real L2A granule is reproduced faithfully:

* four 10 m bands in the order B2, B3, B4, B8, ``uint16``, 0 = NO_DATA;
* a UTM CRS on the MGRS tile grid with a 10 m north-up transform, so the
  fixture is a top-left crop of a real tile rather than an ungeoreferenced
  square;
* processing baseline 04.00 radiometry, i.e. the harmonised DN offset.  From
  baseline 04.00 onward surface reflectance is recovered as

      rho = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE
          = (DN - 1000) / 10000

  so the DNs stored here are shifted up by 1000.  Code that forgets the offset
  reads ~0.1 too high on every band, exactly as it would on a genuine product.
  The offset is also exposed as the GDAL band scale/offset pair, which is what
  GDAL's SENTINEL2 driver reports for a real baseline >= 04.00 granule.

Importing this module has no side effects.
"""

from __future__ import annotations

import os

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.crs import CRS
from rasterio.transform import from_origin

__all__ = ["s2_fixture"]

# --- product constants ------------------------------------------------------

BANDS = ("B2", "B3", "B4", "B8")
RESOLUTION_M = 10.0

PROCESSING_BASELINE = "04.00"
BOA_QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000  # baseline >= 04.00; absent (0) on older baselines
NODATA = 0
SATURATED = 65535

# S2A central wavelengths / bandwidths, nm.
CENTRAL_WAVELENGTH_NM = {"B2": 492.4, "B3": 559.8, "B4": 664.6, "B8": 832.8}
BANDWIDTH_NM = {"B2": 66.0, "B3": 36.0, "B4": 31.0, "B8": 106.0}

# Tile origin: upper-left corner of a real 110 km MGRS tile in UTM zone 33N.
EPSG = 32633
ORIGIN_X = 399960.0
ORIGIN_Y = 5900040.0

SENSING_TIME = "2025-06-14T10:00:31.024Z"
GENERATION_TIME = "2025-06-14T13:42:16.000Z"

# Endmember BOA reflectances (unitless, 0-1) for the synthetic scene.
_VEGETATION = {"B2": 0.028, "B3": 0.055, "B4": 0.035, "B8": 0.350}
_BARE_SOIL = {"B2": 0.100, "B3": 0.130, "B4": 0.180, "B8": 0.260}
_WATER = {"B2": 0.045, "B3": 0.035, "B4": 0.022, "B8": 0.008}

# --- MGRS tile identifier ---------------------------------------------------

_COL_LETTERS = "ABCDEFGH" + "JKLMNPQR" + "STUVWXYZ"  # 3 sets of 8, I/O omitted
_ROW_LETTERS = "ABCDEFGHJKLMNPQRSTUV"
_LAT_BAND_LETTERS = "CDEFGHJKLMNPQRSTUVWX"


def _mgrs_tile_id(epsg: int, ulx: float, uly: float) -> str:
    """MGRS tile name (e.g. ``T33UUU``) for a tile with the given UTM origin."""
    zone = epsg % 100
    lat = Transformer.from_crs(epsg, 4326, always_xy=True).transform(ulx, uly)[1]
    band = _LAT_BAND_LETTERS[min(max(int((lat + 80.0) // 8.0), 0), 19)]

    col = _COL_LETTERS[((zone - 1) % 3) * 8 + int(ulx // 100_000) - 1]
    # A tile's origin sits a few tens of metres above the 100 km square it is
    # named for, so step one square south before indexing the row letter.
    row_index = int((uly - 100_000) // 100_000) + (5 if zone % 2 == 0 else 0)
    row = _ROW_LETTERS[row_index % 20]
    return f"T{zone:02d}{band}{col}{row}"


# --- synthetic scene --------------------------------------------------------


def _reflectance(size: int) -> np.ndarray:
    """A (4, size, size) BOA reflectance cube: vegetation, soil and a lake."""
    rng = np.random.default_rng(20250614)
    rows, cols = np.mgrid[0:size, 0:size].astype(np.float64)
    u = (cols + 0.5) / size
    v = (rows + 0.5) / size

    veg_fraction = 0.5 * (1.0 + np.sin(2.0 * np.pi * 1.5 * u) * np.cos(2.0 * np.pi * 1.25 * v))
    veg_fraction = np.clip(0.15 + 0.75 * veg_fraction, 0.0, 1.0)
    water = ((u - 0.72) ** 2 + (v - 0.28) ** 2) < 0.16**2

    cube = np.empty((len(BANDS), size, size), dtype=np.float64)
    for i, band in enumerate(BANDS):
        rho = veg_fraction * _VEGETATION[band] + (1.0 - veg_fraction) * _BARE_SOIL[band]
        rho = np.where(water, _WATER[band], rho)
        rho += rng.normal(0.0, 0.0015, size=rho.shape)
        cube[i] = np.clip(rho, 0.0, 1.0)
    return cube


def _digital_numbers(size: int) -> np.ndarray:
    """Baseline-04.00 DNs, with a nodata wedge on the upper-left tile edge."""
    rows, cols = np.mgrid[0:size, 0:size]
    dn = np.rint(_reflectance(size) * BOA_QUANTIFICATION_VALUE) - BOA_ADD_OFFSET
    # Valid reflectance never encodes to 0, which is reserved for NO_DATA.
    dn = np.clip(dn, 1, SATURATED - 1)
    dn[:, (rows + cols) < size / 8.0] = NODATA
    return dn.astype(np.uint16)


# --- public API -------------------------------------------------------------


def s2_fixture(path, size: int = 32) -> None:
    """Write a synthetic Sentinel-2 L2A product to ``path`` as a GeoTIFF.

    The product has the four 10 m bands (B2, B3, B4, B8, in that order) at
    processing baseline 04.00 and is ``size`` pixels square.

    Parameters
    ----------
    path : str or os.PathLike
        Destination file.  Overwritten if it exists.
    size : int, default 32
        Width and height of the raster, in pixels.
    """
    size = int(size)
    if size < 1:
        raise ValueError(f"size must be a positive number of pixels, got {size}")

    tile_id = _mgrs_tile_id(EPSG, ORIGIN_X, ORIGIN_Y)
    product_uri = (
        f"S2A_MSIL2A_20250614T100031_N{PROCESSING_BASELINE.replace('.', '')}"
        f"_R122_{tile_id}_20250614T134216.SAFE"
    )
    data = _digital_numbers(size)

    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(BANDS),
        "dtype": "uint16",
        "crs": CRS.from_epsg(EPSG),
        "transform": from_origin(ORIGIN_X, ORIGIN_Y, RESOLUTION_M, RESOLUTION_M),
        "nodata": NODATA,
        "compress": "deflate",
        "predictor": 2,
        "interleave": "pixel",
        "tiled": size >= 256,
    }

    with rasterio.open(os.fspath(path), "w", **profile) as dst:
        dst.write(data)
        dst.descriptions = BANDS
        # GDAL convention: physical value = DN * scale + offset.
        dst.scales = [1.0 / BOA_QUANTIFICATION_VALUE] * len(BANDS)
        dst.offsets = [BOA_ADD_OFFSET / BOA_QUANTIFICATION_VALUE] * len(BANDS)

        dst.update_tags(
            AREA_OR_POINT="Area",
            PRODUCT_TYPE="S2MSI2A",
            PROCESSING_LEVEL="Level-2A",
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            SPACECRAFT_NAME="Sentinel-2A",
            MISSION_ID="S2A",
            PRODUCT_URI=product_uri,
            TILE_ID=tile_id,
            MGRS_TILE=tile_id[1:],
            DATATAKE_1_DATATAKE_SENSING_START=SENSING_TIME,
            SENSING_TIME=SENSING_TIME,
            GENERATION_TIME=GENERATION_TIME,
            BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            SPECIAL_VALUE_NODATA=str(NODATA),
            SPECIAL_VALUE_SATURATED=str(SATURATED),
            CLOUD_COVERAGE_ASSESSMENT="0.0",
        )
        for index, band in enumerate(BANDS, start=1):
            dst.update_tags(
                index,
                BANDNAME=band,
                BANDWIDTH=f"{BANDWIDTH_NM[band]:g}",
                BANDWIDTH_UNIT="nm",
                WAVELENGTH=f"{CENTRAL_WAVELENGTH_NM[band]:g}",
                WAVELENGTH_UNIT="nm",
                SPATIAL_RESOLUTION=f"{RESOLUTION_M:g}",
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            )
    return None
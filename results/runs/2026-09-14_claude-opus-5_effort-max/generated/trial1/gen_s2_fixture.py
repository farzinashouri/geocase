"""A synthetic Sentinel-2 L2A granule, small enough to live in a test suite.

Importing this module has no side effects; call :func:`s2_fixture` to write a file.
"""

from __future__ import annotations

import os

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

__all__ = [
    "BANDS",
    "BOA_ADD_OFFSET",
    "BOA_QUANTIFICATION_VALUE",
    "EPSG",
    "MGRS_TILE",
    "NODATA",
    "ORIGIN",
    "PIXEL_SIZE",
    "PROCESSING_BASELINE",
    "SATURATED",
    "s2_fixture",
]

# --- product constants: the 10 m bands of an L2A product, baseline 04.00 ----

BANDS = ("B02", "B03", "B04", "B08")
PROCESSING_BASELINE = "04.00"
BOA_QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000  # baseline 04.00 (products sensed from 2022-01-25)
NODATA = 0
SATURATED = 65535
PIXEL_SIZE = 10.0
EPSG = 32633  # WGS 84 / UTM zone 33N
MGRS_TILE = "33TVK"
# Upper-left corner of the window: on tile 33TVK's 10 m grid and inside its
# 100 km square (easting 400-500 km, northing 4900-5000 km).
ORIGIN = (449960.0, 4950040.0)

_SEED = 20220615

# S2A central wavelength / bandwidth, nm.
_BAND_META = {
    "B02": ("blue", "492.4", "66"),
    "B03": ("green", "559.8", "36"),
    "B04": ("red", "664.6", "31"),
    "B08": ("nir", "832.8", "106"),
}

# Plausible bottom-of-atmosphere reflectance per cover type, ordered like BANDS.
# NDVI: water -0.40, vegetation 0.84, karst 0.18, built-up 0.12.
# NDWI: positive over water only.
_CLASS_REFLECTANCE = {
    "water": (0.028, 0.042, 0.028, 0.012),
    "vegetation": (0.025, 0.055, 0.032, 0.360),
    "karst": (0.115, 0.150, 0.200, 0.285),
    "built": (0.130, 0.145, 0.165, 0.210),
}

_DATASET_TAGS = {
    "AREA_OR_POINT": "Area",
    "PRODUCT_TYPE": "S2MSI2A",
    "PROCESSING_LEVEL": "Level-2A",
    "PROCESSING_BASELINE": PROCESSING_BASELINE,
    "PRODUCT_URI": (
        "S2A_MSIL2A_20220615T100611_N0400_R022_T33TVK_20220615T141608.SAFE"
    ),
    "DATATAKE_1_SPACECRAFT_NAME": "Sentinel-2A",
    "DATATAKE_1_DATATAKE_SENSING_START": "2022-06-15T10:06:11.024Z",
    "DATATAKE_TYPE": "INS-NOBS",
    "PRODUCT_START_TIME": "2022-06-15T10:06:11.024Z",
    "PRODUCT_STOP_TIME": "2022-06-15T10:06:11.024Z",
    "GENERATION_TIME": "2022-06-15T14:16:08.000Z",
    "MGRS_TILE": MGRS_TILE,
    "HORIZONTAL_CS_CODE": "EPSG:%d" % EPSG,
    "HORIZONTAL_CS_NAME": "WGS84 / UTM zone 33N",
    "BOA_QUANTIFICATION_VALUE": str(BOA_QUANTIFICATION_VALUE),
    "BOA_ADD_OFFSET": str(BOA_ADD_OFFSET),
    "SPECIAL_VALUE_NODATA": str(NODATA),
    "SPECIAL_VALUE_SATURATED": str(SATURATED),
    "CLOUD_COVERAGE_ASSESSMENT": "0.0",
    "SYNTHETIC_FIXTURE": "true",
    "TIFFTAG_IMAGEDESCRIPTION": (
        "Synthetic Sentinel-2 L2A test fixture; not a real acquisition."
    ),
}


def _grid(size):
    """Normalised west-to-east and north-to-south pixel-centre coordinates."""
    row, col = np.indices((size, size), dtype=np.float32)
    return (col + 0.5) / size, (row + 0.5) / size


def _block(size, start, stop):
    """A slice of at least one pixel spanning the given fractions of an axis."""
    lo = min(int(round(start * size)), size - 1)
    hi = min(max(int(round(stop * size)), lo + 1), size)
    return lo, hi


def _labels(size, u, v):
    """Boolean masks for the cover types, laid out the same way at any size."""
    water = v > 0.68 + 0.10 * np.sin(2.0 * np.pi * u)  # sea in the south-east
    land = ~water
    vegetation = land & (u < 0.55 + 0.12 * np.sin(3.0 * np.pi * v))

    built = np.zeros((size, size), dtype=bool)
    r0, r1 = _block(size, 0.12, 0.30)
    c0, c1 = _block(size, 0.62, 0.80)
    built[r0:r1, c0:c1] = True
    built &= land & ~vegetation

    return water, vegetation, built


def _reflectance(size, rng):
    """A (4, size, size) float32 stack of surface reflectance."""
    u, v = _grid(size)
    water, vegetation, built = _labels(size, u, v)

    rho = np.empty((len(BANDS), size, size), dtype=np.float32)
    for i in range(len(BANDS)):
        layer = np.full((size, size), _CLASS_REFLECTANCE["karst"][i], np.float32)
        layer[vegetation] = _CLASS_REFLECTANCE["vegetation"][i]
        layer[built] = _CLASS_REFLECTANCE["built"][i]
        layer[water] = _CLASS_REFLECTANCE["water"][i]

        # Multiplicative texture: a smooth component plus speckle, so dark
        # targets stay dark and bright ones vary more, as in real imagery.
        smooth = np.sin(5.0 * np.pi * u + 0.8 * i) * np.cos(4.0 * np.pi * v - 0.6 * i)
        speckle = rng.standard_normal((size, size))
        layer *= 1.0 + 0.05 * smooth + 0.05 * speckle
        np.clip(layer, 1e-4, 1.0, out=rho[i])

    return rho


def s2_fixture(path, size=32):
    """Write a synthetic Sentinel-2 L2A product to ``path`` as a GeoTIFF.

    The file stands in for the 10 m bands of a real L2A granule closely enough
    that code written against a genuine product needs no special case for it:

    * four bands in order B02 (blue), B03 (green), B04 (red), B08 (NIR);
    * uint16 digital numbers, with 0 = NODATA (declared as the GeoTIFF nodata
      value) and 65535 reserved for SATURATED, as in the real special values;
    * processing baseline 04.00, so reflectance is
      ``(DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE == (DN - 1000) / 10000``
      and dark targets can legitimately go slightly negative. The equivalent
      GDAL scale/offset (1e-4 / -0.1) is also attached to every band, the way
      the L2A cloud-optimised mirrors encode it, so readers that honour
      scale/offset (rioxarray with ``mask_and_scale=True``, say) get
      reflectance directly. Apply one convention or the other, not both;
    * EPSG:32633 (WGS 84 / UTM zone 33N), 10 m square pixels, north up,
      pixel-as-area, on the Sentinel-2 tile grid: the window sits inside the
      100 km square of MGRS tile 33TVK;
    * product metadata under the same tag names GDAL's SENTINEL2 driver
      exposes (PROCESSING_BASELINE, BOA_ADD_OFFSET, SPECIAL_VALUE_NODATA, ...).

    The scene is deterministic for a given ``size``: a coastline with sea to
    the south-east, vegetation, bare karst, a small built-up block, and a
    nodata wedge in the north-west corner like the fill along a granule's
    swath edge. Per-class reflectances are physically plausible, so indices
    come out with the right sign and magnitude -- NDVI about 0.84 over
    vegetation and -0.40 over water, NDWI positive over water only.

    Deliberately not modelled: clouds and cirrus, saturated pixels, the 20 m
    and 60 m bands, the SCL/AOT/WVP layers, and the SAFE directory tree. This
    is a single GeoTIFF, not a product bundle.

    Parameters
    ----------
    path : str or os.PathLike
        Destination file; an existing file is overwritten. The parent
        directory must exist.
    size : int, optional
        Width and height in pixels (default 32), i.e. a ``size * 10`` m square.

    Returns
    -------
    None
    """
    size = int(size)
    if size < 1:
        raise ValueError("size must be a positive integer, got %r" % (size,))

    rho = _reflectance(size, np.random.default_rng(_SEED))

    # Reflectance -> baseline 04.00 digital numbers, keeping the special
    # values free so 0 means "no data" and nothing else.
    dn = np.rint(rho * BOA_QUANTIFICATION_VALUE - BOA_ADD_OFFSET)
    dn = np.clip(dn, NODATA + 1, SATURATED - 1).astype("uint16")

    row, col = np.indices((size, size))
    dn[:, (row + col) < max(1, size // 8)] = NODATA

    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(BANDS),
        "dtype": "uint16",
        "crs": CRS.from_epsg(EPSG),
        "transform": from_origin(ORIGIN[0], ORIGIN[1], PIXEL_SIZE, PIXEL_SIZE),
        "nodata": NODATA,
        "compress": "deflate",
        "predictor": 2,
        "photometric": "minisblack",  # four bands, none of them an alpha band
    }

    with rasterio.open(os.fspath(path), "w", **profile) as dst:
        dst.scales = tuple(1.0 / BOA_QUANTIFICATION_VALUE for _ in BANDS)
        dst.offsets = tuple(
            BOA_ADD_OFFSET / BOA_QUANTIFICATION_VALUE for _ in BANDS
        )
        dst.update_tags(**_DATASET_TAGS)
        for idx, band in enumerate(BANDS, start=1):
            common_name, wavelength, bandwidth = _BAND_META[band]
            dst.set_band_description(idx, band)
            dst.update_tags(
                idx,
                BAND_ID=band,
                COMMON_NAME=common_name,
                CENTRAL_WAVELENGTH_NM=wavelength,
                BANDWIDTH_NM=bandwidth,
                SPATIAL_RESOLUTION_M=str(int(PIXEL_SIZE)),
                BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            )
        dst.write(dn)
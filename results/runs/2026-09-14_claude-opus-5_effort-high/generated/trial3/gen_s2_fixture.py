"""Synthetic Sentinel-2 L2A fixture.

Writes a tiny GeoTIFF that behaves like a real Sentinel-2 Level-2A granule
under processing baseline 04.00, so that code written against genuine L2A
data can be exercised without downloading a 1 GB SAFE archive.

Faithfulness notes (the things that usually break test fixtures):

* Pixel values are **raw DNs**, ``uint16``, exactly as stored in the JP2
  imagery of a real product -- not reflectance floats.  Under baseline 04.00
  a ``BOA_ADD_OFFSET`` of -1000 is in force, so surface reflectance is
  ``(DN + BOA_ADD_OFFSET) / QUANTIFICATION_VALUE == (DN - 1000) / 10000``.
  Reader code that forgets the offset will be off by 0.1 reflectance here,
  the same way it would be off on a genuine baseline-04.00 granule.
  The offset and quantification value are also exposed as GDAL band
  scale/offset and as dataset metadata tags, mirroring what GDAL's SENTINEL2
  driver reports.
* DN 0 means *no data* (declared via the GeoTIFF nodata tag), and the fixture
  contains a small no-data wedge in the upper-left corner, like the swath
  edge of a real granule.  Statistics computed without masking will be wrong.
* Georeferencing is a real 10 m UTM grid (EPSG:32633, MGRS tile 33UUP origin),
  north-up, square pixels, so reprojection and pixel-area maths give sensible
  answers.
* Band order is B02, B03, B04, B08 (blue, green, red, NIR), each carrying a
  band description and central-wavelength metadata.  Colour interpretation is
  left undefined on every band so that band 4 is never mistaken for an alpha
  channel.
* The scene contains water, vegetation, bare soil and built-up patches with
  plausible reflectance, so NDVI/NDWI come out with the expected signs and
  magnitudes.  Content is deterministic for a given ``size``.
"""

from __future__ import annotations

import os

import numpy as np
import rasterio
from rasterio.enums import ColorInterp
from rasterio.transform import from_origin

__all__ = ["s2_fixture"]

# --- product constants (baseline 04.00, S2A) ---------------------------------
BAND_NAMES = ("B02", "B03", "B04", "B08")
BAND_WAVELENGTHS_NM = (492.4, 559.8, 664.6, 832.8)
BAND_RESOLUTION_M = 10.0
QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000
PROCESSING_BASELINE = "04.00"
NODATA = 0
SATURATED = 65535
SENSING_TIME = "2022-06-15T10:20:19.024Z"
MGRS_TILE = "33UUP"
EPSG = 32633
# Upper-left corner of MGRS tile 33UUP, on the 10 m grid.
ORIGIN_X = 399960.0
ORIGIN_Y = 5300040.0

# Mean boundary-of-atmosphere reflectance per class, ordered as BAND_NAMES.
_WATER, _VEGETATION, _SOIL, _BUILTUP = range(4)
_CLASS_REFLECTANCE = np.array(
    [
        [0.045, 0.035, 0.022, 0.008],  # water
        [0.030, 0.055, 0.028, 0.330],  # vegetation
        [0.115, 0.150, 0.195, 0.265],  # bare soil
        [0.140, 0.155, 0.170, 0.200],  # built-up
    ],
    dtype=np.float64,
)
_NOISE_SIGMA = 0.004
_SEED = 20220615


def _classify(size):
    """Return a (size, size) map of land-cover class indices."""
    rows, cols = np.mgrid[0:size, 0:size]
    # Normalised pixel-centre coordinates in [0, 1).
    x = (cols + 0.5) / size
    y = (rows + 0.5) / size

    cover = np.full((size, size), _SOIL, dtype=np.uint8)
    # Vegetated northern two-thirds, with a wavy boundary against the soil.
    cover[y < 0.60 + 0.06 * np.sin(2.0 * np.pi * x)] = _VEGETATION
    # A lake in the south-west.
    lake = ((x - 0.28) / 0.22) ** 2 + ((y - 0.76) / 0.15) ** 2 < 1.0
    cover[lake] = _WATER
    # A built-up block in the south-east.
    cover[(x > 0.70) & (x < 0.92) & (y > 0.66) & (y < 0.88)] = _BUILTUP
    return cover


def _nodata_mask(size):
    """Swath-edge wedge in the upper-left corner, as on a real granule."""
    rows, cols = np.mgrid[0:size, 0:size]
    return (rows + cols) < max(size // 8, 0)


def _digital_numbers(size):
    """Build the (4, size, size) uint16 DN cube."""
    rng = np.random.default_rng(_SEED)
    cover = _classify(size)

    # (4, size, size) of class mean reflectance.
    reflectance = np.moveaxis(_CLASS_REFLECTANCE[cover], -1, 0)
    # Gentle across-track illumination gradient, then sensor noise.
    gradient = np.linspace(0.96, 1.04, size, dtype=np.float64)[np.newaxis, :]
    reflectance = reflectance * gradient
    reflectance += rng.normal(0.0, _NOISE_SIGMA, reflectance.shape)

    dn = np.rint(reflectance * QUANTIFICATION_VALUE - BOA_ADD_OFFSET)
    # DN 0 is reserved for no data; DN 65535 for saturation.
    dn = np.clip(dn, 1, SATURATED - 1)

    dn[:, _nodata_mask(size)] = NODATA
    return dn.astype(np.uint16)


def s2_fixture(path, size=32):
    """Write a synthetic Sentinel-2 L2A product to ``path`` as a GeoTIFF.

    The file has four ``uint16`` bands -- B02, B03, B04, B08 in that order --
    at 10 m resolution, ``size`` by ``size`` pixels, holding raw DNs under
    processing baseline 04.00 (reflectance = ``(DN - 1000) / 10000``, DN 0 is
    no data).  Content is deterministic for a given ``size``.

    Parameters
    ----------
    path : str or os.PathLike
        Destination file.  Missing parent directories are created.
    size : int
        Side length in pixels; must be at least 1.

    Returns
    -------
    None
    """
    size = int(size)
    if size < 1:
        raise ValueError(f"size must be >= 1, got {size}")

    path = os.fspath(path)
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)

    data = _digital_numbers(size)
    transform = from_origin(
        ORIGIN_X, ORIGIN_Y, BAND_RESOLUTION_M, BAND_RESOLUTION_M
    )

    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(BAND_NAMES),
        "dtype": "uint16",
        "crs": rasterio.crs.CRS.from_epsg(EPSG),
        "transform": transform,
        "nodata": NODATA,
        "compress": "deflate",
        "predictor": 2,
        "photometric": "minisblack",
    }

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)
        # Never let band 4 be read as an alpha channel.
        dst.colorinterp = [ColorInterp.undefined] * len(BAND_NAMES)
        # GDAL convention: value = DN * scale + offset -> surface reflectance.
        dst.scales = tuple(1.0 / QUANTIFICATION_VALUE for _ in BAND_NAMES)
        dst.offsets = tuple(
            BOA_ADD_OFFSET / QUANTIFICATION_VALUE for _ in BAND_NAMES
        )
        dst.update_tags(
            AREA_OR_POINT="Area",
            PRODUCT_TYPE="S2MSI2A",
            PROCESSING_LEVEL="Level-2A",
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            SPACECRAFT_NAME="Sentinel-2A",
            MGRS_TILE=MGRS_TILE,
            PRODUCT_START_TIME=SENSING_TIME,
            PRODUCT_STOP_TIME=SENSING_TIME,
            SENSING_TIME=SENSING_TIME,
            QUANTIFICATION_VALUE=str(QUANTIFICATION_VALUE),
            BOA_QUANTIFICATION_VALUE=str(QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            SPECIAL_VALUE_NODATA=str(NODATA),
            SPECIAL_VALUE_SATURATED=str(SATURATED),
            CLOUD_COVERAGE_ASSESSMENT="0.0",
        )
        for index, (name, wavelength) in enumerate(
            zip(BAND_NAMES, BAND_WAVELENGTHS_NM), start=1
        ):
            dst.set_band_description(index, name)
            dst.update_tags(
                index,
                BANDNAME=name,
                CENTRAL_WAVELENGTH_NM=f"{wavelength:.1f}",
                SPATIAL_RESOLUTION_M=f"{BAND_RESOLUTION_M:.0f}",
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
                QUANTIFICATION_VALUE=str(QUANTIFICATION_VALUE),
            )

    return None
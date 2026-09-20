```python
"""Synthetic Sentinel-2 L2A granule for use as a unit-test fixture.

The file written by :func:`s2_fixture` is a miniature stand-in for the 10 m
bands of a real Level-2A product generated under **processing baseline 04.00**
(anything sensed after 2022-01-25).  The pixel values are therefore *not*
reflectance: they are unsigned 16-bit digital numbers that must be decoded with
the radiometric offset that baseline introduced::

    sr = (dn + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE
       = (dn - 1000) / 10000

Reader code that forgets the offset gets plausible-looking but wrong answers
(e.g. NDVI over the vegetated half comes out near 0.52 instead of 0.80), and
dark-water pixels — which legitimately carry slightly negative surface
reflectance after atmospheric correction — encode as DN just below 1000.  The
fixture is built so those mistakes are visible.

Other properties of a genuine granule that are reproduced here: UTM/WGS84 CRS
on the MGRS tile grid with a 10 m pixel and a tile-aligned origin, band order
B2/B3/B4/B8 with per-band descriptions and wavelengths, DN 0 reserved as the
NODATA special value (present as a cut corner, as on a real swath edge), and
the product-level metadata needed to decode the radiometry.
"""

from __future__ import annotations

import operator
import os

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

__all__ = ["s2_fixture"]

# --- Product constants (baseline 04.00, 10 m bands) -------------------------

_BAND_NAMES = ("B02", "B03", "B04", "B08")
_PHYSICAL_BANDS = ("B2", "B3", "B4", "B8")
_BAND_INDICES = (1, 2, 3, 7)  # position in the full 13-band S2 band list
_WAVELENGTHS_NM = (492.4, 559.8, 664.6, 832.8)  # S2A central wavelengths
_BANDWIDTHS_NM = (66.0, 36.0, 31.0, 106.0)

_QUANTIFICATION_VALUE = 10000
_BOA_ADD_OFFSET = -1000  # introduced by processing baseline 04.00
_NODATA = 0
_SATURATED = 65535

_EPSG = 32631  # UTM zone 31N
_MGRS_TILE = "T31TCJ"
_TILE_ORIGIN = (300000.0, 4900020.0)  # NW corner of the tile, metres
_PIXEL_SIZE = 10.0

_PRODUCT_TAGS = {
    "PRODUCT_URI": (
        "S2A_MSIL2A_20220615T104631_N0400_R051_T31TCJ_20220615T170214.SAFE"
    ),
    "PRODUCT_TYPE": "S2MSI2A",
    "PROCESSING_LEVEL": "Level-2A",
    "PROCESSING_BASELINE": "04.00",
    "SPACECRAFT_NAME": "Sentinel-2A",
    "MGRS_TILE": _MGRS_TILE,
    "SENSING_ORBIT_NUMBER": "51",
    "PRODUCT_START_TIME": "2022-06-15T10:46:31.024Z",
    "PRODUCT_STOP_TIME": "2022-06-15T10:46:31.024Z",
    "GENERATION_TIME": "2022-06-15T17:02:14.000Z",
    "TIFFTAG_DATETIME": "2022:06:15 10:46:31",
    "SPATIAL_RESOLUTION": "10",
    "BOA_QUANTIFICATION_VALUE": str(_QUANTIFICATION_VALUE),
    "BOA_ADD_OFFSET": str(_BOA_ADD_OFFSET),
    "REFLECTANCE_CONVERSION_U": "0.9689905",
    "SPECIAL_VALUE_NODATA": str(_NODATA),
    "SPECIAL_VALUE_SATURATED": str(_SATURATED),
    "RADIOMETRY_HINT": "sr = (dn + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE",
}

# --- Scene definition -------------------------------------------------------

# Mean BOA reflectance per land-cover class, in band order B2, B3, B4, B8.
_SOIL, _VEGETATION, _WATER, _BUILT, _CLOUD = range(5)
_CLASS_MEANS = np.array(
    [
        [0.1084, 0.1446, 0.1958, 0.2673],  # bare soil      NDVI ~ 0.15
        [0.0308, 0.0576, 0.0374, 0.3521],  # vegetation     NDVI ~ 0.81
        [0.0452, 0.0331, 0.0208, 0.0024],  # water          NDVI ~ -0.79
        [0.1421, 0.1563, 0.1719, 0.2045],  # built-up       NDVI ~ 0.09
        [0.8412, 0.8367, 0.8298, 0.7934],  # opaque cloud
    ],
    dtype=np.float64,
)

_SEED = 20220615  # fixed: the fixture must be byte-for-byte reproducible


def _dn_cube(size):
    """Return the band-first ``(4, size, size)`` uint16 DN array for the scene."""
    rng = np.random.default_rng(_SEED)

    # Normalised pixel centres, so the layout is the same at any `size`.
    yy, xx = (np.mgrid[0:size, 0:size] + 0.5) / size

    label = np.full((size, size), _SOIL, dtype=np.intp)
    label[xx < 0.5] = _VEGETATION
    label[(xx - 0.27) ** 2 + (yy - 0.72) ** 2 < 0.17**2] = _WATER
    label[(xx > 0.66) & (yy > 0.58)] = _BUILT
    label[(xx - 0.78) ** 2 + (yy - 0.22) ** 2 < 0.13**2] = _CLOUD

    mean = _CLASS_MEANS[label]  # (size, size, 4)
    # Noise floor is deliberately coarse enough that the darkest water pixels
    # land on negative surface reflectance, exactly as they do in real L2A.
    sd = 0.05 * mean + 0.003
    sr = mean + sd * rng.standard_normal(mean.shape)
    sr *= (0.97 + 0.06 * xx)[..., None]  # gentle across-track illumination ramp

    dn = np.rint(sr * _QUANTIFICATION_VALUE - _BOA_ADD_OFFSET)
    dn = np.clip(dn, 1, _SATURATED).astype(np.uint16)  # 0 is reserved for NODATA
    cube = np.moveaxis(dn, -1, 0)

    # Swath-edge cut: the corner is outside the acquisition footprint.
    cube[:, xx + yy < 0.13] = _NODATA
    return cube


def s2_fixture(path, size=32):
    """Write a synthetic Sentinel-2 L2A GeoTIFF to ``path``.

    The product holds the four 10 m bands in the order B2, B3, B4, B8 as
    uint16 digital numbers at processing baseline 04.00, on a ``size`` x
    ``size`` grid at the NW corner of MGRS tile T31TCJ (EPSG:32631, 10 m
    pixels).  Decode with ``(dn + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE``,
    or equivalently ``dn * scale + offset`` using the per-band scale (1e-4) and
    offset (-0.1) recorded in the file; DN 0 means no data.

    The scene contains vegetation (left half), a lake, bare soil, a built-up
    block, an opaque cloud and a nodata corner, so band ratios, masking and
    georeferencing all have something meaningful to act on.  At sizes below
    roughly 16 pixels some of those regions shrink to nothing.

    Parameters
    ----------
    path : str or os.PathLike
        Destination file.  Overwritten if it exists; its directory must exist.
    size : int, optional
        Side length of the square raster in pixels.  Defaults to 32.

    Returns
    -------
    None
    """
    size = operator.index(size)
    if size < 1:
        raise ValueError(f"size must be a positive integer, got {size!r}")

    cube = _dn_cube(size)

    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(_BAND_NAMES),
        "dtype": "uint16",
        "nodata": _NODATA,
        "crs": CRS.from_epsg(_EPSG),
        "transform": from_origin(*_TILE_ORIGIN, _PIXEL_SIZE, _PIXEL_SIZE),
        "compress": "deflate",
        "predictor": 2,
        "interleave": "pixel",
    }
    if size >= 256:  # tiled like a real granule only once it is worth it
        profile.update(tiled=True, blockxsize=256, blockysize=256)

    with rasterio.open(os.fspath(path), "w", **profile) as dst:
        dst.write(cube)
        dst.update_tags(**_PRODUCT_TAGS)

        # GDAL convention: value = dn * scale + offset, i.e. the baseline 04.00
        # decoding expressed in a form generic readers already understand.
        scale = 1.0 / _QUANTIFICATION_VALUE
        offset = _BOA_ADD_OFFSET / _QUANTIFICATION_VALUE
        dst.scales = (scale,) * len(_BAND_NAMES)
        dst.offsets = (offset,) * len(_BAND_NAMES)

        for i, name in enumerate(_BAND_NAMES):
            bidx = i + 1
            dst.set_band_description(bidx, name)
            dst.update_tags(
                bidx,
                BAND_NAME=name,
                PHYSICAL_BAND=_PHYSICAL_BANDS[i],
                BAND_INDEX=str(_BAND_INDICES[i]),
                WAVELENGTH_NM=f"{_WAVELENGTHS_NM[i]:.1f}",
                BANDWIDTH_NM=f"{_BANDWIDTHS_NM[i]:.1f}",
                BOA_ADD_OFFSET=str(_BOA_ADD_OFFSET),
                BOA_QUANTIFICATION_VALUE=str(_QUANTIFICATION_VALUE),
            )
```
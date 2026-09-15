```python
"""Synthetic Sentinel-2 L2A fixture writer.

Produces a small GeoTIFF that stands in for a real L2A granule: the four 10 m
bands (B2, B3, B4, B8) in that order, as raw uint16 digital numbers carrying the
processing-baseline-04.00 radiometric convention, on a UTM grid with 10 m pixels.

Reflectance recovery from a pixel value DN is the same as for a genuine product:

    reflectance = (DN + BOA_ADD_OFFSET) / QUANTIFICATION_VALUE
                = (DN - 1000) / 10000

which is exactly the affine transform written into each band's scale/offset, so
scale-aware readers get the right answer without special-casing the fixture.
Zero is the nodata value, as in the real product.
"""

from __future__ import annotations

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

#: Band names, in the order they are written to the file.
BANDS = ("B2", "B3", "B4", "B8")

#: Central wavelengths in nm, for band descriptions.
_WAVELENGTHS_NM = {"B2": 490, "B3": 560, "B4": 665, "B8": 842}

PROCESSING_BASELINE = "04.00"
QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000  # baseline 04.00 and later
NODATA = 0

#: Ground sampling distance in metres for the bands written here.
GSD = 10.0

#: A real granule origin: UTM 32N (EPSG:32632), tile 32TNS-ish, on the 10 m grid.
_EPSG = 32632
_ORIGIN_X = 399960.0
_ORIGIN_Y = 5300040.0

#: Plausible boundary-of-atmosphere reflectances for a vegetated scene, used as
#: the mean level of each band before spatial structure is added.
_BASE_REFLECTANCE = {"B2": 0.04, "B3": 0.07, "B4": 0.05, "B8": 0.30}


def _band_reflectance(name: str, size: int) -> np.ndarray:
    """Synthetic surface reflectance for one band, shape (size, size), float64.

    A smooth gradient plus a brighter square gives every band some spatial
    structure and a non-degenerate histogram, while keeping values in the
    physical 0..1 range that L2A reflectance occupies.
    """
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    denom = max(size - 1, 1)
    gradient = (xx + yy) / (2.0 * denom)  # 0..1 across the diagonal

    base = _BASE_REFLECTANCE[name]
    refl = base * (0.75 + 0.5 * gradient)

    # A bright patch in the middle quarter of the scene.
    lo, hi = size // 4, max(size // 4 + 1, (3 * size) // 4)
    refl[lo:hi, lo:hi] += 0.5 * base

    return np.clip(refl, 0.0, 1.0)


def _to_dn(reflectance: np.ndarray) -> np.ndarray:
    """Encode reflectance as baseline 04.00 digital numbers (uint16)."""
    dn = np.rint(reflectance * QUANTIFICATION_VALUE - BOA_ADD_OFFSET)
    # Keep NODATA free: a real product never emits 0 for a valid pixel.
    dn = np.clip(dn, 1, np.iinfo(np.uint16).max)
    return dn.astype(np.uint16)


def s2_fixture(path, size=32):
    """Write a synthetic Sentinel-2 L2A product to ``path`` as a GeoTIFF.

    The file has four uint16 bands -- B2, B3, B4, B8, in that order -- at 10 m
    resolution on a UTM grid, ``size`` pixels square, using the processing
    baseline 04.00 radiometric offset.

    Parameters
    ----------
    path : str or os.PathLike
        Destination file path.
    size : int
        Side length of the (square) raster in pixels. Must be positive.

    Returns
    -------
    None
    """
    size = int(size)
    if size <= 0:
        raise ValueError(f"size must be a positive number of pixels, got {size}")

    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(BANDS),
        "dtype": "uint16",
        "crs": CRS.from_epsg(_EPSG),
        "transform": from_origin(_ORIGIN_X, _ORIGIN_Y, GSD, GSD),
        "nodata": NODATA,
        "tiled": False,
        "compress": "deflate",
    }

    scale = 1.0 / QUANTIFICATION_VALUE
    offset = BOA_ADD_OFFSET / QUANTIFICATION_VALUE

    with rasterio.open(path, "w", **profile) as dst:
        for index, name in enumerate(BANDS, start=1):
            dst.write(_to_dn(_band_reflectance(name, size)), index)
            dst.set_band_description(
                index, f"{name} ({_WAVELENGTHS_NM[name]} nm)"
            )
            dst.update_tags(
                index,
                BANDNAME=name,
                WAVELENGTH_NM=str(_WAVELENGTHS_NM[name]),
                GSD=str(int(GSD)),
            )
        # Affine reflectance recovery, applied by scale-aware readers.
        dst.scales = (scale,) * len(BANDS)
        dst.offsets = (offset,) * len(BANDS)
        dst.update_tags(
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            PRODUCT_TYPE="S2MSI2A",
            QUANTIFICATION_VALUE=str(QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            BOA_QUANTIFICATION_VALUE=str(QUANTIFICATION_VALUE),
        )

    return None
```
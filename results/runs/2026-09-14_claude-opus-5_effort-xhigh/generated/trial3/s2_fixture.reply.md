Key decisions: DNs carry the baseline‑04.00 `BOA_ADD_OFFSET = -1000` (so reflectance is `(DN - 1000)/10000`, and pre‑04.00 reader code reads ~0.1 too high here, exactly as on a real granule); uint16 with `nodata=0` including a real granule‑edge nodata corner; UTM/10 m grid geometry, band descriptions and SAFE‑style metadata tags so band identification and reflectance conversion work the same way as on a genuine product.

```python
"""A small synthetic Sentinel-2 L2A product, for use as a unit-test fixture.

The file written by :func:`s2_fixture` is meant to be a faithful stand-in for a
real L2A granule rather than merely a georeferenced array: same dtype and DN
scaling, same nodata convention, same band order and naming, same style of
georeferencing, and the processing-baseline-04.00 radiometric offset.  Code
that reads a genuine product should read this one without special-casing, and
get the same kind of answer.

Importing this module has no side effects.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

__all__ = ["s2_fixture"]


# --- Product characteristics -------------------------------------------------

#: The four 10 m bands, in the order they are written.
BANDS = ("B2", "B3", "B4", "B8")

#: S2A central wavelengths, nm (blue, green, red, NIR).
_CENTRAL_WAVELENGTH_NM = {"B2": 492.4, "B3": 559.8, "B4": 664.6, "B8": 832.8}

_PIXEL_SIZE_M = 10.0
_EPSG = 32631  # WGS 84 / UTM zone 31N
_MGRS_TILE = "T31UDQ"
# Upper-left corner of the tile: on the 10 m grid, offset from the 100 km MGRS
# square the way real granule origins are (tiles are 109 800 m and overlap).
_ULX, _ULY = 399960.0, 5600040.0

# Radiometry.  From processing baseline 04.00 (products sensed on or after
# 2022-01-25) L2A DNs carry an additive offset, so the conversion is
#
#     BOA reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE
#
# Reader code that predates 04.00 omits the offset and therefore reads this
# fixture ~0.1 reflectance too high -- exactly as it does on a real granule.
_QUANTIFICATION_VALUE = 10000
_BOA_ADD_OFFSET = -1000
_NODATA = 0
_SATURATED = 65535

_SENSING_TIME = "2022-06-13T10:46:19.024Z"
_GENERATION_TIME = "2022-06-13T13:41:27.000Z"
_PRODUCT_URI = (
    "S2A_MSIL2A_20220613T104619_N0400_R051_T31UDQ_20220613T134127.SAFE"
)

_PRODUCT_TAGS = {
    "PRODUCT_TYPE": "S2MSI2A",
    "PROCESSING_LEVEL": "Level-2A",
    "PROCESSING_BASELINE": "04.00",
    "SPACECRAFT_NAME": "Sentinel-2A",
    "PRODUCT_URI": _PRODUCT_URI,
    "MGRS_TILE": _MGRS_TILE,
    "SENSING_TIME": _SENSING_TIME,
    "GENERATION_TIME": _GENERATION_TIME,
    "CLOUD_COVERAGE_ASSESSMENT": "0.0",
    "BOA_QUANTIFICATION_VALUE": str(_QUANTIFICATION_VALUE),
    "QUANTIFICATION_VALUE": str(_QUANTIFICATION_VALUE),
    "BOA_ADD_OFFSET": str(_BOA_ADD_OFFSET),
    "NODATA_VALUE": str(_NODATA),
    "SATURATED_VALUE": str(_SATURATED),
    "REFLECTANCE_CONVERSION": (
        "reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE"
    ),
    # Be explicit that this is not real data, so a stray copy of the file
    # cannot be mistaken for a downloaded granule.
    "SYNTHETIC_FIXTURE": "true",
}

# Plausible L2A BOA reflectances per cover type, in BANDS order.  Chosen so the
# usual indices land where a test would expect them: NDVI ~ 0.8 over
# vegetation, negative over water; NDWI positive over water only.
_ENDMEMBERS = {
    "vegetation": (0.030, 0.060, 0.035, 0.360),
    "water": (0.055, 0.045, 0.028, 0.012),
    "bare_soil": (0.105, 0.135, 0.185, 0.265),
    "built_up": (0.125, 0.140, 0.155, 0.200),
}

_SEED = 20220613


def _reflectance_scene(size: int, rng: np.random.Generator) -> np.ndarray:
    """Return a (4, size, size) float32 stack of BOA reflectance."""
    rows, cols = np.mgrid[0:size, 0:size]
    y = (rows + 0.5) / size
    x = (cols + 0.5) / size

    refl = np.empty((len(BANDS), size, size), dtype="float32")
    refl[:] = np.asarray(_ENDMEMBERS["vegetation"], dtype="float32")[:, None, None]

    def paint(mask: np.ndarray, cover: str) -> None:
        values = np.asarray(_ENDMEMBERS[cover], dtype="float32")[:, None, None]
        np.copyto(refl, values, where=mask[None, :, :])

    paint(x > 0.62, "bare_soil")
    paint((x > 0.70) & (y < 0.26), "built_up")
    paint(((x - 0.30) ** 2 + (y - 0.68) ** 2) < 0.19**2, "water")

    # Gentle across-track brightness gradient plus sensor noise, so that
    # per-band statistics are not degenerate.
    refl *= (0.97 + 0.06 * x).astype("float32")
    refl += rng.normal(0.0, 0.004, size=refl.shape).astype("float32")
    return np.clip(refl, 0.0, 1.6, out=refl)


def s2_fixture(path, size: int = 32) -> None:
    """Write a synthetic Sentinel-2 L2A product to ``path`` as a GeoTIFF.

    The product holds the four 10 m bands B2, B3, B4 and B8 in that order, as
    uint16 DNs at processing baseline 04.00, on a ``size`` x ``size`` grid of
    10 m pixels in WGS 84 / UTM zone 31N.  Reflectance is recovered the same
    way as for a real granule::

        reflectance = (DN - 1000) / 10000

    Bands are identified by their GeoTIFF band descriptions (``B2`` ...) and by
    per-band ``BANDNAME`` tags; the conversion constants are also written as
    GDAL scale/offset, so readers that apply those get reflectance directly.

    Pixels with DN 0 are nodata (declared on the dataset), and a triangular
    patch in the north-west corner is left as nodata to mimic the empty edge of
    a real granule.  Note that nodata pixels convert to -0.1 reflectance if the
    offset is applied blindly, exactly as on a real product -- mask first.

    Parameters
    ----------
    path:
        Destination file; parent directories are created if needed.
    size:
        Width and height of the raster in pixels. Defaults to 32.

    Returns
    -------
    None
    """
    size = int(size)
    if size < 1:
        raise ValueError(f"size must be a positive number of pixels, got {size!r}")

    destination = Path(os.fspath(path))
    destination.parent.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(_SEED)
    reflectance = _reflectance_scene(size, rng)

    # Encode as baseline-04.00 DNs, keeping valid data clear of the nodata
    # value, then blank the granule-edge corner.
    dn = np.rint(reflectance * _QUANTIFICATION_VALUE) - _BOA_ADD_OFFSET
    dn = np.clip(dn, 1, _SATURATED).astype("uint16")

    rows, cols = np.mgrid[0:size, 0:size]
    edge = ((rows + 0.5) / size + (cols + 0.5) / size) < 0.25
    dn[:, edge] = _NODATA

    blocksize = 256 if size >= 256 else 16
    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(BANDS),
        "dtype": "uint16",
        "nodata": _NODATA,
        "crs": CRS.from_epsg(_EPSG),
        "transform": from_origin(_ULX, _ULY, _PIXEL_SIZE_M, _PIXEL_SIZE_M),
        "tiled": True,
        "blockxsize": blocksize,
        "blockysize": blocksize,
        "interleave": "band",
        "compress": "deflate",
        "predictor": 2,
    }

    with rasterio.open(destination, "w", **profile) as dst:
        dst.write(dn)
        dst.update_tags(**_PRODUCT_TAGS)
        dst.scales = [1.0 / _QUANTIFICATION_VALUE] * len(BANDS)
        dst.offsets = [_BOA_ADD_OFFSET / _QUANTIFICATION_VALUE] * len(BANDS)
        for index, band in enumerate(BANDS, start=1):
            dst.set_band_description(index, band)
            dst.update_tags(
                index,
                BANDNAME=band,
                CENTRAL_WAVELENGTH_NM=str(_CENTRAL_WAVELENGTH_NM[band]),
                SPATIAL_RESOLUTION_M="10",
                BOA_QUANTIFICATION_VALUE=str(_QUANTIFICATION_VALUE),
                BOA_ADD_OFFSET=str(_BOA_ADD_OFFSET),
            )
```
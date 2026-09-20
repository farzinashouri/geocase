```python
"""Write a small synthetic Sentinel-2 L2A product for use as a unit-test fixture.

The file produced by :func:`s2_fixture` is a stand-in for one 10 m granule of a
real ``S2MSI2A`` product at processing baseline 04.00:

* four bands in the fixed order ``B2, B3, B4, B8`` (blue, green, red, NIR),
* ``uint16`` digital numbers on a 10 m UTM grid aligned to a real MGRS tile,
* ``0`` reserved as NODATA, exactly as in a genuine L2A granule,
* the baseline 04.00 radiometric shift baked into the pixel values.

That last point is the one that matters most for faithfulness.  From baseline
04.00 onward, ESA stores bottom-of-atmosphere reflectance with a ``-1000``
offset, so reflectance must be recovered as::

    reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE
                = (DN - 1000) / 10000

The offset lives in the product metadata (``MTD_MSIL2A.xml``) of a real
product, never in a GDAL scale/offset tag, so it is written here as dataset and
band *tags* only.  Code that ignores it gets reflectance that is 0.1 too high --
on this fixture just as on a real granule -- and code that applies it correctly
gets the plausible surface reflectances of the modelled scene.

The scene itself is deterministic: a water body, a bare-soil strip, a built-up
patch and a vegetated background, with a mild illumination gradient and sensor
noise, so band ratios such as NDVI vary meaningfully across the image.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import Affine

__all__ = ["s2_fixture", "BANDS", "BOA_ADD_OFFSET", "BOA_QUANTIFICATION_VALUE"]

#: Band order of the written file (band index 1..4).
BANDS = ("B2", "B3", "B4", "B8")

#: Sentinel-2A central wavelengths, nm.
CENTRAL_WAVELENGTH_NM = {"B2": 492.4, "B3": 559.8, "B4": 664.6, "B8": 832.8}

PROCESSING_BASELINE = "04.00"
BOA_QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000  # baseline >= 04.00
NODATA = 0

PIXEL_SIZE = 10.0
EPSG = 32631  # UTM zone 31N
TILE_ID = "T31TCJ"
TILE_ORIGIN = (399960.0, 4800000.0)  # upper-left corner of the real MGRS tile
SENSING_TIME = datetime(2022, 6, 15, 10, 46, 21, 24000, tzinfo=timezone.utc)

# Endmember BOA reflectance per class, in BANDS order.
_ENDMEMBERS = {
    "water": (0.045, 0.035, 0.024, 0.009),
    "soil": (0.105, 0.140, 0.192, 0.268),
    "built": (0.148, 0.160, 0.172, 0.205),
    "vegetation": (0.031, 0.062, 0.036, 0.322),
}


def _smoothstep(edge0: float, edge1: float, value: np.ndarray) -> np.ndarray:
    """Hermite ramp from 0 at ``edge0`` to 1 at ``edge1`` (either order)."""
    t = np.clip((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _reflectance(size: int) -> np.ndarray:
    """Return a ``(4, size, size)`` float array of BOA reflectance."""
    rng = np.random.default_rng(20220615)
    span = max(size - 1, 1)
    rows, cols = np.mgrid[0:size, 0:size].astype("float64")
    y = rows / span
    x = cols / span

    # Class abundances: a lake, a diagonal soil strip, a built-up block, and
    # vegetation filling whatever is left over.
    w_water = _smoothstep(0.30, 0.16, np.hypot(x - 0.22, y - 0.78))
    w_soil = _smoothstep(0.16, 0.06, np.abs(x + y - 1.15))
    w_built = _smoothstep(0.26, 0.12, np.maximum(np.abs(x - 0.80), np.abs(y - 0.22)))
    w_veg = np.clip(1.0 - w_water - w_soil - w_built, 0.0, 1.0) + 1e-6

    weights = np.stack([w_water, w_soil, w_built, w_veg])
    weights /= weights.sum(axis=0)

    table = np.array([_ENDMEMBERS[name] for name in
                      ("water", "soil", "built", "vegetation")])  # (class, band)
    refl = np.einsum("cyx,cb->byx", weights, table)

    # Mild across-track illumination gradient plus per-pixel sensor noise whose
    # magnitude grows with signal, as on a real granule.
    refl *= 1.0 + 0.06 * (x - y)
    refl += rng.standard_normal(refl.shape) * (0.0015 + 0.02 * refl)

    return np.clip(refl, 0.0005, 1.0)


def _digital_numbers(size: int) -> np.ndarray:
    """Quantise reflectance to baseline 04.00 ``uint16`` DNs."""
    dn = np.rint(_reflectance(size) * BOA_QUANTIFICATION_VALUE - BOA_ADD_OFFSET)
    # 0 means NODATA, so valid data starts at 1; this fixture has no gaps.
    return np.clip(dn, NODATA + 1, np.iinfo("uint16").max).astype("uint16")


def s2_fixture(path, size: int = 32) -> None:
    """Write a synthetic Sentinel-2 L2A GeoTIFF of ``size`` x ``size`` pixels.

    Parameters
    ----------
    path:
        Destination file, as :class:`str`, :class:`bytes` or
        :class:`os.PathLike`.  Any missing parent directories are created.
    size:
        Side length of the square raster in pixels (default 32).

    Returns
    -------
    None
    """
    size = int(size)
    if size < 1:
        raise ValueError(f"size must be a positive number of pixels, got {size!r}")

    path = os.fspath(path)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    data = _digital_numbers(size)
    transform = Affine(PIXEL_SIZE, 0.0, TILE_ORIGIN[0],
                       0.0, -PIXEL_SIZE, TILE_ORIGIN[1])

    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(BANDS),
        "dtype": "uint16",
        "crs": CRS.from_epsg(EPSG),
        "transform": transform,
        "nodata": NODATA,
        "interleave": "pixel",
        "compress": "deflate",
        "predictor": 2,
    }

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)
        dst.descriptions = BANDS
        dst.update_tags(
            AREA_OR_POINT="Area",
            PRODUCT_TYPE="S2MSI2A",
            PROCESSING_LEVEL="Level-2A",
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            SPACECRAFT_NAME="Sentinel-2A",
            TILE_ID=TILE_ID,
            SENSING_TIME=SENSING_TIME.isoformat().replace("+00:00", "Z"),
            BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            SPATIAL_RESOLUTION=str(int(PIXEL_SIZE)),
            NODATA_VALUE=str(NODATA),
            SATURATED_VALUE="65535",
        )
        for index, band in enumerate(BANDS, start=1):
            dst.update_tags(
                index,
                BANDNAME=band,
                CENTRAL_WAVELENGTH_NM=f"{CENTRAL_WAVELENGTH_NM[band]:.1f}",
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
                BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            )

    return None
```
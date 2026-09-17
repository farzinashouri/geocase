"""Synthetic Sentinel-2 Level-2A fixture for unit tests.

``s2_fixture`` writes a tiny, deterministic GeoTIFF that stands in for the
four 10 m bands (B02, B03, B04, B08) of a Sentinel-2 L2A granule produced
at processing baseline 04.00.

The pixel encoding is the one a real baseline >= 04.00 product uses, so a
reader that decodes genuine L2A data will decode this file the same way:

    dtype                     uint16
    nodata                    0
    BOA_QUANTIFICATION_VALUE  10000
    BOA_ADD_OFFSET            -1000        (introduced in baseline 04.00)
    surface reflectance       (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE
                              == (DN - 1000) / 10000

So reflectance 0.0 is stored as DN 1000 (not 0), reflectance 0.25 as DN
3500, and the slightly negative reflectances that real products contain
(e.g. water in B08) are stored as DN in [1, 1000).  Dividing DN by 10000
without applying the offset -- the pre-04.00 convention -- yields values
that are 0.1 too high, which is exactly the mistake this fixture exists
to catch.

The same relationship is exposed through GDAL per-band scale/offset
(scale=1e-4, offset=-0.1) and through dataset/band tags mirroring the
fields of ``MTD_MSIL2A.xml``.  The raster is georeferenced as the
upper-left ``size`` x ``size`` window of tile T31TCJ (EPSG:32631, 10 m).
"""

from __future__ import annotations

import os

import numpy as np
import rasterio
from rasterio.transform import from_origin

__all__ = ["s2_fixture"]

# Product / encoding constants (Sentinel-2 L2A, processing baseline >= 04.00).
PROCESSING_BASELINE = "04.00"
BOA_QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000
NODATA = 0
DTYPE = "uint16"

# Band layout in file order: (name, MTD_MSIL2A band_id, S2A central wavelength nm).
BANDS = (
    ("B02", 1, 492.4),
    ("B03", 2, 559.8),
    ("B04", 3, 664.6),
    ("B08", 7, 832.8),
)

# Georeferencing: upper-left corner of tile T31TCJ, 10 m pixels.
CRS = "EPSG:32631"
TILE_ID = "T31TCJ"
TILE_ULX = 300000.0
TILE_ULY = 4900020.0
PIXEL_SIZE = 10.0

_SEED = 20220125  # the date processing baseline 04.00 became operational

# Typical BOA reflectance per land-cover class, in (B02, B03, B04, B08) order.
_CLASS_REFLECTANCE = np.array(
    [
        [0.030, 0.060, 0.040, 0.400],  # 0: healthy vegetation
        [0.100, 0.140, 0.200, 0.300],  # 1: bare soil
        [0.050, 0.040, 0.020, 0.002],  # 2: clear water (B08 straddles zero)
    ],
    dtype=np.float64,
)


def _surface_reflectance(size, rng):
    """Return ``(rho, valid)``.

    ``rho`` is a float64 ``(4, size, size)`` array of surface reflectance.
    ``valid`` is a bool ``(size, size)`` array that is False in a small
    triangle at the upper-left corner, mimicking the no-data wedge found at
    the edge of a swath.  Small rasters (size < 4) are fully valid.
    """
    rows, cols = np.indices((size, size))
    v = (rows + 0.5) / size  # fractional row position, top -> bottom
    u = (cols + 0.5) / size  # fractional column position, left -> right

    cls = np.zeros((size, size), dtype=np.intp)  # vegetation everywhere...
    cls[v > 0.65] = 1  # ...a bare-soil strip along the bottom...
    cls[(u - 0.65) ** 2 + (v - 0.35) ** 2 < 0.04] = 2  # ...and a lake.

    rho = np.moveaxis(_CLASS_REFLECTANCE[cls], -1, 0)  # (4, size, size)
    rho = rho * (1.0 + 0.10 * (u - 0.5))  # gentle illumination gradient
    rho = rho * rng.normal(1.0, 0.05, size=rho.shape)  # per-pixel texture
    rho = rho + rng.normal(0.0, 0.002, size=rho.shape)  # residual noise

    valid = (rows + cols) >= size // 4
    return rho, valid


def _encode(rho, valid):
    """Convert surface reflectance to L2A digital numbers (uint16, 0 = nodata).

    DN = rho * BOA_QUANTIFICATION_VALUE - BOA_ADD_OFFSET, clipped to
    [1, 65535] so that no valid pixel collides with the nodata value.
    """
    dn = np.rint(rho * BOA_QUANTIFICATION_VALUE - BOA_ADD_OFFSET)
    dn = np.clip(dn, 1, np.iinfo(np.uint16).max).astype(np.uint16)
    dn[:, ~valid] = NODATA
    return dn


def s2_fixture(path, size=32):
    """Write a synthetic Sentinel-2 L2A (baseline 04.00) GeoTIFF to ``path``.

    Parameters
    ----------
    path : str or os.PathLike
        Destination file.  Any existing file is overwritten.
    size : int, default 32
        Edge length in pixels; the raster is ``size`` x ``size``.

    The file has four uint16 bands in the order B02, B03, B04, B08 with
    nodata 0, and encodes surface reflectance as
    ``(DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE`` == ``(DN - 1000) / 10000``.
    Equivalent GDAL scale/offset values and MTD-style tags are stored as
    well.  Output is deterministic for a given ``size``.

    Returns
    -------
    None
    """
    if isinstance(size, bool) or not isinstance(size, (int, np.integer)) or size < 1:
        raise ValueError(f"size must be a positive integer, got {size!r}")
    size = int(size)

    rng = np.random.default_rng(_SEED)
    rho, valid = _surface_reflectance(size, rng)
    dn = _encode(rho, valid)

    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(BANDS),
        "dtype": DTYPE,
        "crs": CRS,
        "transform": from_origin(TILE_ULX, TILE_ULY, PIXEL_SIZE, PIXEL_SIZE),
        "nodata": NODATA,
        "compress": "deflate",
    }

    with rasterio.open(os.fspath(path), "w", **profile) as dst:
        dst.write(dn)
        dst.descriptions = tuple(name for name, _, _ in BANDS)
        # GDAL convention: physical = DN * scale + offset  ->  (DN - 1000) / 10000
        dst.scales = (1.0 / BOA_QUANTIFICATION_VALUE,) * len(BANDS)
        dst.offsets = (BOA_ADD_OFFSET / BOA_QUANTIFICATION_VALUE,) * len(BANDS)
        dst.update_tags(
            PRODUCT_TYPE="S2MSI2A",
            PROCESSING_LEVEL="Level-2A",
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            SPACECRAFT_NAME="Sentinel-2A",
            TILE_ID=TILE_ID,
            DATATAKE_SENSING_START="2022-03-10T10:56:21.024Z",
            GENERATION_TIME="2022-03-10T14:02:37.000Z",
            BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            NODATA_VALUE=str(NODATA),
            REFLECTANCE_FORMULA="(DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE",
        )
        for bidx, (name, band_id, wavelength) in enumerate(BANDS, start=1):
            dst.update_tags(
                bidx,
                BAND_NAME=name,
                BAND_ID=str(band_id),
                RESOLUTION="10",
                CENTRAL_WAVELENGTH_NM=str(wavelength),
                BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            )
    return None
"""Synthetic Sentinel-2 Level-2A product for use as a unit-test fixture.

The module writes a four-band GeoTIFF (B2, B3, B4, B8 -- the 10 m bands, in
that order) that stands in for a real L2A granule processed with baseline
04.00.  The properties that matter to reader code are reproduced faithfully:

* uint16 DNs on a 10 m UTM grid aligned to a real MGRS tile origin,
* 0 reserved as NODATA (declared on every band),
* the baseline 04.00 radiometric offset, so that

      reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE
                  = (DN - 1000) / 10000

  which is also exposed through the GDAL band scale/offset
  (``value = DN * 0.0001 + (-0.1)``) and through ``BOA_ADD_OFFSET`` /
  ``BOA_QUANTIFICATION_VALUE`` dataset tags mirroring ``MTD_MSIL2A.xml``,
* a scene whose spectra are physically plausible (vegetation with high NIR,
  bare soil, and a water body whose NIR reflectance dips slightly negative,
  as atmospheric correction routinely produces over dark targets).

Importing this module has no side effects; all work happens in ``s2_fixture``.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

__all__ = ["s2_fixture"]

# --- Product constants (baseline 04.00 L2A, as recorded in MTD_MSIL2A.xml) ---

BANDS = ("B2", "B3", "B4", "B8")

# bandId as used in the product metadata (0=B1, 1=B2, ... 7=B8, 8=B8A, ...)
BAND_IDS = {"B2": 1, "B3": 2, "B4": 3, "B8": 7}
CENTRAL_WAVELENGTHS_NM = {"B2": 492.4, "B3": 559.8, "B4": 664.6, "B8": 832.8}
BANDWIDTHS_NM = {"B2": 66.0, "B3": 36.0, "B4": 31.0, "B8": 106.0}

RESOLUTION_M = 10.0
PROCESSING_BASELINE = "04.00"
BOA_QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000  # applies to every band from baseline 04.00 onwards
NODATA = 0
SATURATED = 65535

# The fixture is the top-left corner of MGRS tile T31UDQ (UTM zone 31N), so the
# grid falls exactly where a real granule's grid falls.
EPSG = 32631
MGRS_TILE = "T31UDQ"
ORIGIN_X = 499980.0
ORIGIN_Y = 5600040.0

SENSING_TIME = "2022-06-15T10:36:19.024Z"
PRODUCT_URI = "S2A_MSIL2A_20220615T103619_N0400_R008_T31UDQ_20220615T134244.SAFE"
GRANULE_ID = "L2A_T31UDQ_A036391_20220615T103621"

# Typical BOA reflectances for the three covers in the synthetic scene.
_SURFACES = {
    "vegetation": {"B2": 0.028, "B3": 0.058, "B4": 0.034, "B8": 0.315},
    "soil": {"B2": 0.095, "B3": 0.130, "B4": 0.180, "B8": 0.245},
    "water": {"B2": 0.042, "B3": 0.030, "B4": 0.018, "B8": 0.004},
}

_SEED = 20220615  # fixed, so the fixture is byte-for-byte reproducible


def _smooth(field: np.ndarray) -> np.ndarray:
    """3x3 box filter with edge replication, so noise is spatially correlated."""
    rows, cols = field.shape
    padded = np.pad(field, 1, mode="edge")
    return (
        sum(
            padded[i : i + rows, j : j + cols]
            for i in range(3)
            for j in range(3)
        )
        / 9.0
    )


def _noise_fields(size: int, count: int, rng: np.random.Generator) -> np.ndarray:
    """`count` independent, unit-variance, spatially correlated noise fields."""
    fields = []
    for _ in range(count):
        field = _smooth(_smooth(rng.standard_normal((size, size))))
        spread = float(field.std())
        fields.append(field / spread if spread > 0 else np.zeros_like(field))
    return np.stack(fields)


def _scene(size: int, rng: np.random.Generator):
    """Return (reflectance stack of shape (4, size, size), nodata mask)."""
    rows, cols = np.mgrid[0:size, 0:size]
    u = (cols + 0.5) / size
    v = (rows + 0.5) / size

    water = (u - 0.68) ** 2 + (v - 0.62) ** 2 < 0.19**2
    soil = (v > 0.45 + 0.08 * np.sin(2 * np.pi * u)) & ~water
    # Granules are clipped to the swath, so a corner of the tile is empty.
    nodata = (u + v) < 0.22

    base = np.empty((len(BANDS), size, size), dtype=np.float64)
    for i, band in enumerate(BANDS):
        layer = np.full((size, size), _SURFACES["vegetation"][band])
        layer[soil] = _SURFACES["soil"][band]
        layer[water] = _SURFACES["water"][band]
        base[i] = layer

    # Mild illumination gradient (topography/BRDF) plus per-band texture, and a
    # small additive term standing in for atmospheric-correction residuals --
    # that is what pushes dark water slightly below zero in the NIR.
    illumination = 0.95 + 0.10 * (1.0 - v)
    noise = _noise_fields(size, len(BANDS), rng)
    reflectance = base * illumination * (1.0 + 0.08 * noise) + 0.005 * noise

    return reflectance, nodata


def s2_fixture(path, size: int = 32) -> None:
    """Write a synthetic Sentinel-2 L2A GeoTIFF to `path`.

    The file holds `size` x `size` uint16 pixels for bands B2, B3, B4 and B8
    (in that order) on a 10 m UTM zone 31N grid, with 0 as nodata and the
    processing baseline 04.00 radiometric offset applied, so reflectance is
    recovered as ``(DN - 1000) / 10000``.  Content is deterministic.
    """
    if isinstance(size, (int, np.integer)) is False or size < 1:
        raise ValueError(f"size must be a positive integer, got {size!r}")
    size = int(size)

    destination = Path(os.fspath(path))
    destination.parent.mkdir(parents=True, exist_ok=True)

    reflectance, nodata_mask = _scene(size, np.random.default_rng(_SEED))

    # Invert reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE.
    dn = np.rint(reflectance * BOA_QUANTIFICATION_VALUE).astype(np.int64)
    dn -= BOA_ADD_OFFSET
    # Keep 0 for nodata and 65535 for saturated/defective out of the valid range.
    dn = np.clip(dn, 1, SATURATED - 1)
    dn[:, nodata_mask] = NODATA
    dn = dn.astype(np.uint16)

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
    }

    with rasterio.open(destination, "w", **profile) as dst:
        dst.write(dn)

        # Expose the baseline 04.00 conversion the way GDAL expects it:
        # reflectance = DN * scale + offset.
        dst.scales = tuple(1.0 / BOA_QUANTIFICATION_VALUE for _ in BANDS)
        dst.offsets = tuple(
            BOA_ADD_OFFSET / BOA_QUANTIFICATION_VALUE for _ in BANDS
        )

        dst.update_tags(
            AREA_OR_POINT="Area",
            TIFFTAG_DATETIME="2022:06:15 10:36:19",
            PRODUCT_TYPE="S2MSI2A",
            PROCESSING_LEVEL="Level-2A",
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            SPACECRAFT_NAME="Sentinel-2A",
            PRODUCT_URI=PRODUCT_URI,
            GRANULE_ID=GRANULE_ID,
            MGRS_TILE=MGRS_TILE,
            DATATAKE_SENSING_START=SENSING_TIME,
            PRODUCT_START_TIME=SENSING_TIME,
            PRODUCT_STOP_TIME=SENSING_TIME,
            BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            REFLECTANCE_CONVERSION_U="0.9694",
            SPECIAL_VALUE_NODATA=str(NODATA),
            SPECIAL_VALUE_SATURATED=str(SATURATED),
            MEAN_SUN_ZENITH_ANGLE="31.24",
            MEAN_SUN_AZIMUTH_ANGLE="157.83",
            CLOUDY_PIXEL_PERCENTAGE="0.0",
            BAND_ORDER=",".join(BANDS),
        )

        for index, band in enumerate(BANDS, start=1):
            dst.set_band_description(index, band)
            dst.update_tags(
                index,
                BAND_NAME=band,
                BAND_ID=str(BAND_IDS[band]),
                CENTRAL_WAVELENGTH_NM=str(CENTRAL_WAVELENGTHS_NM[band]),
                BANDWIDTH_NM=str(BANDWIDTHS_NM[band]),
                SPATIAL_RESOLUTION_M=str(int(RESOLUTION_M)),
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
                BOA_QUANTIFICATION_VALUE=str(BOA_QUANTIFICATION_VALUE),
            )

    return None
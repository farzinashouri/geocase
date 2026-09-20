"""Synthetic Sentinel-2 L2A product for use as a unit-test fixture.

The fixture is a miniature stand-in for a real Level-2A granule: same grid
geometry, same dtype, same no-data convention and -- most importantly -- the
same *radiometry*, including the ``BOA_ADD_OFFSET`` introduced at processing
baseline 04.00 (January 2022). Reader code that is correct against a real
post-2022 granule is correct against this file, and reader code that forgets
the offset is wrong against both by the same 0.1 reflectance.

Importing this module has no side effects.
"""

from __future__ import annotations

import operator

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

__all__ = ["s2_fixture"]

# --- Product constants (mirroring MTD_MSIL2A.xml / MTD_TL.xml) ---------------

BANDS = ("B2", "B3", "B4", "B8")            # the four 10 m bands, in this order
BAND_IDS = {"B2": 1, "B3": 2, "B4": 3, "B8": 7}          # ESA 0-based bandId
CENTRAL_WAVELENGTHS_NM = {"B2": 492.4, "B3": 559.8, "B4": 664.6, "B8": 832.8}
BANDWIDTHS_NM = {"B2": 66.0, "B3": 36.0, "B4": 31.0, "B8": 106.0}

PIXEL_SIZE_M = 10.0
EPSG = 32631                                 # UTM zone 31N / WGS 84
MGRS_TILE = "31TCJ"
ORIGIN_X, ORIGIN_Y = 399960.0, 4800000.0     # NW corner of tile 31TCJ

PROCESSING_BASELINE = "04.00"
QUANTIFICATION_VALUE = 10000                 # BOA_QUANTIFICATION_VALUE
BOA_ADD_OFFSET = -1000                       # baseline >= 04.00 only
NODATA = 0                                   # SPECIAL_VALUE NODATA
SATURATED = 65535                            # SPECIAL_VALUE SATURATED

SPACECRAFT = "Sentinel-2A"
SENSING_TIME = "2023-06-15T10:46:19.024Z"
PRODUCT_URI = (
    "S2A_MSIL2A_20230615T104619_N0400_R008_T31TCJ_20230615T134502.SAFE"
)
SUN_ZENITH_DEG = 22.35
SUN_AZIMUTH_DEG = 152.61

_SEED = 20230615                             # fixtures must be byte-reproducible

# --- Scene composition -------------------------------------------------------

_NO_DATA, _VEGETATION, _BARE_SOIL, _BUILT_UP, _WATER, _CLOUD = range(6)

# Plausible BOA (surface) reflectances. These are what a reader must recover
# after applying the offset; they put NDVI/NDWI in the right place per class:
# vegetation NDVI ~0.79, bare soil ~0.14, built-up ~0.11, water ~-0.75 with
# NDWI ~0.85, cloud NDVI ~-0.03.
_SPECTRA = {
    _VEGETATION: {"B2": 0.032, "B3": 0.058, "B4": 0.040, "B8": 0.345},
    _BARE_SOIL: {"B2": 0.115, "B3": 0.160, "B4": 0.225, "B8": 0.300},
    _BUILT_UP: {"B2": 0.135, "B3": 0.148, "B4": 0.165, "B8": 0.205},
    _WATER: {"B2": 0.055, "B3": 0.048, "B4": 0.028, "B8": 0.004},
    # Cloud tops routinely exceed reflectance 1.0 in the blue, i.e. DN above
    # the quantification value. Real granules do this; so does the fixture.
    _CLOUD: {"B2": 1.020, "B3": 0.980, "B4": 0.950, "B8": 0.900},
}


def _class_map(size):
    """Return the per-pixel land-cover code and the normalised centre grids."""
    axis = (np.arange(size, dtype=np.float64) + 0.5) / size
    uu, vv = np.meshgrid(axis, axis)         # uu: west->east, vv: north->south

    classes = np.full((size, size), _VEGETATION, dtype=np.uint8)
    classes[(uu > 0.58) & (vv < 0.42)] = _BARE_SOIL
    classes[(uu > 0.08) & (uu < 0.34) & (vv > 0.12) & (vv < 0.40)] = _BUILT_UP
    classes[np.abs(vv - (0.70 + 0.10 * np.sin(2.0 * np.pi * uu))) < 0.075] = _WATER
    classes[(uu - 0.80) ** 2 + (vv - 0.24) ** 2 < 0.010] = _CLOUD
    # Granule edge: real tiles are rarely full, and 0 means no-data, not black.
    classes[uu + vv < 0.16] = _NO_DATA
    return classes, uu, vv


def _digital_numbers(classes, uu, vv):
    """Turn a class map into baseline-04.00 digital numbers, band-major."""
    rng = np.random.default_rng(_SEED)
    refl = np.zeros((len(BANDS),) + classes.shape, dtype=np.float64)
    for index, band in enumerate(BANDS):
        for code, spectrum in _SPECTRA.items():
            refl[index][classes == code] = spectrum[band]

    # Smooth illumination/terrain shading gives spatially correlated texture;
    # the per-pixel term stands in for sensor noise and surface variability.
    refl *= 1.0 + 0.05 * np.sin(3.0 * np.pi * uu) * np.cos(2.0 * np.pi * vv)
    dn = refl * QUANTIFICATION_VALUE - BOA_ADD_OFFSET
    dn += rng.normal(size=dn.shape) * (35.0 + 0.02 * refl * QUANTIFICATION_VALUE)

    # Valid pixels stay clear of 0 so no-data stays unambiguous. Dark water in
    # the NIR still dips below DN 1000, i.e. slightly negative reflectance --
    # which is exactly what baseline-04.00 L2A does.
    dn = np.clip(np.rint(dn), NODATA + 1, SATURATED).astype(np.uint16)
    dn[:, classes == _NO_DATA] = NODATA
    return dn


def s2_fixture(path, size=32):
    """Write a synthetic Sentinel-2 L2A product to *path* as a GeoTIFF.

    The file has four uint16 bands in the order B2, B3, B4, B8 (the 10 m
    bands), is ``size`` pixels square, and sits on a north-up 10 m UTM grid
    (EPSG:32631) anchored at the north-west corner of MGRS tile 31TCJ.

    It is written at processing baseline 04.00, so the stored values are
    digital numbers that need the additive offset to become reflectance::

        reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE
                    = (DN - 1000) / 10000

    Both constants are recorded in the dataset and per-band metadata, and also
    as GDAL scale/offset (1e-4 and -0.1) so that scale-aware readers convert
    without being told. ``nodata`` is 0, as in the real product.

    The scene holds vegetation, bare fields, a built-up block, a meandering
    river, an opaque cloud, and a no-data sliver along the granule edge, so
    band ratios, masking and statistics all land in realistic ranges.

    Returns None.
    """
    size = operator.index(size)
    if size < 1:
        raise ValueError(f"size must be a positive pixel count, got {size!r}")

    classes, uu, vv = _class_map(size)
    data = _digital_numbers(classes, uu, vv)

    total = float(classes.size)
    nodata_pct = 100.0 * np.count_nonzero(classes == _NO_DATA) / total
    cloud_pct = 100.0 * np.count_nonzero(classes == _CLOUD) / total

    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": len(BANDS),
        "dtype": "uint16",
        "crs": CRS.from_epsg(EPSG),
        "transform": from_origin(ORIGIN_X, ORIGIN_Y, PIXEL_SIZE_M, PIXEL_SIZE_M),
        "nodata": NODATA,
        "compress": "deflate",
        "predictor": 2,
        "interleave": "pixel",
        # Keep four bands as four measurements: never let band 4 be read as alpha.
        "photometric": "minisblack",
    }
    if size >= 16:
        block = 256 if size >= 256 else 16
        profile.update(tiled=True, blockxsize=block, blockysize=block)

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)

        dst.scales = tuple(1.0 / QUANTIFICATION_VALUE for _ in BANDS)
        dst.offsets = tuple(BOA_ADD_OFFSET / QUANTIFICATION_VALUE for _ in BANDS)

        dst.update_tags(
            PRODUCT_TYPE="S2MSI2A",
            PROCESSING_LEVEL="Level-2A",
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            PRODUCT_URI=PRODUCT_URI,
            SPACECRAFT_NAME=SPACECRAFT,
            MGRS_TILE=MGRS_TILE,
            TILE_ID=f"T{MGRS_TILE}",
            DATATAKE_SENSING_START=SENSING_TIME,
            PRODUCT_START_TIME=SENSING_TIME,
            PRODUCT_STOP_TIME=SENSING_TIME,
            BOA_QUANTIFICATION_VALUE=str(QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            REFLECTANCE_CONVERSION=(
                "reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE"
            ),
            SPECIAL_VALUE_NODATA=str(NODATA),
            SPECIAL_VALUE_SATURATED=str(SATURATED),
            NODATA_PIXEL_PERCENTAGE=f"{nodata_pct:.6f}",
            CLOUDY_PIXEL_PERCENTAGE=f"{cloud_pct:.6f}",
            MEAN_SUN_ZENITH_ANGLE=f"{SUN_ZENITH_DEG:.6f}",
            MEAN_SUN_AZIMUTH_ANGLE=f"{SUN_AZIMUTH_DEG:.6f}",
        )

        for index, band in enumerate(BANDS, start=1):
            dst.set_band_description(index, band)
            dst.update_tags(
                index,
                BANDNAME=band,
                BAND_ID=str(BAND_IDS[band]),
                WAVELENGTH=f"{CENTRAL_WAVELENGTHS_NM[band]:.1f}",
                WAVELENGTH_UNIT="nm",
                BANDWIDTH=f"{BANDWIDTHS_NM[band]:.1f}",
                SPATIAL_RESOLUTION=f"{PIXEL_SIZE_M:.0f}",
                BOA_QUANTIFICATION_VALUE=str(QUANTIFICATION_VALUE),
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            )
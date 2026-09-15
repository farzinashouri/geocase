"""Synthetic Sentinel-2 L2A GeoTIFF fixtures for unit tests."""

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

BAND_ORDER = ("B2", "B3", "B4", "B8")
RESOLUTION_M = 10.0
QUANTIFICATION_VALUE = 10000
# Baseline >= 04.00 stores DN = reflectance * QUANTIFICATION_VALUE - BOA_ADD_OFFSET,
# so apparent reflectance down to -0.1 survives without clipping at 0 like older baselines.
BOA_ADD_OFFSET = -1000
PROCESSING_BASELINE = "04.00"
NODATA = 0

# Approximate surface reflectance per band (B2, B3, B4, B8) for a few land-cover classes.
_VEGETATION = (0.035, 0.065, 0.045, 0.35)
_WATER = (0.045, 0.035, 0.020, 0.010)
_SOIL = (0.100, 0.130, 0.160, 0.280)
_SHADOW = (-0.015, -0.010, -0.008, -0.020)


def s2_fixture(path, size=32):
    rng = np.random.default_rng(4002026)

    y, x = np.mgrid[0:size, 0:size]
    vegetation_mask = (x + y) < size
    soil_mask = (x > size * 0.6) & (y < size * 0.3)
    shadow_mask = (x < max(1, size // 8)) & (y < max(1, size // 8))

    reflectance = np.empty((4, size, size), dtype=np.float64)
    for i in range(4):
        band = np.where(vegetation_mask, _VEGETATION[i], _WATER[i])
        band = np.where(soil_mask, _SOIL[i], band)
        band = np.where(shadow_mask, _SHADOW[i], band)
        band = band + rng.normal(0.0, 0.004, size=(size, size))
        reflectance[i] = band

    dn = np.round(reflectance * QUANTIFICATION_VALUE - BOA_ADD_OFFSET)
    dn = np.clip(dn, 0, 65535).astype(np.uint16)

    transform = from_origin(499980.0, 4500000.0, RESOLUTION_M, RESOLUTION_M)
    crs = CRS.from_epsg(32633)

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=4,
        dtype="uint16",
        crs=crs,
        transform=transform,
        nodata=NODATA,
    ) as dst:
        dst.update_tags(
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            PRODUCT_TYPE="S2MSI2A",
            BOA_QUANTIFICATION_VALUE=str(QUANTIFICATION_VALUE),
        )
        for i, name in enumerate(BAND_ORDER, start=1):
            dst.write(dn[i - 1], i)
            dst.set_band_description(i, name)
            dst.update_tags(i, BAND_NAME=name, BOA_ADD_OFFSET=str(BOA_ADD_OFFSET))

    return None
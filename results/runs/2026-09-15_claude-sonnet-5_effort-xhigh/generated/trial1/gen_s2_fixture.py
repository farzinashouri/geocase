"""Synthetic Sentinel-2 L2A product fixture for unit tests."""

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

_BANDS = ("B02", "B03", "B04", "B08")

_CENTRAL_WAVELENGTH_NM = {
    "B02": 492.4,
    "B03": 559.8,
    "B04": 664.6,
    "B08": 832.8,
}

_BASE_REFLECTANCE = {
    "B02": 900,
    "B03": 1100,
    "B04": 1000,
    "B08": 2800,
}


def s2_fixture(path, size=32):
    rng = np.random.default_rng(42)

    crs = CRS.from_epsg(32633)
    transform = from_origin(499980, 5500020, 10, 10)

    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "nodata": 0,
        "width": size,
        "height": size,
        "count": len(_BANDS),
        "crs": crs,
        "transform": transform,
        "interleave": "pixel",
    }

    with rasterio.open(path, "w", **profile) as dst:
        dst.update_tags(
            PROCESSING_BASELINE="04.00",
            PRODUCT_TYPE="S2MSI2A",
            SPECIAL_VALUE_NODATA="0",
            SPECIAL_VALUE_SATURATED="65535",
            BOA_QUANTIFICATION_VALUE="10000",
        )
        for band_index, band in enumerate(_BANDS, start=1):
            base = _BASE_REFLECTANCE[band]
            noise = rng.normal(0, 150, size=(size, size))
            values = np.clip(base + noise, 1, 10000).astype(np.uint16)

            dst.write(values, band_index)
            dst.set_band_description(band_index, band)
            dst.update_tags(
                band_index,
                BAND_NAME=band,
                CENTRAL_WAVELENGTH_NM=str(_CENTRAL_WAVELENGTH_NM[band]),
            )

    return None
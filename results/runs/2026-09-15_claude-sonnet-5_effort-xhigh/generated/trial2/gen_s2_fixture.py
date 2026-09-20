"""Synthetic Sentinel-2 L2A GeoTIFF fixture for unit tests."""

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

_BANDS = ("B2", "B3", "B4", "B8")
_PROCESSING_BASELINE = "04.00"
_BOA_QUANTIFICATION_VALUE = 10000
# From baseline 04.00 onward ESA adds this offset before scaling DN, so
# true reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE.
_BOA_ADD_OFFSET = -1000


def s2_fixture(path, size=32):
    """Write a synthetic 4-band (B2, B3, B4, B8) Sentinel-2 L2A GeoTIFF to `path`."""
    rng = np.random.default_rng(0)

    reflectance = {
        "B2": rng.uniform(0.02, 0.15, size=(size, size)),
        "B3": rng.uniform(0.03, 0.18, size=(size, size)),
        "B4": rng.uniform(0.02, 0.20, size=(size, size)),
        "B8": rng.uniform(0.10, 0.45, size=(size, size)),
    }

    data = np.zeros((len(_BANDS), size, size), dtype=np.uint16)
    for i, band in enumerate(_BANDS):
        dn = reflectance[band] * _BOA_QUANTIFICATION_VALUE - _BOA_ADD_OFFSET
        data[i] = np.clip(np.round(dn), 1, 65535).astype(np.uint16)

    transform = from_origin(499980.0, 5900040.0, 10, 10)
    crs = CRS.from_epsg(32633)

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=len(_BANDS),
        dtype=np.uint16,
        crs=crs,
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(data)
        dst.update_tags(
            PRODUCT_TYPE="S2MSI2A",
            PROCESSING_BASELINE=_PROCESSING_BASELINE,
            BOA_ADD_OFFSET=str(_BOA_ADD_OFFSET),
            BOA_QUANTIFICATION_VALUE=str(_BOA_QUANTIFICATION_VALUE),
        )
        for i, band in enumerate(_BANDS, start=1):
            dst.set_band_description(i, band)
            dst.update_tags(i, BAND_NAME=band)

    return None
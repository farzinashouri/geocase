"""Synthetic Sentinel-2 L2A GeoTIFF fixture generator for unit tests."""

import numpy as np
import rasterio
from rasterio.transform import from_origin

_BANDS = ("B2", "B3", "B4", "B8")
_WAVELENGTH_NM = {"B2": 492, "B3": 560, "B4": 665, "B8": 833}

# Processing baseline >= 04.00: reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE.
# BOA_ADD_OFFSET is negative, so DN must be shifted *up* by its magnitude to store reflectance.
_BOA_ADD_OFFSET = -1000
_BOA_QUANTIFICATION_VALUE = 10000

# Rough (B2, B3, B4, B8) surface reflectance signatures for a few land-cover classes.
_CLASS_SPECTRA = {
    "water": (0.08, 0.06, 0.04, 0.02),
    "vegetation": (0.04, 0.07, 0.05, 0.35),
    "bare_soil": (0.12, 0.14, 0.18, 0.22),
    "cloud": (0.60, 0.60, 0.60, 0.62),
}


def s2_fixture(path, size=32):
    rng = np.random.default_rng(42)

    classes = list(_CLASS_SPECTRA)
    centers = rng.uniform(0, size, size=(len(classes), 2))
    rows, cols = np.mgrid[0:size, 0:size]
    coords = np.stack([rows, cols], axis=-1).astype(np.float64)
    dists = np.stack(
        [np.hypot(coords[..., 0] - cy, coords[..., 1] - cx) for cy, cx in centers],
        axis=-1,
    )
    labels = np.argmin(dists, axis=-1)

    reflectance = np.empty((len(_BANDS), size, size), dtype=np.float64)
    for band_idx in range(len(_BANDS)):
        band_values = np.array(
            [_CLASS_SPECTRA[classes[label]][band_idx] for label in range(len(classes))]
        )
        base = band_values[labels]
        noise = rng.normal(0.0, 0.015, size=(size, size))
        reflectance[band_idx] = np.clip(base + noise, 0.0, 1.0)

    dn = np.round(reflectance * _BOA_QUANTIFICATION_VALUE - _BOA_ADD_OFFSET)
    dn = np.clip(dn, 0, 65535).astype(np.uint16)

    transform = from_origin(499980.0, 4700020.0, 10, 10)

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=len(_BANDS),
        dtype=rasterio.uint16,
        crs="EPSG:32633",
        transform=transform,
        nodata=0,
    ) as dst:
        dst.update_tags(
            PROCESSING_BASELINE="04.00",
            PRODUCT_TYPE="S2MSI2A",
            SPACECRAFT_NAME="Sentinel-2A",
            MTD_MSIL2A="synthetic-fixture",
        )
        for i, band in enumerate(_BANDS, start=1):
            dst.write(dn[i - 1], i)
            dst.set_band_description(i, band)
            dst.update_tags(
                i,
                BAND_NAME=band,
                WAVELENGTH_NM=str(_WAVELENGTH_NM[band]),
                BOA_ADD_OFFSET=str(_BOA_ADD_OFFSET),
                BOA_QUANTIFICATION_VALUE=str(_BOA_QUANTIFICATION_VALUE),
            )

    return None
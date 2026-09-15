```python
"""Synthetic Sentinel-2 L2A GeoTIFF fixture generator for unit tests."""

import numpy as np
import rasterio
from rasterio.transform import from_origin


def s2_fixture(path, size=32):
    rng = np.random.default_rng(42)

    # Typical Sentinel-2 L2A surface reflectance values are stored as
    # uint16 with an offset of 1000 (BOA_ADD_OFFSET) at baseline 04.00,
    # scaled by 10000. Emulate plausible reflectance for four 10 m bands.
    band_means = {
        "B2": 900,   # blue
        "B3": 1100,  # green
        "B4": 1000,  # red
        "B8": 3200,  # NIR
    }

    bands = []
    for mean in band_means.values():
        data = rng.normal(loc=mean, scale=mean * 0.05, size=(size, size))
        data = np.clip(data, 1, 65535).astype(np.uint16)
        bands.append(data)

    stack = np.stack(bands, axis=0)

    # UTM zone 33N, 10 m pixels, arbitrary but realistic origin.
    transform = from_origin(500000.0, 4500000.0, 10, 10)
    crs = "EPSG:32633"

    profile = {
        "driver": "GTiff",
        "height": size,
        "width": size,
        "count": stack.shape[0],
        "dtype": "uint16",
        "crs": crs,
        "transform": transform,
        "nodata": 0,
        "compress": "deflate",
    }

    tags = {
        "PROCESSING_BASELINE": "04.00",
        "PRODUCT_TYPE": "S2MSI2A",
        "BOA_ADD_OFFSET": "-1000",
    }

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(stack)
        dst.update_tags(**tags)
        for i, band_name in enumerate(band_means.keys(), start=1):
            dst.set_band_description(i, band_name)
            dst.update_tags(i, BAND_NAME=band_name)

    return None
```
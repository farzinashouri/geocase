```python
"""Synthetic Sentinel-2 L2A fixture generator for unit tests."""

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin


def s2_fixture(path, size=32):
    """Write a small synthetic Sentinel-2 L2A GeoTIFF (B2, B3, B4, B8 @ 10m) to `path`."""
    rng = np.random.default_rng(42)

    bands = np.stack(
        [
            rng.integers(1, 10000, size=(size, size), dtype=np.uint16)
            for _ in range(4)
        ],
        axis=0,
    )

    # UTM zone 33N, 10 m pixels, arbitrary top-left origin on a 10 m grid.
    crs = CRS.from_epsg(32633)
    transform = from_origin(600000.0, 5300000.0, 10.0, 10.0)

    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "nodata": 0,
        "width": size,
        "height": size,
        "count": 4,
        "crs": crs,
        "transform": transform,
        "compress": "deflate",
    }

    band_names = ["B02", "B03", "B04", "B08"]

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(bands)
        for idx, name in enumerate(band_names, start=1):
            dst.set_band_description(idx, name)
        dst.update_tags(
            PROCESSING_BASELINE="04.00",
            PRODUCT_TYPE="S2MSI2A",
            MTD_MSIL2A="synthetic",
        )
```
```python
"""Synthetic Sentinel-2 L2A fixture generator for tests."""

import numpy as np
import rasterio
from rasterio.transform import from_origin

BANDS = ("B02", "B03", "B04", "B08")
PROCESSING_BASELINE = "04.00"


def s2_fixture(path, size=32):
    rng = np.random.default_rng(42)

    data = np.stack(
        [
            rng.integers(1, 10000, size=(size, size), dtype=np.uint16)
            for _ in BANDS
        ],
        axis=0,
    )

    # UTM zone 33N, 10 m pixels, arbitrary but plausible origin.
    transform = from_origin(500000.0, 5000000.0, 10.0, 10.0)
    crs = "EPSG:32633"

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=len(BANDS),
        dtype=data.dtype,
        crs=crs,
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(data)
        for i, band_name in enumerate(BANDS, start=1):
            dst.set_band_description(i, band_name)
        dst.update_tags(
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            PRODUCT_TYPE="S2MSI2A",
        )

    return None
```
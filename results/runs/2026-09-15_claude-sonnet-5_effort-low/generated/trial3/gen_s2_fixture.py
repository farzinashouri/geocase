"""Synthetic Sentinel-2 L2A fixture generator for unit tests."""

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin


def s2_fixture(path, size=32):
    band_names = ("B2", "B3", "B4", "B8")
    rng = np.random.default_rng(42)

    data = np.stack(
        [
            rng.integers(1, 10000, size=(size, size), dtype=np.uint16)
            for _ in band_names
        ]
    )

    pixel_size = 10.0
    transform = from_origin(499980.0, 5900040.0, pixel_size, pixel_size)
    crs = CRS.from_epsg(32633)

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=len(band_names),
        dtype=data.dtype,
        crs=crs,
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(data)
        for idx, name in enumerate(band_names, start=1):
            dst.set_band_description(idx, name)
        dst.update_tags(
            PROCESSING_BASELINE="04.00",
            PRODUCT_TYPE="S2MSI2A",
        )

    return None
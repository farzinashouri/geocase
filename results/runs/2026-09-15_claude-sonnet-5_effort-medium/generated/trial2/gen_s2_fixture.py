"""Synthetic Sentinel-2 L2A fixture generator for unit tests."""

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin


def s2_fixture(path, size=32):
    rng = np.random.default_rng(42)

    band_ranges = {
        "B2": (200, 2000),
        "B3": (200, 2200),
        "B4": (200, 2400),
        "B8": (500, 4000),
    }
    band_order = ["B2", "B3", "B4", "B8"]

    data = np.stack(
        [
            rng.integers(low, high, size=(size, size), dtype=np.uint16)
            for low, high in (band_ranges[b] for b in band_order)
        ]
    )

    crs = CRS.from_epsg(32633)
    resolution = 10.0
    transform = from_origin(499980.0, 5400000.0, resolution, resolution)

    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "nodata": 0,
        "width": size,
        "height": size,
        "count": len(band_order),
        "crs": crs,
        "transform": transform,
        "compress": "deflate",
        "tiled": True,
        "blockxsize": 16 if size >= 16 else size,
        "blockysize": 16 if size >= 16 else size,
        "interleave": "pixel",
    }

    with rasterio.open(path, "w", **profile) as dst:
        for i, band_name in enumerate(band_order, start=1):
            dst.write(data[i - 1], i)
            dst.set_band_description(i, band_name)

        dst.update_tags(
            PROCESSING_BASELINE="04.00",
            PRODUCT_TYPE="S2MSI2A",
            SPACECRAFT_NAME="Sentinel-2A",
        )
        for i, band_name in enumerate(band_order, start=1):
            dst.update_tags(i, BAND_NAME=band_name, BANDWIDTH="10m")

    return None
"""Synthetic Sentinel-2 L2A fixture generator for unit tests."""

import numpy as np
import rasterio
from rasterio.transform import from_origin


def s2_fixture(path, size=32):
    """Write a synthetic 4-band (B2, B3, B4, B8) Sentinel-2 L2A 10 m GeoTIFF to `path`."""
    rng = np.random.default_rng(seed=42)

    bands = np.stack(
        [
            rng.integers(1000, 4000, size=(size, size), dtype=np.uint16),  # B2 - blue
            rng.integers(1000, 4000, size=(size, size), dtype=np.uint16),  # B3 - green
            rng.integers(1000, 4000, size=(size, size), dtype=np.uint16),  # B4 - red
            rng.integers(1500, 6000, size=(size, size), dtype=np.uint16),  # B8 - NIR
        ],
        axis=0,
    )

    # UTM zone 33N, 10 m pixels, upper-left anchored at a plausible S2 tile origin.
    transform = from_origin(499980.0, 5900040.0, 10.0, 10.0)

    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "nodata": 0,
        "width": size,
        "height": size,
        "count": 4,
        "crs": "EPSG:32633",
        "transform": transform,
        "compress": "deflate",
    }

    band_names = ("B2", "B3", "B4", "B8")

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(bands)
        dst.update_tags(
            PROCESSING_BASELINE="04.00",
            PRODUCT_TYPE="S2MSI2A",
        )
        for idx, name in enumerate(band_names, start=1):
            dst.set_band_description(idx, name)
            dst.update_tags(idx, BAND_NAME=name)

    return None
```python
"""
s2_fixture.py

Generate a small synthetic Sentinel-2 L2A product as a GeoTIFF for unit testing.
"""

import os
import numpy as np
from rasterio.transform import from_bounds
import rasterio


def s2_fixture(path, size=32):
    """
    Write a small synthetic Sentinel-2 L2A product to `path` as a GeoTIFF.

    The product includes the four 10 m bands (B2, B3, B4, B8) in that order,
    with a processing baseline of 04.00, and is `size` pixels square.

    Parameters:
        path (str): Output file path for the GeoTIFF.
        size (int): Pixel dimension of the square raster (default 32).

    Returns:
        None
    """
    # Sentinel-2 L2A metadata
    crs = "EPSG:32632"  # UTM Zone 32N (common for S2 products)
    transform = from_bounds(
        500000.0, 5640000.0,
        500000.0 + size * 10, 5640000.0 + size * 10,
        width=size, height=size
    )

    # Create synthetic data for each band
    # Use a gradient pattern to simulate realistic reflectance values
    x = np.linspace(0, 1, size)
    y = np.linspace(0, 1, size)
    xx, yy = np.meshgrid(x, y)

    # Band-specific patterns (B2, B3, B4, B8)
    b2 = (xx * 1000).astype(np.uint16)  # Blue
    b3 = (yy * 1000).astype(np.uint16)  # Green
    b4 = ((xx + yy) * 500).astype(np.uint16)  # Red
    b8 = (np.sin(xx * np.pi) * 2000).astype(np.uint16)  # NIR

    data = np.stack([b2, b3, b4, b8], axis=0)

    # Write GeoTIFF
    with rasterio.open(
        path,
        'w',
        driver='GTiff',
        height=size,
        width=size,
        count=4,
        dtype='uint16',
        crs=crs,
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(data)

    return None
```
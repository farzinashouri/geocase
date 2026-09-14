```python
import numpy as np
import rasterio
from rasterio.transform import Affine
from rasterio.crs import CRS


def s2_fixture(path, size=32):
    """
    Write a synthetic Sentinel-2 L2A product to path as a GeoTIFF.
    
    The product covers the four 10m bands (B2, B3, B4, B8) in that order,
    at processing baseline 04.00, and is size x size pixels.
    """
    # Generate synthetic spectral data
    x = np.arange(size)
    y = np.arange(size)
    xx, yy = np.meshgrid(x, y)
    
    # L2A reflectance: 0-10000 (0-100%)
    b2 = np.uint16(np.clip(2000 + 500 * np.sin(xx / size * np.pi), 0, 10000))
    b3 = np.uint16(np.clip(2500 + 500 * np.sin((xx + yy) / size * np.pi), 0, 10000))
    b4 = np.uint16(np.clip(3000 + 500 * np.cos(xx / size * np.pi), 0, 10000))
    b8 = np.uint16(np.clip(5000 + 1000 * np.sin(yy / size * np.pi), 0, 10000))
    
    data = np.array([b2, b3, b4, b8], dtype=np.uint16)
    
    # UTM Zone 32N with 10m resolution
    crs = CRS.from_epsg(32632)
    transform = Affine(10.0, 0, 500000, 0, -10.0, 5000000)
    
    # Write GeoTIFF
    with rasterio.open(
        path,
        'w',
        driver='GTiff',
        height=size,
        width=size,
        count=4,
        dtype=np.uint16,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(data)
```
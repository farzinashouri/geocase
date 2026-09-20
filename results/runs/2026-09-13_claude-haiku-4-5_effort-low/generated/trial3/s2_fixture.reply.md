```python
import numpy as np
import rasterio
from rasterio.transform import from_bounds


def s2_fixture(path, size=32):
    """Write a synthetic Sentinel-2 L2A product to path as GeoTIFF.
    
    Creates a four-band GeoTIFF covering B2, B3, B4, B8 (10m bands) with
    realistic reflectance values suitable for testing code that reads L2A products.
    """
    np.random.seed(42)
    x = np.linspace(0, 1, size)
    y = np.linspace(0, 1, size)
    xx, yy = np.meshgrid(x, y)
    
    pattern = (xx + yy) / 2
    detail = 0.15 * np.sin(xx * 6) * np.cos(yy * 6)
    noise = np.random.normal(0, 0.04, (size, size))
    base = pattern + detail + noise
    
    b2 = np.uint16(np.clip(1500 + 1000 * base, 0, 10000))
    b3 = np.uint16(np.clip(2000 + 1200 * base, 0, 10000))
    b4 = np.uint16(np.clip(1200 + 1000 * base, 0, 10000))
    b8 = np.uint16(np.clip(3500 + 2000 * base, 0, 10000))
    
    data = np.stack([b2, b3, b4, b8], axis=0)
    
    transform = from_bounds(
        500000, 5000000,
        500000 + size * 10, 5000000 + size * 10,
        width=size, height=size
    )
    
    with rasterio.open(
        path,
        'w',
        driver='GTiff',
        height=size,
        width=size,
        count=4,
        dtype=rasterio.uint16,
        crs='EPSG:32632',
        transform=transform,
    ) as dst:
        dst.write(data)
```
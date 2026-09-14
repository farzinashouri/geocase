```python
import numpy as np
import rasterio
from rasterio.transform import from_bounds


def s2_fixture(path, size=32):
    """Write a synthetic Sentinel-2 L2A product as a GeoTIFF."""
    # Create synthetic data for bands B2, B3, B4, B8
    data = np.zeros((4, size, size), dtype=np.uint16)
    
    # Generate grid of coordinates
    y, x = np.mgrid[0:size, 0:size]
    
    # Realistic reflectance patterns (0-10000 range)
    data[0] = np.clip(2000 + 1000 * x / size + 500 * np.sin(y / 5), 0, 10000).astype(np.uint16)  # B2
    data[1] = np.clip(2500 + 1000 * y / size + 500 * np.cos(x / 5), 0, 10000).astype(np.uint16)  # B3
    data[2] = np.clip(1500 + 800 * (x + y) / (2 * size), 0, 10000).astype(np.uint16)  # B4
    data[3] = np.clip(4000 + 1500 * x / size + 1000 * y / size, 0, 10000).astype(np.uint16)  # B8
    
    # Define georeferencing (1km square in UTM zone 32N)
    transform = from_bounds(500000, 6000000, 500001, 6000001, size, size)
    
    # Write GeoTIFF
    with rasterio.open(
        path,
        'w',
        driver='GTiff',
        height=size,
        width=size,
        count=4,
        dtype=np.uint16,
        crs='EPSG:32632',
        transform=transform,
    ) as dst:
        dst.write(data[0], 1)
        dst.write(data[1], 2)
        dst.write(data[2], 3)
        dst.write(data[3], 4)
        dst.update_tags(PROCESSING_BASELINE='04.00')
```
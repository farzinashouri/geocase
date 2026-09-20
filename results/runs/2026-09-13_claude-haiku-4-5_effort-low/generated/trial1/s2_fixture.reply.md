```python
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS


def s2_fixture(path, size=32):
    rng = np.random.default_rng(42)
    crs = CRS.from_epsg(32632)
    left, bottom = 400000.0, 4500000.0
    transform = from_bounds(left, bottom, left + size * 10, bottom + size * 10, size, size)
    
    # B2, B3, B4, B8 in order - synthetic reflectance values (uint16, 0-10000)
    bands = [
        rng.integers(1000, 4000, (size, size), dtype=np.uint16),  # B2
        rng.integers(1000, 4000, (size, size), dtype=np.uint16),  # B3
        rng.integers(500, 3000, (size, size), dtype=np.uint16),   # B4
        rng.integers(2000, 6000, (size, size), dtype=np.uint16),  # B8
    ]
    
    with rasterio.open(path, 'w', driver='GTiff', height=size, width=size,
                       count=4, dtype=np.uint16, crs=crs, transform=transform) as dst:
        for i, data in enumerate(bands, 1):
            dst.write(data, i)
        dst.update_tags(PROCESSING_BASELINE='04.00')
```
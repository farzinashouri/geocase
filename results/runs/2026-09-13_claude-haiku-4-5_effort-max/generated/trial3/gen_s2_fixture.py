import numpy as np
import rasterio
from rasterio.transform import Affine
from rasterio.crs import CRS


def s2_fixture(path, size=32):
    np.random.seed(42)
    
    band_data = np.zeros((4, size, size), dtype=np.uint16)
    band_data[0] = np.random.randint(1000, 3000, (size, size), dtype=np.uint16)
    band_data[1] = np.random.randint(1500, 3500, (size, size), dtype=np.uint16)
    band_data[2] = np.random.randint(1000, 3000, (size, size), dtype=np.uint16)
    band_data[3] = np.random.randint(3000, 7000, (size, size), dtype=np.uint16)
    
    transform = Affine(10, 0, 500000, 0, -10, 5000000)
    
    with rasterio.open(
        path,
        'w',
        driver='GTiff',
        height=size,
        width=size,
        count=4,
        dtype=np.uint16,
        crs=CRS.from_epsg(32632),
        transform=transform,
    ) as dst:
        for i in range(4):
            dst.write(band_data[i], i + 1)
import numpy as np
import rasterio
from rasterio.transform import Affine

def s2_fixture(path, size=32):
    np.random.seed(42)
    data = np.random.randint(0, 10000, size=(4, size, size), dtype=np.uint16)
    transform = Affine(10, 0, 0, 0, -10, 0)
    with rasterio.open(
        path,
        'w',
        driver='GTiff',
        height=size,
        width=size,
        count=4,
        dtype='uint16',
        crs='EPSG:32633',
        transform=transform,
    ) as dst:
        dst.write(data)
    return None
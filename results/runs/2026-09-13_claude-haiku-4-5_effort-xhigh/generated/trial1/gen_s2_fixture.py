import numpy as np
import rasterio
from rasterio.transform import Affine
from rasterio.crs import CRS


def s2_fixture(path, size=32):
    """Write a synthetic Sentinel-2 L2A product to a GeoTIFF file."""
    np.random.seed(42)
    bands_data = []
    
    for band_idx in range(4):
        base = np.random.randint(1000, 8000, size=(size, size), dtype=np.uint16)
        y, x = np.ogrid[:size, :size]
        pattern = ((x * 7 + y * 11) % 500).astype(np.uint16)
        data = np.clip(base + pattern, 0, 10000)
        bands_data.append(data)
    
    data = np.stack(bands_data, axis=0)
    
    crs = CRS.from_epsg(32633)
    transform = Affine.translation(0, size * 10) * Affine.scale(10, -10)
    
    with rasterio.open(
        path,
        'w',
        driver='GTiff',
        height=size,
        width=size,
        count=4,
        dtype=np.uint16,
        crs=crs,
        transform=transform
    ) as dst:
        dst.write(data)
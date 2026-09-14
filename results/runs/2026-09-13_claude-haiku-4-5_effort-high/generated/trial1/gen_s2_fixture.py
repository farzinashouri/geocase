import numpy as np
import rasterio
from rasterio.transform import Affine
from rasterio.crs import CRS


def s2_fixture(path, size=32):
    """
    Write a synthetic Sentinel-2 L2A product to path as a GeoTIFF.
    
    Covers the four 10m bands (B2, B3, B4, B8) at processing baseline 04.00.
    """
    # Synthetic band data: uint16 is standard for L2A reflectance values
    np.random.seed(42)
    data = np.zeros((4, size, size), dtype=np.uint16)
    for i in range(4):
        data[i] = np.random.randint(1000, 5000, (size, size), dtype=np.uint16)
    
    # Sentinel-2 standard: UTM projection, 10m resolution
    crs = CRS.from_epsg(32633)
    transform = Affine(10.0, 0, 500000, 0, -10.0, 5000000)
    
    # Write GeoTIFF with proper geospatial metadata
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
        TILED=True,
        BLOCKXSIZE=512,
        BLOCKYSIZE=512,
    ) as dst:
        dst.write(data)
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS


def s2_fixture(path, size=32):
    """
    Write a synthetic Sentinel-2 L2A product to path as a GeoTIFF.
    
    Covers the four 10 m bands (B2, B3, B4, B8) in that order.
    Processing baseline 04.00.
    """
    # Create synthetic data for 4 bands (B2, B3, B4, B8)
    # Sentinel-2 L2A reflectance data: 0-10000 (12-bit)
    data = np.zeros((4, size, size), dtype=np.uint16)
    
    # Base values for each band (realistic)
    base_values = [2500, 3000, 3500, 5500]
    
    for band_idx in range(4):
        y, x = np.ogrid[:size, :size]
        base = base_values[band_idx]
        data[band_idx] = np.clip(base + (x + y) * 20, 0, 10000).astype(np.uint16)
    
    # UTM CRS (zone 32N, arbitrary)
    crs = CRS.from_epsg(32632)
    
    # Bounds for a size x size pixel tile at 10 m/pixel
    west, south = 400000, 4000000
    east, north = west + size * 10, south + size * 10
    transform = from_bounds(west, south, east, north, size, size)
    
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
        dst.update_tags(1, PROCESSING_BASELINE='04.00')
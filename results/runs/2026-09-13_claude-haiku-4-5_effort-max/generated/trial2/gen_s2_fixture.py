import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds


def s2_fixture(path, size=32):
    """
    Write a synthetic Sentinel-2 L2A product to path as a GeoTIFF.
    
    Creates a GeoTIFF covering the four 10m bands (B2, B3, B4, B8)
    at processing baseline 04.00, suitable for unit testing.
    Returns None.
    """
    # Create synthetic data for each band (B2, B3, B4, B8)
    # Sentinel-2 L2A reflectance values: 0-10000 (uint16)
    band_names = ['B2', 'B3', 'B4', 'B8']
    base_reflectances = [1500, 1800, 2500, 3000]
    
    bands_data = []
    for base_value in base_reflectances:
        x = np.linspace(0, 1, size)
        y = np.linspace(0, 1, size)
        xx, yy = np.meshgrid(x, y)
        band_data = (base_value + 500 * (xx + yy)).astype(np.uint16)
        bands_data.append(band_data)
    
    # Geospatial parameters
    crs = CRS.from_epsg(32632)  # UTM zone 32N
    left = 600000.0
    top = 4000000.0
    pixel_size = 10.0
    
    transform = from_bounds(
        left,
        top - size * pixel_size,
        left + size * pixel_size,
        top,
        size,
        size
    )
    
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
        compress='deflate'
    ) as dst:
        for idx, (band_data, band_name) in enumerate(zip(bands_data, band_names), 1):
            dst.write(band_data, idx)
            dst.update_tags(idx, name=band_name)
        
        dst.update_tags(
            processing_baseline='04.00',
            product_type='S2MSI2A'
        )
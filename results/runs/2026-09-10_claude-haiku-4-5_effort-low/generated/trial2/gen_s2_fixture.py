import numpy as np
import rasterio
from rasterio.transform import from_bounds
from pyproj import CRS


def s2_fixture(path, size=32):
    """Write a synthetic Sentinel-2 L2A product to path as a GeoTIFF.
    
    The product covers the four 10m bands (B2, B3, B4, B8) in that order,
    at processing baseline 04.00, with size x size pixels.
    
    Parameters
    ----------
    path : str or PathLike
        Output file path for the GeoTIFF
    size : int, default 32
        Dimension of each band (size x size pixels)
    
    Returns
    -------
    None
    """
    # Create synthetic band data (uint16, 0-10000 range for L2A reflectances)
    rng = np.random.RandomState(42)
    b2 = rng.randint(500, 3000, (size, size), dtype=np.uint16)
    b3 = rng.randint(700, 3500, (size, size), dtype=np.uint16)
    b4 = rng.randint(600, 3200, (size, size), dtype=np.uint16)
    b8 = rng.randint(2000, 8000, (size, size), dtype=np.uint16)
    data = np.stack([b2, b3, b4, b8], axis=0)
    
    # UTM zone 33N as representative coordinate system
    utm_crs = CRS.from_epsg(32633)
    
    # Geotransform for 10m resolution
    xmin, ymin = 500000, 6650000
    xmax = xmin + size * 10
    ymax = ymin + size * 10
    transform = from_bounds(xmin, ymin, xmax, ymax, size, size)
    
    # Write as GeoTIFF
    with rasterio.open(
        path,
        'w',
        driver='GTiff',
        height=size,
        width=size,
        count=4,
        dtype=rasterio.uint16,
        crs=utm_crs,
        transform=transform,
    ) as dst:
        dst.write(data)
        dst.update_tags(processing_baseline='04.00')
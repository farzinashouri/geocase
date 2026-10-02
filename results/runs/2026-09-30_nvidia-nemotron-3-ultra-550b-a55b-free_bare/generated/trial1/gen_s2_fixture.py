import numpy as np
import rasterio
from rasterio.transform import Affine
from rasterio.crs import CRS


def s2_fixture(path, size=32):
    """
    Write a synthetic Sentinel-2 L2A product (4 bands, 10 m resolution) to a GeoTIFF.

    Parameters
    ----------
    path : str or Path
        Output file path.
    size : int, optional
        Width and height of the image in pixels (default 32).

    Returns
    -------
    None
    """
    # UTM zone 32N (EPSG:32632) – a common Sentinel-2 tile CRS
    crs = CRS.from_epsg(32632)
    # 10 m pixel size, origin at (500000, 5000000) – arbitrary but realistic
    transform = Affine(10.0, 0.0, 500000.0, 0.0, -10.0, 5000000.0)

    # Synthetic data: 4 bands (B2, B3, B4, B8) as uint16 (L2A scaling factor 10000)
    data = np.zeros((4, size, size), dtype=np.uint16)
    # Simple distinct values per band for easy identification in tests
    data[0] = 1000   # B2
    data[1] = 2000   # B3
    data[2] = 3000   # B4
    data[3] = 4000   # B8

    band_names = ['B2', 'B3', 'B4', 'B8']
    wavelengths = {'B2': 492.4, 'B3': 559.8, 'B4': 664.6, 'B8': 832.8}

    profile = {
        'driver': 'GTiff',
        'dtype': 'uint16',
        'width': size,
        'height': size,
        'count': 4,
        'crs': crs,
        'transform': transform,
        'nodata': 0,
        'compress': 'lzw',
        'tiled': True,
        'blockxsize': 256,
        'blockysize': 256,
    }

    with rasterio.open(path, 'w', **profile) as dst:
        dst.write(data)
        for idx, name in enumerate(band_names, start=1):
            dst.set_band_description(idx, name)
            dst.update_tags(
                idx,
                BAND_NAME=name,
                WAVELENGTH_NM=wavelengths[name],
                PROCESSING_BASELINE='04.00',
            )
        dst.update_tags(
            PROCESSING_BASELINE='04.00',
            SENSOR='MSI',
            MISSION='S2A',
            PRODUCT_LEVEL='L2A',
        )
    return None
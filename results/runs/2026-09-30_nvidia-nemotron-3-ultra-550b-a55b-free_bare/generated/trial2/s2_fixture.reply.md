```python
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS


def s2_fixture(path, size=32):
    """
    Write a synthetic Sentinel-2 L2A product as a multi-band GeoTIFF.

    The file contains the four 10 m bands (B2, B3, B4, B8) in that order,
    with processing baseline 04.00, and is `size` pixels square. The data
    are uint16 scaled reflectances (scale=0.0001, offset=0) with a nodata
    value of 0, in a UTM zone 33N projection (EPSG:32633) at 10 m resolution.

    Parameters
    ----------
    path : str or Path
        Output file path.
    size : int, optional
        Width and height in pixels (default 32).

    Returns
    -------
    None
    """
    # Coordinate reference system and geotransform (10 m pixels)
    crs = CRS.from_epsg(32633)
    transform = from_origin(500000.0, 5000000.0, 10.0, 10.0)

    # Band metadata
    band_names = ["B2", "B3", "B4", "B8"]
    wavelengths_nm = [490, 560, 665, 842]  # central wavelengths in nm

    # Generate synthetic reflectance data (0–10000)
    rng = np.random.default_rng(42)
    x = np.linspace(0, 1, size)
    y = np.linspace(0, 1, size)
    xx, yy = np.meshgrid(x, y)
    base = (xx + yy) * 5000  # smooth gradient 0–10000

    data = np.zeros((4, size, size), dtype=np.uint16)
    for i in range(4):
        band_data = base + rng.normal(0, 200, size=(size, size))
        data[i] = np.clip(band_data, 0, 10000).astype(np.uint16)

    # Rasterio profile
    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "width": size,
        "height": size,
        "count": 4,
        "crs": crs,
        "transform": transform,
        "nodata": 0,
        "compress": "lzw",
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)
        for idx, (name, wl) in enumerate(zip(band_names, wavelengths_nm), start=1):
            dst.set_band_description(idx, name)
            dst.update_tags(
                idx,
                scale=0.0001,
                offset=0.0,
                wavelength_nm=wl,
                resolution_m=10,
            )
        dst.update_tags(
            processing_baseline="04.00",
            product_type="S2MSI2A",
            sensor="MSI",
            satellite="Sentinel-2A",
        )

    return None
```
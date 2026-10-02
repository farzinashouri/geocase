```python
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS
from rasterio.enums import Resampling


def s2_fixture(path, size=32):
    """
    Write a synthetic Sentinel-2 L2A GeoTIFF fixture with four 10 m bands (B2, B3, B4, B8).

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
    # Fixed seed for reproducibility
    rng = np.random.default_rng(42)

    # Sentinel-2 L2A uses UTM; pick zone 32N (EPSG:32632) and a plausible origin
    crs = CRS.from_epsg(32632)
    west, north = 500_000.0, 5_000_000.0  # UTM coordinates (metres)
    transform = from_origin(west, north, 10.0, 10.0)  # 10 m resolution

    # Generate synthetic reflectance data scaled to 0–10000 (uint16)
    # Typical ranges per band (very rough):
    # B2 (Blue)  : 0–3000, B3 (Green): 0–4000, B4 (Red) : 0–5000, B8 (NIR): 0–10000
    band_ranges = [(0, 3000), (0, 4000), (0, 5000), (0, 10000)]
    data = np.empty((4, size, size), dtype=np.uint16)
    for i, (lo, hi) in enumerate(band_ranges):
        data[i] = rng.integers(lo, hi, size=(size, size), dtype=np.uint16)

    # Metadata mimicking a minimal S2 L2A product
    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "width": size,
        "height": size,
        "count": 4,
        "crs": crs,
        "transform": transform,
        "tiled": True,
        "blockxsize": 16,
        "blockysize": 16,
        "compress": "lzw",
        "nodata": 0,
    }

    with rasterio.open(path, "w", **profile) as dst:
        # Band order: B2, B3, B4, B8
        band_names = ["B2", "B3", "B4", "B8"]
        for idx, name in enumerate(band_names, start=1):
            dst.write(data[idx - 1], idx)
            dst.set_band_description(idx, name)
            # S2 L2A scaling factor (reflectance = DN * 0.0001)
            dst.update_tags(idx, scale_factor=0.0001, add_offset=0.0)

        # Dataset-level tags
        dst.update_tags(
            PROCESSING_BASELINE="04.00",
            PRODUCT_TYPE="S2MSI2A",
            SENSING_TIME="2023-06-15T10:20:30Z",
            TILE_ID="T32UPU",
        )
```
```python
import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds
from datetime import datetime, timezone
import uuid

def s2_fixture(path, size=32):
    """
    Write a synthetic Sentinel-2 L2A product as a multi-band GeoTIFF.

    The file contains the four 10 m bands (B2, B3, B4, B8) in that order,
    with processing baseline 04.00, and is `size` pixels square.
    The data are uint16 scaled by 0.0001 (reflectance * 10000), with nodata=0.
    The CRS is UTM zone 31N (EPSG:32631) and the pixel size is 10 m.

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
    if size <= 0:
        raise ValueError("size must be positive")

    # Fixed parameters for a realistic Sentinel-2 L2A granule
    crs = CRS.from_epsg(32631)          # UTM zone 31N
    pixel_size = 10.0                   # 10 m resolution
    left = 500000.0                     # arbitrary westing
    top = 5000000.0                     # arbitrary northing
    right = left + size * pixel_size
    bottom = top - size * pixel_size
    transform = from_bounds(left, bottom, right, top, size, size)

    # Synthetic reflectance data (uint16, scale=0.0001)
    rng = np.random.default_rng(42)
    data = rng.integers(0, 10000, size=(4, size, size), dtype=np.uint16)
    # Make band 4 (B8, NIR) slightly brighter on average
    data[3] = np.clip(data[3] * 1.5, 0, 10000).astype(np.uint16)

    nodata = 0
    scale = 0.0001
    offset = 0.0

    # Metadata tags mimicking Sentinel-2 L2A product
    tags = {
        "SENSING_TIME": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "PROCESSING_BASELINE": "04.00",
        "SPACECRAFT_NAME": "Sentinel-2A",
        "PRODUCT_TYPE": "S2MSI2A",
        "DATATAKE_ID": str(uuid.uuid4()).upper(),
        "TILE_ID": "T31TCJ",
        "CLOUD_COVERAGE_ASSESSMENT": "0.0",
        "GENERATION_TIME": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    band_descriptions = ["B2", "B3", "B4", "B8"]

    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "width": size,
        "height": size,
        "count": 4,
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
        "compress": "lzw",
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)
        dst.update_tags(**tags)
        dst.scales = [scale] * 4
        dst.offsets = [offset] * 4
        for i, desc in enumerate(band_descriptions, start=1):
            dst.set_band_description(i, desc)

    return None
```
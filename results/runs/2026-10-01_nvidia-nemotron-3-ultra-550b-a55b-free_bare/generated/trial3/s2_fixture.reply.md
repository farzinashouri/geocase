```python
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS


def s2_fixture(path, size=32):
    """
    Write a synthetic Sentinel-2 L2A GeoTIFF fixture to `path`.

    The file contains four 10 m bands (B2, B3, B4, B8) in that order,
    with processing baseline 04.00, and is `size` pixels square.
    The data are deterministic pseudo-random reflectance values scaled by 10000.
    The CRS is UTM zone 30N (EPSG:32630) with a realistic top-left origin.
    """
    # Fixed UTM zone 30N (northern hemisphere) for reproducibility
    crs = CRS.from_epsg(32630)

    # Top-left corner (west, north) in metres – a plausible Sentinel-2 tile origin
    west = 300_000
    north = 5_400_000 + size * 10  # shift north so the tile sits in positive coordinates
    transform = from_origin(west, north, 10, 10)  # 10 m pixel size

    # Deterministic synthetic data (reflectance * 10000, uint16)
    rng = np.random.default_rng(42)
    data = np.empty((4, size, size), dtype=np.uint16)
    data[0] = rng.integers(0, 3000, size=(size, size), dtype=np.uint16)   # B2
    data[1] = rng.integers(0, 3000, size=(size, size), dtype=np.uint16)   # B3
    data[2] = rng.integers(0, 3000, size=(size, size), dtype=np.uint16)   # B4
    data[3] = rng.integers(3000, 10000, size=(size, size), dtype=np.uint16)  # B8

    band_names = ["B2", "B3", "B4", "B8"]

    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "width": size,
        "height": size,
        "count": 4,
        "crs": crs,
        "transform": transform,
        "compress": "lzw",
        "tiled": True,
        "blockxsize": min(256, size),
        "blockysize": min(256, size),
        "interleave": "band",
    }

    with rasterio.open(path, "w", **profile) as dst:
        for i in range(4):
            dst.write(data[i], i + 1)
            dst.update_tags(
                i + 1,
                STATISTICS_MINIMUM=str(data[i].min()),
                STATISTICS_MAXIMUM=str(data[i].max()),
                STATISTICS_MEAN=str(round(data[i].mean(), 2)),
                STATISTICS_STDDEV=str(round(data[i].std(), 2)),
                QUANTIFICATION_VALUE="10000",
                BAND_NAME=band_names[i],
            )
        dst.update_tags(
            PROCESSING_BASELINE="04.00",
            PRODUCT_TYPE="S2MSI2A",
            SENSOR="MSI",
            SPACECRAFT_NAME="Sentinel-2A",
            DATATAKE_ID="GS2A_20230101T000000_000000_N04.00",
            TILE_ID="T30TXP",
            UPPER_LEFT_X=str(transform.c),
            UPPER_LEFT_Y=str(transform.f),
        )
    return None
```
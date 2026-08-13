```python
import numpy as np
import rasterio
from rasterio.transform import Affine
from pathlib import Path


def s2_fixture(path, size=32):
    """
    Create a synthetic Sentinel‑2 L2A GeoTIFF with four 10 m bands (B2, B3, B4, B8).
    The file is written to *path* and is suitable for unit‑test fixtures.
    """
    path = Path(path)

    # Synthetic data: each band has a constant value
    data = np.zeros((4, size, size), dtype=np.uint16)
    data[0] = 1000  # B2
    data[1] = 2000  # B3
    data[2] = 3000  # B4
    data[3] = 4000  # B8

    # Affine transform: 10 m resolution, origin at (0, size*10)
    transform = Affine(10, 0, 0, 0, -10, size * 10)

    # Write the GeoTIFF
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        dtype="uint16",
        count=4,
        width=size,
        height=size,
        crs="EPSG:32632",
        transform=transform,
        compress="lzw",
        tiled=True,
        blockxsize=64,
        blockysize=64,
    ) as dst:
        dst.write(data)
        dst.update_tags(
            PRODUCT_TYPE="S2MSI2A",
            PROCESSING_BASELINE="04.00",
            BAND_NAMES="B2,B3,B4,B8",
            BAND_DESCRIPTIONS="Blue,Green,Red,NIR",
            CLOUD_COVER="0",
            SENSING_TIME="2023-01-01T00:00:00Z",
            DATATAKE_TIME="2023-01-01T00:00:00Z",
        )
```
import numpy as np
import rasterio
from rasterio.transform import Affine
from rasterio.crs import CRS
from pathlib import Path

def s2_fixture(path: str | Path, size: int = 32) -> None:
    """
    Create a synthetic Sentinel‑2 L2A product as a single GeoTIFF.

    Parameters
    ----------
    path : str or pathlib.Path
        Destination file path for the synthetic GeoTIFF.
    size : int, default 32
        Width and height (in pixels) of the square image.

    The resulting file contains four 10 m bands (B2, B3, B4, B8) in that
    order, uses UTM zone 32N (EPSG:32632) as CRS, and has a pixel size of
    10 m.  The file includes minimal metadata to resemble a real L2A
    granule, notably the processing baseline ``04.00`` and a product type
    tag.  Each band is filled with a deterministic pattern so that the
    output is reproducible.

    Returns
    -------
    None
    """
    path = Path(path)
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Define spatial reference and transform
    crs = CRS.from_epsg(32632)  # UTM zone 32N
    pixel_size = 10.0  # Sentinel‑2 L2A 10 m resolution
    # Top‑left corner at (0, size*pixel_size)
    transform = Affine.translation(0, size * pixel_size) * Affine.scale(pixel_size, -pixel_size)

    # Create synthetic data: each band gets a unique pattern
    data = np.empty((4, size, size), dtype=np.uint16)
    for i in range(4):
        # Simple pattern: band index * 1000 + row index * 10 + col index
        band = np.arange(size * size, dtype=np.uint16).reshape(size, size)
        band = band + i * 1000
        data[i] = band

    # Write the GeoTIFF
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=4,
        dtype=data.dtype,
        crs=crs,
        transform=transform,
        nodata=0,
        compress="deflate",
    ) as dst:
        # Write each band
        for i in range(4):
            dst.write(data[i], i + 1)
            dst.set_band_description(i + 1, f"B{i + 2}")  # B2, B3, B4, B8

        # Global tags
        dst.update_tags(
            PROCESSING_BASELINE="04.00",
            PRODUCT_TYPE="S2MSI2A",
            GRANULE_ID="T32TNR_20200101T000000_20200101T000000_B02",
        )
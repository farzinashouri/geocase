"""
Synthetic Sentinel-2 L2A fixture generator.

Provides a function to write a minimal, standards-compliant GeoTIFF that mimics
a Sentinel-2 Level-2A granule (four 10 m bands: B2, B3, B4, B8) for unit testing.
"""

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import Affine


def s2_fixture(path, size=32):
    """
    Write a synthetic Sentinel-2 L2A product to `path` as a multi-band GeoTIFF.

    The product contains the four 10 m bands (B2, B3, B4, B8) in that order,
    uses processing baseline 04.00, and is `size` pixels square. The data are
    plausible reflectance values scaled by 10000 (uint16), with a UTM zone 33N
    CRS and 10 m resolution. The file is a faithful stand-in for a real granule:
    code that reads genuine L2A products can read this file and obtain the same
    kind of answer.

    Parameters
    ----------
    path : str or pathlib.Path
        Output file path.
    size : int, optional
        Width and height of the raster in pixels (default 32).

    Returns
    -------
    None
    """
    # Fixed projection and geotransform (UTM zone 33N, 10 m pixel size)
    crs = CRS.from_epsg(32633)
    transform = Affine(10.0, 0.0, 500000.0, 0.0, -10.0, 5000000.0)

    # Reproducible synthetic data for each band (scaled reflectance * 10000)
    rng = np.random.default_rng(42)
    data = np.empty((4, size, size), dtype=np.uint16)
    # B2 (blue) - low reflectance
    data[0] = (rng.random((size, size)) * 1000 + 500).astype(np.uint16)
    # B3 (green) - medium reflectance
    data[1] = (rng.random((size, size)) * 2000 + 1000).astype(np.uint16)
    # B4 (red) - medium reflectance
    data[2] = (rng.random((size, size)) * 2000 + 1000).astype(np.uint16)
    # B8 (NIR) - high reflectance
    data[3] = (rng.random((size, size)) * 4000 + 3000).astype(np.uint16)

    # GeoTIFF profile matching Sentinel-2 L2A conventions
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

    band_names = ["B2", "B3", "B4", "B8"]
    wavelengths = {"B2": 490, "B3": 560, "B4": 665, "B8": 842}

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)
        # Band descriptions and per-band metadata
        for idx, name in enumerate(band_names, start=1):
            dst.set_band_description(idx, name)
            dst.update_tags(
                idx,
                BAND_NAME=name,
                WAVELENGTH_NM=wavelengths[name],
                RESOLUTION_M=10,
            )
        # Dataset-level metadata
        dst.update_tags(
            PROCESSING_BASELINE="04.00",
            SENSOR="MSI",
            PRODUCT_TYPE="L2A",
            BAND_ORDER=",".join(band_names),
            CRS_WKT=crs.to_wkt(),
        )

    return None


if __name__ == "__main__":
    # Module can be run directly for a quick sanity check (no side effects on import)
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        s2_fixture(tmp.name, size=64)
        print(f"Fixture written to {tmp.name}")
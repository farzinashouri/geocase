"""
Synthetic Sentinel-2 L2A fixture generator.

Creates a minimal but structurally faithful GeoTIFF that mimics a real
Sentinel-2 Level-2A 10 m granule (bands B2, B3, B4, B8 in that order).
"""

from __future__ import annotations

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin


def s2_fixture(path: str, size: int = 32) -> None:
    """
    Write a synthetic Sentinel-2 L2A product to *path*.

    Parameters
    ----------
    path : str
        Output GeoTIFF path.
    size : int, default 32
        Width and height of the image in pixels (10 m resolution).

    Returns
    -------
    None
    """
    # ------------------------------------------------------------------
    # Fixed metadata that mimics a real S2A_MSIL2A granule (baseline 04.00)
    # ------------------------------------------------------------------
    crs = CRS.from_epsg(32631)                 # UTM zone 31N (arbitrary but valid)
    transform = from_origin(300_000.0, 5_000_000.0, 10.0, 10.0)  # 10 m pixels
    dtype = "uint16"
    nodata = 0
    count = 4                                   # B2, B3, B4, B8
    band_names = ("B2", "B3", "B4", "B8")
    band_descriptions = (
        "Band 2 - Blue (490 nm)",
        "Band 3 - Green (560 nm)",
        "Band 4 - Red (665 nm)",
        "Band 8 - NIR (842 nm)",
    )

    # ------------------------------------------------------------------
    # Synthetic data: each band gets a distinct constant so that unit tests
    # can verify band order and values without relying on randomness.
    # Values are in the typical L2A range (0–10000 after scaling by 10000).
    # ------------------------------------------------------------------
    data = np.empty((count, size, size), dtype=dtype)
    data[0] = 1000   # B2
    data[1] = 2000   # B3
    data[2] = 3000   # B4
    data[3] = 4000   # B8

    # ------------------------------------------------------------------
    # Write GeoTIFF with Sentinel-2-like tags
    # ------------------------------------------------------------------
    profile = {
        "driver": "GTiff",
        "dtype": dtype,
        "nodata": nodata,
        "width": size,
        "height": size,
        "count": count,
        "crs": crs,
        "transform": transform,
        "tiled": True,
        "blockxsize": 128,
        "blockysize": 128,
        "compress": "lzw",
        "interleave": "band",
    }

    with rasterio.open(path, "w", **profile) as dst:
        # Band-level metadata
        for idx, (name, desc) in enumerate(zip(band_names, band_descriptions), start=1):
            dst.set_band_description(idx, desc)
            dst.update_tags(idx, band_name=name)

        # Dataset-level metadata (mimics S2 L2A user product metadata)
        dst.update_tags(
            AREA_OR_POINT="Area",
            PROCESSING_BASELINE="04.00",
            PRODUCT_TYPE="S2MSI2A",
            SENSOR="MSI",
            SPACECRAFT_NAME="Sentinel-2A",
            DATATAKE_ID="GS2A_20240101T000000_000000_N04.00",
            GENERATION_TIME="2024-01-01T00:00:00.000Z",
        )

        dst.write(data)
```python
"""Synthetic Sentinel-2 L2A GeoTIFF fixture generator for unit tests."""

from __future__ import annotations

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

# Order matches real Sentinel-2 L2A 10 m stacks: B02 (blue), B03 (green),
# B04 (red), B08 (NIR).
_BAND_NAMES = ("B02", "B03", "B04", "B08")
_PIXEL_SIZE_M = 10.0
_PROCESSING_BASELINE = "04.00"
# BOA reflectance is stored as UInt16 with a quantification value of 10000
# (reflectance * 10000), 0 reserved as NODATA, per the L2A product spec.
_BOA_QUANTIFICATION_VALUE = 10000
_NODATA = 0


def s2_fixture(path, size=32):
    """Write a small synthetic Sentinel-2 L2A GeoTIFF to ``path``.

    The product contains the four 10 m bands (B02, B03, B04, B08), in that
    order, tagged with processing baseline 04.00, so code written against a
    real granule can read it and get plausible-looking results.
    """
    rng = np.random.default_rng(0)

    # Simple per-band reflectance stats (in BOA units, 0-10000) roughly in
    # line with vegetated/mixed land cover, so band ratios (e.g. NDVI) come
    # out sane rather than pure noise.
    band_means = {"B02": 900, "B03": 1100, "B04": 1000, "B08": 2800}
    band_stds = {"B02": 150, "B03": 180, "B04": 200, "B08": 400}

    data = np.empty((len(_BAND_NAMES), size, size), dtype=np.uint16)
    for i, band in enumerate(_BAND_NAMES):
        values = rng.normal(band_means[band], band_stds[band], size=(size, size))
        values = np.clip(values, 1, _BOA_QUANTIFICATION_VALUE - 1)
        data[i] = values.astype(np.uint16)

    # Arbitrary but realistic UTM grid, aligned to the 10 m Sentinel-2 tiling
    # grid origin convention (upper-left corner, north-up).
    crs = CRS.from_epsg(32633)
    transform = from_origin(499980.0, 5900040.0, _PIXEL_SIZE_M, _PIXEL_SIZE_M)

    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "nodata": _NODATA,
        "width": size,
        "height": size,
        "count": len(_BAND_NAMES),
        "crs": crs,
        "transform": transform,
        "compress": "deflate",
    }

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)
        for i, band in enumerate(_BAND_NAMES, start=1):
            dst.set_band_description(i, band)
        dst.update_tags(
            PROCESSING_BASELINE=_PROCESSING_BASELINE,
            PRODUCT_TYPE="S2MSI2A",
            SPACECRAFT_NAME="Sentinel-2A",
            BOA_QUANTIFICATION_VALUE=str(_BOA_QUANTIFICATION_VALUE),
        )

    return None
```
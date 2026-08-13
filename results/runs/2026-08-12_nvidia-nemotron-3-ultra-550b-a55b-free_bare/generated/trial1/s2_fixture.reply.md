```python
"""
Synthetic Sentinel-2 L2A fixture generator.

Provides a function `s2_fixture` that writes a minimal but faithful
GeoTIFF stand-in for a Sentinel-2 Level-2A granule containing the four
10 m bands (B2, B3, B4, B8) in that order.
"""

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import Affine


def s2_fixture(path, size=32):
    """
    Write a synthetic Sentinel-2 L2A product to `path` as a GeoTIFF.

    The product contains four 10 m bands (B2, B3, B4, B8) in that band
    order, at processing baseline 04.00, and is `size` pixels square.
    The file is a faithful stand-in for a real granule: code that reads
    a genuine L2A product should be able to read this file and get the
    same kind of answer.

    Parameters
    ----------
    path : str or Path
        Output file path.
    size : int, optional
        Width and height of the image in pixels (default 32).

    Returns
    -------
    None
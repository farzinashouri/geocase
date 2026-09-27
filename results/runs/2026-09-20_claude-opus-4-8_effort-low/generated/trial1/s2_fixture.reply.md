```python
"""Synthetic Sentinel-2 L2A GeoTIFF fixture for unit tests.

Importing this module has no side effects.
"""

import numpy as np
import rasterio
from rasterio.transform import from_origin


# Processing baseline 04.00 (and later) applies a radiometric BOA offset:
# surface reflectance = (DN - BOA_ADD_OFFSET) / QUANTIFICATION_VALUE.
# For baseline >= 04.00 the offset is -1000 and the quantification value is
# 10000, so DN = reflectance * 10000 + 1000. A faithful stand-in must encode
# this offset, otherwise a reader that subtracts it would get wrong reflectance.
_BOA_ADD_OFFSET = -1000
_QUANTIFICATION_VALUE = 10000
_BANDS = ("B2", "B3", "B4", "B8")  # the four 10 m bands, in this order
_NODATA = 0


def s2_fixture(path, size=32):
    """Write a small synthetic Sentinel-2 L2A product to ``path``.

    The GeoTIFF has four uint16 bands (B2, B3, B4, B8 at 10 m), processing
    baseline 04.00, and is ``size`` pixels square. Returns ``None``.
    """
    # Plausible surface reflectances (0..1) for each band, with a gentle
    # spatial gradient so the raster is not uniform.
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    grad = (xx + yy) / max(2 * (size - 1), 1)  # 0..1 across the diagonal

    base_reflectance = {
        "B2": 0.08,   # blue
        "B3": 0.11,   # green
        "B4": 0.10,   # red
        "B8": 0.32,   # NIR (vegetation-like, high)
    }

    dns = np.empty((len(_BANDS), size, size), dtype=np.uint16)
    for i, band in enumerate(_BANDS):
        refl = base_reflectance[band] * (0.75 + 0.5 * grad)
        # Encode with the baseline 04.00 offset: DN = refl * QV + 1000.
        dn = refl * _QUANTIFICATION_VALUE - _BOA_ADD_OFFSET
        dn = np.clip(np.rint(dn), 1, 65535)  # keep off the 0 nodata value
        dns[i] = dn.astype(np.uint16)

    # A real granule is in a UTM projection at 10 m resolution.
    crs = rasterio.crs.CRS.from_epsg(32631)  # UTM zone 31N
    resolution = 10.0
    transform = from_origin(300000.0, 5100000.0, resolution, resolution)

    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "count": len(_BANDS),
        "height": size,
        "width": size,
        "crs": crs,
        "transform": transform,
        "nodata": _NODATA,
    }

    tags = {
        "PROCESSING_BASELINE": "04.00",
        "BOA_ADD_OFFSET": str(_BOA_ADD_OFFSET),
        "QUANTIFICATION_VALUE": str(_QUANTIFICATION_VALUE),
    }

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(dns)
        dst.update_tags(**tags)
        for i, band in enumerate(_BANDS, start=1):
            dst.set_band_description(i, band)
            dst.update_tags(i, BOA_ADD_OFFSET=str(_BOA_ADD_OFFSET))

    return None
```
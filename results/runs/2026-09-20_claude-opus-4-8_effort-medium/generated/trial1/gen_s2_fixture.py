"""Synthetic Sentinel-2 L2A fixture writer.

Creates a small GeoTIFF that stands in for a real Sentinel-2 Level-2A
granule: four 10 m bands (B2, B3, B4, B8, in that order), stored as
uint16 digital numbers at processing baseline 04.00.

Baseline 04.00 introduced the ``BOA_ADD_OFFSET`` of -1000: surface
reflectance is recovered as ``(DN - 1000) / 10000``. That offset is
encoded here both in the pixel values and in the per-band scale/offset
tags, so a reader that handles a genuine baseline-04.00 product will
recover the same reflectances from this fixture.

Importing this module has no side effects.
"""

import numpy as np
import rasterio
from rasterio.transform import from_origin

# Sentinel-2 10 m bands, in the required band order.
BANDS = ("B2", "B3", "B4", "B8")

# Baseline 04.00 radiometric convention.
PROCESSING_BASELINE = "04.00"
BOA_ADD_OFFSET = -1000          # DN offset introduced at baseline 04.00
QUANTIFICATION_VALUE = 10000    # DN per unit reflectance
NODATA = 0                      # Sentinel-2 uses 0 for no-data / saturated

# Reflectance -> DN:  DN = reflectance * QUANTIFICATION_VALUE - BOA_ADD_OFFSET
_SCALE = 1.0 / QUANTIFICATION_VALUE          # DN -> reflectance multiplier
_OFFSET = BOA_ADD_OFFSET / QUANTIFICATION_VALUE  # DN -> reflectance addend (-0.1)


def s2_fixture(path, size=32):
    """Write a synthetic Sentinel-2 L2A GeoTIFF to ``path``.

    The product is ``size`` pixels square, covers bands B2, B3, B4, B8 at
    10 m resolution, and is stored as uint16 DNs at processing baseline
    04.00 (surface reflectance = ``(DN - 1000) / 10000``).

    Returns ``None``.
    """
    size = int(size)
    if size <= 0:
        raise ValueError("size must be a positive integer")

    # A plausible UTM tile: 10 m pixels, origin on a granule-aligned corner.
    # UTM zone 31N (EPSG:32631), a typical Sentinel-2 tile CRS.
    crs = rasterio.crs.CRS.from_epsg(32631)
    res = 10.0
    x_origin = 600000.0      # 100 km-aligned easting
    y_origin = 4900000.0     # northing (top-left corner)
    transform = from_origin(x_origin, y_origin, res, res)

    # Synthetic, deterministic reflectance per band, in the physical range
    # of a real L2A scene (roughly 0.0-0.4). A smooth gradient plus a
    # per-band base level keeps values distinct and readable.
    rows = np.linspace(0.0, 1.0, size, dtype=np.float64)[:, None]
    cols = np.linspace(0.0, 1.0, size, dtype=np.float64)[None, :]
    base = {"B2": 0.06, "B3": 0.09, "B4": 0.11, "B8": 0.28}

    data = np.empty((len(BANDS), size, size), dtype=np.uint16)
    for i, band in enumerate(BANDS):
        reflectance = base[band] + 0.10 * rows + 0.05 * cols
        # Encode reflectance as baseline-04.00 DN, avoiding the nodata value.
        dn = np.rint(reflectance * QUANTIFICATION_VALUE - BOA_ADD_OFFSET)
        dn = np.clip(dn, 1, np.iinfo(np.uint16).max)
        data[i] = dn.astype(np.uint16)

    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "count": len(BANDS),
        "height": size,
        "width": size,
        "crs": crs,
        "transform": transform,
        "nodata": NODATA,
        "tiled": False,
    }

    with rasterio.open(path, "w", **profile) as dst:
        for i, band in enumerate(BANDS, start=1):
            dst.write(data[i - 1], i)
            dst.set_band_description(i, band)
            # Per-band DN -> reflectance mapping (baseline 04.00).
            dst.scales = tuple(_SCALE for _ in BANDS)
            dst.offsets = tuple(_OFFSET for _ in BANDS)

        dst.update_tags(
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            PRODUCT_TYPE="S2MSI2A",
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            BOA_QUANTIFICATION_VALUE=str(QUANTIFICATION_VALUE),
        )
        for i, band in enumerate(BANDS, start=1):
            dst.update_tags(
                i,
                BANDNAME=band,
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            )

    return None
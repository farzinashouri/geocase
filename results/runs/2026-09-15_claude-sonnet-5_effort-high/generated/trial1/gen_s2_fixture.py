"""Synthetic Sentinel-2 L2A GeoTIFF fixture generator for unit tests."""

from __future__ import annotations

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

# Band order for the four native 10 m bands of a Sentinel-2 L2A product.
_BANDS = ("B02", "B03", "B04", "B08")
_WAVELENGTHS_NM = {"B02": 492.4, "B03": 559.8, "B04": 664.6, "B08": 832.8}

# Approximate bottom-of-atmosphere reflectance (scaled by 10000, per the
# official BOA_QUANTIFICATION_VALUE) for a handful of plausible land-cover
# classes. Order matches _BANDS.
_CLASS_REFLECTANCE = {
    "water": (800, 600, 400, 200),
    "vegetation": (400, 650, 300, 4000),
    "soil": (1500, 1700, 2000, 2500),
    "cloud": (9000, 9200, 9300, 9100),
}


def s2_fixture(path, size: int = 32) -> None:
    """Write a synthetic Sentinel-2 L2A product to ``path`` as a GeoTIFF.

    The product has four 10 m bands (B02, B03, B04, B08, in that order),
    is ``size`` pixels square, and carries processing baseline 04.00
    metadata, so that code written against real L2A granules can read it
    and get plausible answers.
    """
    rng = np.random.default_rng(42)

    # Build a small Voronoi-style land-cover map so the scene has spatial
    # structure (patches) rather than pure per-pixel noise.
    class_names = list(_CLASS_REFLECTANCE.keys())
    n_centers = len(class_names)
    centers = rng.uniform(0, size, size=(n_centers, 2))
    rows, cols = np.meshgrid(np.arange(size), np.arange(size), indexing="ij")
    coords = np.stack([rows, cols], axis=-1).astype(np.float64)
    dists = np.stack(
        [np.hypot(coords[..., 0] - cy, coords[..., 1] - cx) for cy, cx in centers],
        axis=-1,
    )
    class_map = np.argmin(dists, axis=-1)

    data = np.zeros((len(_BANDS), size, size), dtype=np.float64)
    for class_idx, name in enumerate(class_names):
        mask = class_map == class_idx
        base = _CLASS_REFLECTANCE[name]
        for band_idx, value in enumerate(base):
            noise = rng.normal(loc=0.0, scale=150.0, size=mask.sum())
            data[band_idx][mask] = value + noise

    data = np.clip(data, 1, 10000).astype(np.uint16)

    # A realistic UTM tile origin/CRS, as used by real S2 MGRS tiles.
    transform = from_origin(399960.0, 4700040.0, 10, 10)
    crs = CRS.from_epsg(32633)

    profile = {
        "driver": "GTiff",
        "height": size,
        "width": size,
        "count": len(_BANDS),
        "dtype": "uint16",
        "crs": crs,
        "transform": transform,
        "nodata": 0,
    }

    with rasterio.open(path, "w", **profile) as dst:
        dst.update_tags(
            PROCESSING_BASELINE="04.00",
            PRODUCT_TYPE="S2MSI2A",
            SPACECRAFT_NAME="Sentinel-2A",
            BOA_QUANTIFICATION_VALUE="10000",
        )
        dst.scales = tuple(0.0001 for _ in _BANDS)
        for i, band in enumerate(_BANDS, start=1):
            dst.write(data[i - 1], i)
            dst.set_band_description(i, band)
            dst.update_tags(i, BANDNAME=band, WAVELENGTH_NM=str(_WAVELENGTHS_NM[band]))
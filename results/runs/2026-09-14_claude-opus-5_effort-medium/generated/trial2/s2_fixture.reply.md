```python
"""Synthetic Sentinel-2 L2A test fixture.

Writes a tiny four-band (10 m) L2A granule as a GeoTIFF that behaves like the
real thing for the purposes of reader code:

* band order B2, B3, B4, B8 (the four 10 m bands), uint16;
* processing baseline 04.00, which means the DNs carry BOA_ADD_OFFSET = -1000:
  surface reflectance = (DN + BOA_ADD_OFFSET) / QUANTIFICATION_VALUE
                      = (DN - 1000) / 10000;
* 0 is NODATA, and the granule has a clipped corner of it, as real tiles do;
* a UTM CRS with a 10 m pixel grid aligned to a multiple of 10 m.

The pixel values are therefore *not* reflectance * 10000: code that forgets the
baseline-04.00 offset will read this file and get the same wrong answer it would
get from a genuine granule, which is the point of a fixture.

No scale/offset is written into the GeoTIFF band metadata on purpose: real L2A
JP2s do not carry one either (the offset lives in MTD_MSIL2A.xml), and writing
one would let a reader accidentally pass a test it should fail.

Importing this module has no side effects.
"""

from __future__ import annotations

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

__all__ = ["s2_fixture"]

# --- Product constants (baseline 04.00) -------------------------------------

PROCESSING_BASELINE = "04.00"
QUANTIFICATION_VALUE = 10000
BOA_ADD_OFFSET = -1000
NODATA = 0

#: Band order of the written file, with ESA band ids and central wavelengths (nm).
BANDS = (
    ("B02", "blue", 492.4),
    ("B03", "green", 559.8),
    ("B04", "red", 664.6),
    ("B08", "nir", 832.8),
)

# Nominal 10 m granule geometry: UTM zone 31N, origin on the 10 m grid.
EPSG = 32631
PIXEL_SIZE = 10.0
ORIGIN_X = 600000.0
ORIGIN_Y = 4900000.0

# Plausible surface reflectances per land-cover class, in BANDS order.
_CLASS_REFLECTANCE = {
    "vegetation": (0.030, 0.060, 0.035, 0.320),
    "soil": (0.090, 0.130, 0.180, 0.270),
    "water": (0.060, 0.045, 0.030, 0.012),
}

_NOISE_REFLECTANCE = 0.004  # per-pixel speckle, in reflectance units
_SEED = 20220125  # baseline 04.00 cut-over date; any fixed value would do


def _class_map(size):
    """Return an integer map of land-cover classes, deterministic in `size`.

    Three classes so that band ratios (NDVI, NDWI, ...) come out with the right
    signs: a water body bottom-left, a soil field top-right, vegetation around.
    """
    rows, cols = np.mgrid[0:size, 0:size]
    frow = (rows + 0.5) / size
    fcol = (cols + 0.5) / size

    classes = np.zeros((size, size), dtype=np.uint8)  # 0 = vegetation
    soil = (frow < 0.45) & (fcol > 0.55)
    water = ((frow - 0.75) ** 2 + (fcol - 0.28) ** 2) < 0.20**2
    classes[soil] = 1
    classes[water] = 2
    return classes


def _nodata_mask(size):
    """A clipped corner of NODATA, like the edge of a real granule/orbit swath."""
    rows, cols = np.mgrid[0:size, 0:size]
    return (rows + cols) < max(1, size // 8)


def s2_fixture(path, size=32):
    """Write a synthetic Sentinel-2 L2A product to `path` as a GeoTIFF.

    Parameters
    ----------
    path : str or os.PathLike
        Destination file. Overwritten if it exists.
    size : int
        Width and height of the product in pixels (10 m each). Must be >= 1.

    Returns
    -------
    None
    """
    size = int(size)
    if size < 1:
        raise ValueError(f"size must be >= 1, got {size}")

    classes = _class_map(size)
    nodata = _nodata_mask(size)
    rng = np.random.default_rng(_SEED)

    data = np.empty((len(BANDS), size, size), dtype=np.uint16)
    for b, (band_id, _alias, _wavelength) in enumerate(BANDS):
        reflectance = np.empty((size, size), dtype=np.float64)
        for class_index, name in enumerate(("vegetation", "soil", "water")):
            reflectance[classes == class_index] = _CLASS_REFLECTANCE[name][b]
        reflectance += rng.uniform(
            -_NOISE_REFLECTANCE, _NOISE_REFLECTANCE, size=(size, size)
        )

        # Invert the baseline-04.00 convention to get the stored DNs.
        dn = np.rint(reflectance * QUANTIFICATION_VALUE - BOA_ADD_OFFSET)
        # Keep valid pixels off the NODATA value so the mask stays meaningful.
        dn = np.clip(dn, 1, np.iinfo(np.uint16).max)
        dn[nodata] = NODATA
        data[b] = dn.astype(np.uint16)

    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "count": len(BANDS),
        "width": size,
        "height": size,
        "crs": CRS.from_epsg(EPSG),
        "transform": from_origin(ORIGIN_X, ORIGIN_Y, PIXEL_SIZE, PIXEL_SIZE),
        "nodata": NODATA,
        "compress": "deflate",
        "interleave": "pixel",
    }

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)
        dst.update_tags(
            AREA_OR_POINT="Area",
            PRODUCT_TYPE="S2MSI2A",
            PROCESSING_LEVEL="Level-2A",
            PROCESSING_BASELINE=PROCESSING_BASELINE,
            SPACECRAFT_NAME="Sentinel-2A",
            QUANTIFICATION_VALUE=str(QUANTIFICATION_VALUE),
            BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            BOA_QUANTIFICATION_VALUE=str(QUANTIFICATION_VALUE),
            SPATIAL_RESOLUTION="10",
            MGRS_TILE="31UDQ",
            PRODUCT_URI=(
                "S2A_MSIL2A_20220601T104631_N0400_R051_T31UDQ_20220601T134623.SAFE"
            ),
            SENSING_TIME="2022-06-01T10:46:31.024Z",
        )
        for index, (band_id, alias, wavelength) in enumerate(BANDS, start=1):
            dst.set_band_description(index, band_id)
            dst.update_tags(
                index,
                BANDNAME=band_id,
                ALIAS=alias,
                CENTRAL_WAVELENGTH_NM=f"{wavelength}",
                BOA_ADD_OFFSET=str(BOA_ADD_OFFSET),
            )

    return None
```
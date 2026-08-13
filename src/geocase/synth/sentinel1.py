"""Spec-accurate synthetic Sentinel-1 GRD products at unit-test scale.

The default output is faithful to what a GRD measurement file actually
stores — detected amplitude as uint16 DNs (witness: ``pixelValue=Detected``,
``outputPixels=16 bit Unsigned Integer``), zero-valued at the image border,
with no dB anywhere. ``units="linear"`` and ``units="dB"`` produce the
*calibrated derivatives* (sigma0) a processing chain computes from those DNs;
they are float32 and are not what ESA ships.

Deliberate deviation, documented rather than hidden: real GRD measurement
files are georeferenced by GCPs and carry no CRS/transform. These fixtures
keep the corpus's projected UTM grid so every bundled loader and assertion
works unchanged; GCP georeferencing is out of Plan 18's scope.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from geocase.synth.spec import (
    S1_GRD_DTYPE,
    S1_GRD_PIXEL_VALUE,
    S1_GRD_PRODUCT_TYPE,
    S1_IW_GRDH_PIXEL_SPACING_M,
)

_CRS = "EPSG:32633"
_ORIGIN = (500_000.0, 4_500_000.0)

#: Typical IW GRDH land amplitudes are a few hundred DN.
_AMPLITUDE_BASE = {"VV": 220.0, "VH": 90.0}


def _amplitude(size: int, pol: str) -> np.ndarray:
    """Deterministic detected-amplitude DNs for one polarisation."""
    rows = np.arange(size).reshape(-1, 1)
    cols = np.arange(size).reshape(1, -1)
    ripple = ((rows * 7 + cols * 11) % 97) / 97.0  # [0, 1)
    return _AMPLITUDE_BASE[pol] * (0.5 + ripple)


def sentinel1_grd(
    path: str | Path,
    size: int = 32,
    pol: str = "VV+VH",
    units: str = "amplitude",
    border_noise: bool = False,
) -> Path:
    """Write a synthetic Sentinel-1 IW GRDH product to *path* as a GeoTIFF.

    ``pol`` is ``"VV"``, ``"VH"`` or ``"VV+VH"``. ``units="amplitude"``
    (default) writes uint16 detected-amplitude DNs as a real GRD does;
    ``"linear"`` writes float32 sigma0, ``"dB"`` writes float32
    10*log10(sigma0). ``border_noise=True`` zeroes the leading columns, the
    unfiltered-border-noise signature every real GRD carries at scene edges.
    """
    path = Path(path)
    pols = tuple(pol.split("+"))
    unknown = set(pols) - set(_AMPLITUDE_BASE)
    if unknown or units not in {"amplitude", "linear", "dB"}:
        raise ValueError(f"unsupported pol={pol!r} or units={units!r}")

    bands = []
    for p in pols:
        amp = _amplitude(size, p)
        if units == "amplitude":
            band = np.round(amp).astype(S1_GRD_DTYPE)
        else:
            # Calibrated sigma0 = DN^2 / A^2 with a flat calibration constant,
            # scaled so land values sit in a realistic range (~ -20..0 dB).
            sigma0 = (amp / _AMPLITUDE_BASE["VV"]) ** 2 * 0.25
            band = ((10.0 * np.log10(sigma0)) if units == "dB" else sigma0).astype(
                "float32"
            )
        bands.append(band)
    stack = np.stack(bands)

    nodata = 0 if units == "amplitude" else None
    if border_noise:
        stack[:, :, :2] = 0

    spacing = S1_IW_GRDH_PIXEL_SPACING_M
    profile: dict = {
        "driver": "GTiff",
        "height": size,
        "width": size,
        "count": len(pols),
        "dtype": stack.dtype.name,
        "crs": _CRS,
        "transform": from_origin(*_ORIGIN, spacing, spacing),
        "compress": "deflate",
    }
    if nodata is not None:
        profile["nodata"] = nodata
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(stack)
        for idx, p in enumerate(pols, start=1):
            dst.set_band_description(idx, p)
            dst.update_tags(idx, POLARISATION=p)
        dst.update_tags(
            PRODUCT_TYPE=S1_GRD_PRODUCT_TYPE,
            MODE="IW",
            PIXEL_VALUE=S1_GRD_PIXEL_VALUE if units == "amplitude" else units,
            UNITS=units,
        )
    return path

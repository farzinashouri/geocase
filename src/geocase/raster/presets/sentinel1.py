"""Spec-accurate synthetic Sentinel-1 GRD products, as a preset.

**Frozen.** Ported from ``geocase.synth.sentinel1`` and deliberately not
extended: three evaluated codebases treat SAR as dead weight, and the one
compute-side adopter ranks the ML-EO tables (foundation-model normalisation
statistics, cloud-mask conventions) ahead of it. It stays because the facts are
already witnessed and correct, not because it is where the next work goes.

The default output is faithful to what a GRD measurement file actually stores —
detected amplitude as uint16 DNs, zero-valued at the image border, with no dB
anywhere. ``units="linear"`` and ``units="dB"`` produce the *calibrated
derivatives* (sigma0) a processing chain computes from those DNs; they are
float32 and are not what ESA ships.

Deliberate deviation, documented rather than hidden: real GRD measurement files
are georeferenced by GCPs and carry no CRS/transform. These fixtures keep a
projected UTM grid so ordinary readers work unchanged; GCP georeferencing is out
of scope.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from geospatial_spec.sentinel1 import explain, pixel_spacing_m, pixel_value_convention

from geocase.raster.primitive import DEFAULT_SIZE, FixtureSpec, raster_fixture

__all__ = ["sentinel1_grd"]

_CRS = "EPSG:32633"
_ORIGIN = (500_000.0, 4_500_000.0)

_DTYPE: str = explain("dtype").value
_PRODUCT_TYPE: str = explain("product_type").value

#: Typical IW GRDH land amplitudes are a few hundred DN.
_AMPLITUDE_BASE = {"VV": 220.0, "VH": 90.0}


def _amplitude(size: int, pol: str) -> np.ndarray:
    """Deterministic detected-amplitude DNs for one polarisation."""
    rows = np.arange(size).reshape(-1, 1)
    cols = np.arange(size).reshape(1, -1)
    ripple = ((rows * 7 + cols * 11) % 97) / 97.0  # [0, 1)
    return _AMPLITUDE_BASE[pol] * (0.5 + ripple)


def sentinel1_grd(
    path: str | Path | None = None,
    size: int = DEFAULT_SIZE,
    pol: str = "VV+VH",
    units: str = "amplitude",
    border_noise: bool | int = False,
) -> FixtureSpec | Path:
    """Build a synthetic Sentinel-1 IW GRDH product.

    Args:
        path: Where to write a GeoTIFF. **If omitted, returns the
            :class:`FixtureSpec` instead of writing.**
        size: Edge length in pixels. Defaults to 256.
        pol: ``"VV"``, ``"VH"`` or ``"VV+VH"``.
        units: ``"amplitude"`` (default) writes uint16 detected-amplitude DNs as
            a real GRD does; ``"linear"`` writes float32 sigma0; ``"dB"`` writes
            float32 10*log10(sigma0). Only ``"amplitude"`` is what ESA ships.
        border_noise: Width in pixels of the zeroed border every real GRD
            carries at scene edges, or ``True`` for 2 px.

    Returns:
        The written :class:`~pathlib.Path` if *path* was given, otherwise the
        :class:`~geocase.raster.FixtureSpec`.
    """
    pols = tuple(pol.split("+"))
    unknown = set(pols) - set(_AMPLITUDE_BASE)
    if unknown or units not in {"amplitude", "linear", "dB"}:
        raise ValueError(f"unsupported pol={pol!r} or units={units!r}")

    border = 2 if border_noise is True else int(border_noise or 0)

    bands = []
    for p in pols:
        amp = _amplitude(size, p)
        if units == "amplitude":
            band = np.round(amp).astype(_DTYPE)
        else:
            # Calibrated sigma0 = DN^2 / A^2 with a flat calibration constant,
            # scaled so land values sit in a realistic range (~ -20..0 dB).
            sigma0 = (amp / _AMPLITUDE_BASE["VV"]) ** 2 * 0.25
            band = ((10.0 * np.log10(sigma0)) if units == "dB" else sigma0).astype(
                "float32"
            )
        bands.append(band)
    stack = np.stack(bands)

    # Only the stored-DN form has a meaningful nodata sentinel; the calibrated
    # derivatives are floats where 0 is a legitimate value.
    nodata = 0 if units == "amplitude" else None
    spacing = pixel_spacing_m(mode="IW", resolution="GRDH")

    spec = raster_fixture(
        bands=len(pols),
        dtype=stack.dtype.name,
        size=size,
        crs=_CRS,
        origin=_ORIGIN,
        resolution=spacing,
        nodata=nodata,
        values=stack,
        band_descriptions=pols,
        band_tags=tuple({"POLARISATION": p} for p in pols),
        tags={
            "PRODUCT_TYPE": _PRODUCT_TYPE,
            "MODE": "IW",
            "PIXEL_VALUE": (
                pixel_value_convention(product_type="GRD")
                if units == "amplitude"
                else units
            ),
            "UNITS": units,
        },
    )

    if border:
        # Leading columns only, not a full frame: GRD border noise is a
        # range-edge artifact of the unfiltered swath margin, so a four-sided
        # frame would misrepresent where it actually occurs. Applied after
        # construction because the border is zero regardless of whether a
        # nodata sentinel is declared — for the float units it is genuinely
        # undeclared, which is what a real GRD looks like.
        spec.array[:, :, :border] = 0

    return spec if path is None else spec.write(path)

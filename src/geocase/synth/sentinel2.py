"""Spec-accurate synthetic Sentinel-2 L2A products at unit-test scale.

The generator exists because the useful axes (baseline, band set, nodata
border, SCL sidecar) are combinatorial — static files cannot span them — and
because its correctness lives in one audited place: every radiometric fact
comes from :mod:`geocase.synth.spec`, which is machine-checked against a real
granule's metadata by ``tests/synth/test_spec_fidelity.py``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from geocase.synth.spec import (
    S2_BAND_RESOLUTION_M,
    S2_BANDS_10M,
    S2_BOA_ADD_OFFSET,
    S2_BOA_QUANTIFICATION_VALUE,
    S2_DTYPE,
    S2_NODATA,
    S2_SCL_CLASSES,
    S2_SCL_RESOLUTION_M,
    baseline_has_offset,
)

# Matches the corpus's shared synthetic grid (see
# scripts/generate_raster_fixtures.py): UTM 33N, 10 m pixels.
_CRS = "EPSG:32633"
_ORIGIN = (500_000.0, 4_500_000.0)


def _native_resolution(band: str) -> int:
    """Native resolution of a zero-padded or witness-form band name."""
    if band in S2_BAND_RESOLUTION_M:
        return S2_BAND_RESOLUTION_M[band]
    # Zero-padded filename form ("B04") -> witness form ("B4").
    return S2_BAND_RESOLUTION_M["B" + band[1:].lstrip("0")]


def _reflectance(size: int, seed: int) -> np.ndarray:
    """Deterministic surface reflectance in [0.02, 0.62)."""
    rows = np.arange(size).reshape(-1, 1)
    cols = np.arange(size).reshape(1, -1)
    ramp = ((rows * 3 + cols * 5 + seed * 17) % 60) / 100.0
    return ramp + 0.02


def _dn(reflectance: np.ndarray, baseline: str) -> np.ndarray:
    """Encode reflectance as L2A DNs for *baseline*.

    Baseline >= 04.00: DN = reflectance * 10000 - BOA_ADD_OFFSET, so that
    reflectance = (DN + BOA_ADD_OFFSET) / 10000. Earlier baselines carry no
    offset (plan trap 3): DN = reflectance * 10000.
    """
    dn = reflectance * S2_BOA_QUANTIFICATION_VALUE
    if baseline_has_offset(baseline):
        dn = dn - S2_BOA_ADD_OFFSET
    return np.round(dn).astype(S2_DTYPE)


def sentinel2_l2a(
    path: str | Path,
    size: int = 32,
    bands: tuple[str, ...] = S2_BANDS_10M,
    baseline: str = "04.00",
    nodata_border: bool = False,
    scl: bool = False,
) -> Path:
    """Write a synthetic Sentinel-2 L2A band stack to *path* as a GeoTIFF.

    All bands are written on the 10 m grid, as real L2A resampled stacks are;
    a band whose native resolution is 20 m gets its values block-replicated
    from a size/2 grid, so the upsampled-from-20 m structure (and therefore a
    genuine resolution mismatch for anything treating it as 10 m-native
    information) is present in the pixels, not just claimed in metadata.

    ``scl=True`` writes the Scene Classification sidecar next to *path* as
    ``<stem>_SCL.tif`` — uint8 at 20 m, as in a real granule.
    """
    path = Path(path)
    arrays = []
    for i, band in enumerate(bands):
        if _native_resolution(band) >= 20:
            coarse = _reflectance(size // 2, seed=i)
            refl = np.repeat(np.repeat(coarse, 2, axis=0), 2, axis=1)
        else:
            refl = _reflectance(size, seed=i)
        arrays.append(_dn(refl, baseline))
    stack = np.stack(arrays)

    if nodata_border:
        stack[:, :, :2] = S2_NODATA

    offset_present = baseline_has_offset(baseline)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=len(bands),
        dtype=S2_DTYPE,
        crs=_CRS,
        transform=from_origin(*_ORIGIN, 10.0, 10.0),
        nodata=S2_NODATA,
        compress="deflate",
    ) as dst:
        dst.write(stack)
        for idx, band in enumerate(bands, start=1):
            dst.set_band_description(idx, band)
            dst.update_tags(idx, NATIVE_RESOLUTION_M=str(_native_resolution(band)))
        # GDAL's convention is value = raw * scale + offset, so the
        # self-consistent band form of (DN - 1000) / 10000 is scale 1e-4 with
        # the offset expressed in the scaled unit: -0.1.
        quant = float(S2_BOA_QUANTIFICATION_VALUE)
        dst.scales = (1.0 / quant,) * len(bands)
        dst.offsets = ((S2_BOA_ADD_OFFSET / quant if offset_present else 0.0),) * len(
            bands
        )
        tags = {
            "PROCESSING_BASELINE": baseline,
            "QUANTIFICATION_VALUE": str(S2_BOA_QUANTIFICATION_VALUE),
            "BOA_QUANTIFICATION_VALUE": str(S2_BOA_QUANTIFICATION_VALUE),
        }
        if offset_present:
            tags["BOA_ADD_OFFSET"] = str(S2_BOA_ADD_OFFSET)
        dst.update_tags(**tags)

    if scl:
        _write_scl(path.with_name(f"{path.stem}_SCL.tif"), size)
    return path


def _write_scl(path: Path, size: int) -> None:
    """Write the SCL sidecar: uint8 class codes on the 20 m grid."""
    scl_size = size * 10 // S2_SCL_RESOLUTION_M
    codes = sorted(S2_SCL_CLASSES)
    rows = np.arange(scl_size).reshape(-1, 1)
    cols = np.arange(scl_size).reshape(1, -1)
    data = np.asarray(codes, dtype="uint8")[(rows + cols) % len(codes)]
    data[0, 0] = 0  # SC_NODATA present so readers meet the sentinel
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=scl_size,
        width=scl_size,
        count=1,
        dtype="uint8",
        crs=_CRS,
        transform=from_origin(
            *_ORIGIN, float(S2_SCL_RESOLUTION_M), float(S2_SCL_RESOLUTION_M)
        ),
        nodata=0,
        compress="deflate",
    ) as dst:
        dst.write(data, 1)
        dst.set_band_description(1, "SCL")
        dst.update_tags(
            **{f"SCL_{i}": name for i, name in S2_SCL_CLASSES.items()},
        )

"""Spec-accurate synthetic Sentinel-2 L2A products, as a preset.

Every radiometric fact here comes from ``geospatial-spec``, reached through its
guard API — so this module cannot encode the offset without stating which
baseline it is encoding for. That is the same discipline the guard imposes on
production code, applied to the generator that produces test data.

Formerly ``geocase.synth.sentinel2``. Two changes on the way across:

1. Constants are no longer local. They import from the spec package, which
   machine-checks them against a real granule's metadata.
2. ``size`` defaults to 256, not 32. The one confirmed compute-side adopter set
   ≥224 px as a hard requirement — below it a ViT pipeline cannot run at all.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from geospatial_spec.sentinel2 import (
    baseline_has_offset,
    boa_offset,
    explain,
    nodata_value,
    quantification,
)

from geocase.raster.primitive import DEFAULT_SIZE, FixtureSpec, raster_fixture

__all__ = ["sentinel2_l2a", "DEFAULT_SIZE"]

# Matches the corpus's shared synthetic grid: UTM 33N, 10 m pixels.
_CRS = "EPSG:32633"
_ORIGIN = (500_000.0, 4_500_000.0)

#: Native resolution per band and the SCL class table are descriptive facts, not
#: scoped ones — they do not change with baseline — so they are read through
#: ``explain`` rather than through a guard.
_BAND_RESOLUTION_M: dict[str, int] = explain("band_resolution_m").value
_SCL_CLASSES: dict[int, str] = explain("scl_classes").value
_SCL_RESOLUTION_M: int = explain("scl_resolution_m").value
_DTYPE: str = explain("dtype").value

#: The four native-10 m bands, in zero-padded filename form.
BANDS_10M = ("B02", "B03", "B04", "B08")


def _native_resolution(band: str) -> int:
    """Native resolution of a zero-padded or witness-form band name."""
    if band in _BAND_RESOLUTION_M:
        return _BAND_RESOLUTION_M[band]
    # Zero-padded filename form ("B04") -> witness form ("B4").
    return _BAND_RESOLUTION_M["B" + band[1:].lstrip("0")]


def _reflectance(size: int, seed: int) -> np.ndarray:
    """Deterministic surface reflectance in [0.02, 0.62)."""
    rows = np.arange(size).reshape(-1, 1)
    cols = np.arange(size).reshape(1, -1)
    ramp = ((rows * 3 + cols * 5 + seed * 17) % 60) / 100.0
    return ramp + 0.02


def _dn(reflectance: np.ndarray, baseline: str) -> np.ndarray:
    """Encode reflectance as L2A DNs for *baseline*.

    ``reflectance = (DN + offset) / quantification``, so the encoder subtracts
    the offset. Asking the guard for the offset means this function cannot be
    written without naming the baseline it encodes for.
    """
    dn = reflectance * quantification(baseline=baseline) - boa_offset(baseline=baseline)
    encoded: np.ndarray = np.round(dn).astype(_DTYPE)
    return encoded


def sentinel2_l2a(
    path: str | Path | None = None,
    size: int = DEFAULT_SIZE,
    bands: tuple[str, ...] = BANDS_10M,
    baseline: str = "04.00",
    nodata_border: int | bool = False,
    scl: bool = False,
) -> FixtureSpec | Path:
    """Build a synthetic Sentinel-2 L2A band stack.

    All bands are written on the 10 m grid, as real L2A resampled stacks are; a
    band whose native resolution is 20 m gets its values block-replicated from a
    size/2 grid, so the upsampled-from-20 m structure is present in the pixels
    rather than merely claimed in metadata.

    Args:
        path: Where to write a GeoTIFF. **If omitted, returns the
            :class:`FixtureSpec` instead of writing** — the escape hatch, for
            callers who do not want a rasterio dependency.
        size: Edge length in pixels. Defaults to 256; values below 224 cannot
            exercise a ViT pipeline.
        baseline: Processing baseline. ``"04.00"`` and later carry the BOA
            offset; earlier baselines do not, and the pixel values differ
            accordingly.
        nodata_border: Width in pixels of a nodata frame, or ``True`` for a
            2 px frame (the legacy behaviour).
        scl: Also write the Scene Classification sidecar as ``<stem>_SCL.tif``,
            uint8 at 20 m. Requires *path*.

    Returns:
        The written :class:`~pathlib.Path` if *path* was given, otherwise the
        :class:`~geocase.raster.FixtureSpec`.
    """
    border = 2 if nodata_border is True else int(nodata_border or 0)
    nodata = nodata_value(product="S2_L2A")

    arrays = []
    for i, band in enumerate(bands):
        if _native_resolution(band) >= 20:
            coarse = _reflectance(size // 2, seed=i)
            refl = np.repeat(np.repeat(coarse, 2, axis=0), 2, axis=1)
        else:
            refl = _reflectance(size, seed=i)
        arrays.append(_dn(refl, baseline))

    quant = float(quantification(baseline=baseline))
    offset = boa_offset(baseline=baseline)

    spec = raster_fixture(
        bands=len(bands),
        dtype=_DTYPE,
        size=size,
        crs=_CRS,
        origin=_ORIGIN,
        resolution=10.0,
        nodata=nodata,
        nodata_border=border,
        values=np.stack(arrays),
        band_descriptions=tuple(bands),
        band_tags=tuple(
            {"NATIVE_RESOLUTION_M": str(_native_resolution(b))} for b in bands
        ),
        # GDAL's convention is value = raw * scale + offset, so the
        # self-consistent band form of (DN + offset) / quant is scale 1/quant
        # with the offset expressed in the scaled unit.
        scales=(1.0 / quant,) * len(bands),
        offsets=(offset / quant,) * len(bands),
        tags=_product_tags(baseline),
    )

    if path is None:
        if scl:
            raise ValueError("scl=True writes a sidecar file and requires path=")
        return spec

    written = spec.write(path)
    if scl:
        _write_scl(written.with_name(f"{written.stem}_SCL.tif"), size)
    return written


def _product_tags(baseline: str) -> dict[str, str]:
    """Dataset tags a real L2A product carries."""
    quant = quantification(baseline=baseline)
    tags = {
        "PROCESSING_BASELINE": baseline,
        "QUANTIFICATION_VALUE": str(quant),
        "BOA_QUANTIFICATION_VALUE": str(quant),
    }
    if baseline_has_offset(baseline):
        tags["BOA_ADD_OFFSET"] = str(boa_offset(baseline=baseline))
    return tags


def _write_scl(path: Path, size: int) -> None:
    """Write the SCL sidecar: uint8 class codes on the 20 m grid."""
    scl_size = size * 10 // _SCL_RESOLUTION_M
    codes = sorted(_SCL_CLASSES)
    rows = np.arange(scl_size).reshape(-1, 1)
    cols = np.arange(scl_size).reshape(1, -1)
    data = np.asarray(codes, dtype="uint8")[(rows + cols) % len(codes)]
    data[0, 0] = 0  # SC_NODATA present so readers meet the sentinel

    raster_fixture(
        bands=1,
        dtype="uint8",
        size=scl_size,
        crs=_CRS,
        origin=_ORIGIN,
        resolution=float(_SCL_RESOLUTION_M),
        nodata=0,
        values=data[np.newaxis, ...],
        band_descriptions=("SCL",),
        tags={f"SCL_{i}": name for i, name in _SCL_CLASSES.items()},
    ).write(path)

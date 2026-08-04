"""Generic loader — dispatch to the right loader based on a loader hint.

Used when callers want a single entry point and let the case metadata's
``loader_hint`` decide which concrete loader runs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load(path: str | Path, *, loader_hint: str = "generic", **kwargs: Any) -> Any:
    """Load *path* using the loader implied by *loader_hint*.

    Args:
        path: Path to the data file.
        loader_hint: One of ``"geopandas"``, ``"rasterio"``, ``"xarray"`` or
            ``"generic"``. ``"generic"`` falls back to reading raw bytes.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: If *loader_hint* is unknown.
    """
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Data file not found: {resolved}")

    # Each branch binds its own name: the three `load` functions have
    # different signatures, so reusing one alias makes the second and third
    # imports type errors.
    if loader_hint == "rasterio":
        from geocase.loaders.rasterio_loader import load as _load_rasterio

        return _load_rasterio(resolved, **kwargs)
    if loader_hint == "geopandas":
        from geocase.loaders.geopandas_loader import load as _load_geopandas

        return _load_geopandas(resolved, **kwargs)
    if loader_hint == "xarray":
        from geocase.loaders.xarray_loader import load as _load_xarray

        return _load_xarray(resolved, **kwargs)
    if loader_hint == "generic":
        return resolved.read_bytes()

    raise ValueError(f"Unknown loader_hint: {loader_hint!r}")

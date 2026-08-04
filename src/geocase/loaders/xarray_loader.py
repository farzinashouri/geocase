"""xarray loader — open raster/netcdf fixtures as xarray objects."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load(path: str | Path, **kwargs: Any) -> Any:
    """Open *path* with :func:`xarray.open_dataset`.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ImportError: If xarray is not installed.
    """
    import xarray as xr  # lazy import

    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Dataset file not found: {resolved}")

    return xr.open_dataset(resolved, **kwargs)

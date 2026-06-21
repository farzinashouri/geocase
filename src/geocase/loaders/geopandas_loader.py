"""GeoPandas loader — read bundled vector fixtures into GeoDataFrames."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load(path: str | Path, **kwargs: Any) -> Any:
    """Read *path* into a GeoDataFrame via :func:`geopandas.read_file`.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ImportError: If geopandas is not installed.
    """
    import geopandas as gpd  # lazy import

    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Vector file not found: {resolved}")

    return gpd.read_file(resolved, **kwargs)

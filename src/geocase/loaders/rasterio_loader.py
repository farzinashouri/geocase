"""Rasterio loader — open bundled raster fixtures as rasterio datasets.

Thin wrappers around ``rasterio.open`` so that callers (and the registry-driven
test suites) have a single, typed entry point for reading raster cases.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import rasterio


@contextmanager
def open_raster(
    path: str | Path,
    **kwargs: Any,
) -> Generator[rasterio.DatasetReader, None, None]:
    """Open *path* as a rasterio dataset (context manager).

    Yields:
        A :class:`rasterio.DatasetReader`.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ImportError: If rasterio is not installed.
    """
    import rasterio as _rio  # lazy import

    resolved = Path(path)
    if not resolved.is_file():
        raise FileNotFoundError(f"Raster file not found: {resolved}")

    with _rio.open(resolved, **kwargs) as src:
        yield src


def load(path: str | Path, band: int | None = None, **kwargs: Any) -> tuple:
    """Read a raster into memory and return ``(data, profile, nodata)``.

    Args:
        path: Path to the raster file.
        band: Optional 1-based band index. If omitted, all bands are read
            (returning a 3-D array shaped ``(bands, rows, cols)``).

    Returns:
        Tuple of ``(numpy_array, profile_dict, nodata)``.
    """
    with open_raster(path, **kwargs) as src:
        data = src.read(band) if band is not None else src.read()
        profile = dict(src.profile)
        nodata = src.nodata
    return data, profile, nodata

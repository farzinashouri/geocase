"""Raster case — wraps a raster dataset for rasterio-based access."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from geocase.cases.base import BaseCase
from geocase.catalog.models import CaseMetadata
from geocase.loaders.rasterio_loader import load as _load_raster
from geocase.loaders.rasterio_loader import open_raster

if TYPE_CHECKING:
    import rasterio


class RasterCase(BaseCase):
    """A test case backed by a raster file (GeoTIFF, …).

    Usage::

        case = RasterCase(metadata, root_dir)
        with case.open() as src:
            data = src.read(1)
    """

    def __init__(self, metadata: CaseMetadata, root_dir: Path) -> None:
        if metadata.category != "raster":
            raise ValueError(
                f"RasterCase requires category='raster', "
                f"got '{metadata.category}' for case '{metadata.id}'"
            )
        super().__init__(metadata, root_dir)

    @contextmanager
    def open(self, **kwargs: Any) -> Generator[rasterio.DatasetReader, None, None]:
        """Open the primary raster file as a rasterio dataset.

        This is a context manager — use it with ``with``.

        Yields:
            A :class:`rasterio.DatasetReader`.

        Raises:
            FileNotFoundError: If the primary file does not exist.
            ImportError: If rasterio is not installed.
        """
        # Opening is delegated to loaders/rasterio_loader.py so there is one
        # rasterio entry point rather than two parallel ones (Step 9). The
        # existence check stays here because the loader's message names a
        # file, while this one names the case's *primary* file.
        path = self.primary_path
        if not path.is_file():
            raise FileNotFoundError(f"Primary data file not found: {path}")

        with open_raster(path, **kwargs) as src:
            yield src

    def read(self, band: int = 1, **kwargs: Any) -> tuple[Any, dict[str, Any], Any]:
        """Convenience: read a single band and return (array, profile).

        Args:
            band: Band number (1-based).

        Returns:
            Tuple of ``(numpy_array, profile_dict, nodata)``.
        """
        path = self.primary_path
        if not path.is_file():
            raise FileNotFoundError(f"Primary data file not found: {path}")

        return _load_raster(path, band=band, **kwargs)

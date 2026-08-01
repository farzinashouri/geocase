"""Case factory — dispatch metadata to the correct case subclass."""

from __future__ import annotations

from pathlib import Path

from geocase.cases.base import BaseCase
from geocase.cases.netcdf import NetCDFCase
from geocase.cases.raster import RasterCase
from geocase.cases.vector import VectorCase
from geocase.catalog.models import CaseMetadata

_DISPATCH: dict[str, type[BaseCase]] = {
    "vector": VectorCase,
    "raster": RasterCase,
    "netcdf": NetCDFCase,
}


def create_case(metadata: CaseMetadata, root_dir: Path) -> BaseCase:
    """Create the appropriate case subclass for the given metadata.

    Args:
        metadata: Parsed case metadata (must include ``category``).
        root_dir: Path to the case's directory on disk.

    Returns:
        A :class:`VectorCase`, :class:`RasterCase`, or
        :class:`NetCDFCase` instance.

    Raises:
        ValueError: If the category has no registered handler.
    """
    cls = _DISPATCH.get(metadata.category)
    if cls is None:
        raise ValueError(
            f"No case handler for category '{metadata.category}'. "
            f"Supported: {sorted(_DISPATCH)}"
        )
    return cls(metadata, root_dir)

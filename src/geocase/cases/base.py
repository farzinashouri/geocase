"""Base case — abstract foundation for all test-case types.

Every concrete case (vector, raster, netcdf) inherits from :class:`BaseCase`,
which bundles the parsed metadata with the on-disk root directory so that
subclasses can resolve file paths and load data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from geocase.catalog.models import AssertionHints, CaseMetadata, FileMap


class BaseCase:
    """Common base for all geospatial test cases.

    A ``BaseCase`` is *not* loadable on its own — subclasses must
    implement the appropriate ``load()`` or ``open()`` method.

    Attributes:
        metadata: The parsed :class:`CaseMetadata`.
        root_dir: Absolute path to the case's directory (the folder
            that contains ``case.yaml``).
    """

    def __init__(self, metadata: CaseMetadata, root_dir: Path) -> None:
        self._metadata = metadata
        self._root_dir = Path(root_dir).resolve()

    # ------------------------------------------------------------------
    # Metadata shortcuts
    # ------------------------------------------------------------------

    @property
    def metadata(self) -> CaseMetadata:
        return self._metadata

    @property
    def id(self) -> str:
        return self._metadata.id

    @property
    def title(self) -> str:
        return self._metadata.title

    @property
    def category(self) -> str:
        return self._metadata.category

    @property
    def tags(self) -> list[str]:
        return self._metadata.tags

    @property
    def assertions(self) -> AssertionHints:
        return self._metadata.assertions

    @property
    def params(self) -> dict[str, Any]:
        return self._metadata.params

    @property
    def files(self) -> FileMap:
        return self._metadata.files

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------

    @property
    def root_dir(self) -> Path:
        """Absolute path to the case directory."""
        return self._root_dir

    @property
    def primary_path(self) -> Path:
        """Absolute path to the primary data file."""
        return self._root_dir / self._metadata.files.primary

    @property
    def notes_path(self) -> Path | None:
        """Absolute path to the notes file, or *None*."""
        if self._metadata.files.notes:
            return self._root_dir / self._metadata.files.notes
        return None

    def sidecar_paths(self) -> list[Path]:
        """Absolute paths to any sidecar files."""
        return [self._root_dir / s for s in self._metadata.files.sidecars]

    def primary_exists(self) -> bool:
        """Return True if the primary data file exists on disk."""
        return self.primary_path.is_file()

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        cls = type(self).__name__
        return f"{cls}({self.id!r}, root={str(self._root_dir)!r})"

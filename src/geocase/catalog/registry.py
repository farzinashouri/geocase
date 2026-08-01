"""Case registry — in-memory lookup of all known test cases.

Loads the case-index.yaml, parses every referenced case.yaml into a
CaseMetadata model, and provides fast lookup by case id.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from geocase.catalog.loader import load_case_index, load_case_metadata
from geocase.catalog.manifests import load_manifest
from geocase.catalog.models import CaseMetadata, ManifestMetadata


class CaseRegistry:
    """Immutable in-memory registry of all indexed test cases.

    Usage::

        registry = CaseRegistry.from_index(metadata_dir / "case-index.yaml")
        case = registry.get("dateline_crossing_polygon")
        for case in registry:
            ...
    """

    def __init__(
        self,
        cases: dict[str, CaseMetadata],
        manifest_cases: dict[str, ManifestMetadata] | None = None,
    ) -> None:
        self._cases: dict[str, CaseMetadata] = dict(cases)
        self._manifest_cases: dict[str, ManifestMetadata] = dict(manifest_cases or {})

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_index(cls, case_index_path: Path) -> CaseRegistry:
        """Build a registry by loading every case listed in case-index.yaml.

        Args:
            case_index_path: Path to ``case-index.yaml``.

        Returns:
            A populated :class:`CaseRegistry`.

        Raises:
            FileNotFoundError: If the index or any referenced case.yaml
                is missing.
        """
        case_index_path = Path(case_index_path)
        base_dir = case_index_path.parent  # metadata/ directory

        # case-index.yaml paths are relative to the src/geocase/ root
        src_root = base_dir.parent  # src/geocase/

        relative_paths = load_case_index(case_index_path)

        cases: dict[str, CaseMetadata] = {}
        for rel in relative_paths:
            case_path = src_root / rel
            meta = load_case_metadata(case_path)
            if meta.id in cases:
                raise ValueError(
                    f"Duplicate case id '{meta.id}' found in registry ({case_path})"
                )
            cases[meta.id] = meta

        return cls(cases)

    @classmethod
    def from_sources(
        cls,
        case_index_path: Path,
        *,
        manifest_paths: list[Path] | None = None,
    ) -> CaseRegistry:
        """Build a registry from bundled cases plus optional manifest sources."""
        registry = cls.from_index(case_index_path)
        manifest_case_map: dict[str, ManifestMetadata] = {}

        for manifest_path in manifest_paths or []:
            manifest = load_manifest(manifest_path)
            for entry in manifest.cases:
                if entry.case_id in registry._cases:
                    raise ValueError(
                        f"Manifest case id '{entry.case_id}' collides with "
                        f"the bundled registry"
                    )
                if entry.case_id in manifest_case_map:
                    raise ValueError(
                        f"Manifest case id '{entry.case_id}' appears in more "
                        f"than one manifest"
                    )
                manifest_case_map[entry.case_id] = manifest

        return cls(registry._cases, manifest_cases=manifest_case_map)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, case_id: str) -> CaseMetadata:
        """Return case metadata for a given id.

        Raises:
            KeyError: If the case id is not registered.
        """
        try:
            return self._cases[case_id]
        except KeyError:
            raise KeyError(
                f"Case '{case_id}' not found in registry. "
                f"Available: {sorted(self._cases)}"
            ) from None

    def list_ids(self) -> list[str]:
        """Return a sorted list of all registered case ids."""
        return sorted([*self._cases, *self._manifest_cases])

    def list_cases(self) -> list[CaseMetadata]:
        """Return all registered cases sorted by id."""
        return [self._cases[k] for k in sorted(self._cases)]

    def __contains__(self, case_id: str) -> bool:
        return case_id in self._cases or case_id in self._manifest_cases

    def __len__(self) -> int:
        return len(self._cases) + len(self._manifest_cases)

    def __iter__(self) -> Iterator[CaseMetadata]:
        return iter(self.list_cases())

    def __repr__(self) -> str:
        return f"CaseRegistry({len(self._cases)} cases)"


# ------------------------------------------------------------------
# Module-level convenience
# ------------------------------------------------------------------

_DEFAULT_REGISTRY: CaseRegistry | None = None


def get_registry(*, reload: bool = False) -> CaseRegistry:
    """Return the singleton registry, loading it on first call.

    The default case-index.yaml is resolved relative to the installed
    package tree.

    Args:
        reload: Force re-reading from disk.

    Returns:
        The global :class:`CaseRegistry`.
    """
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None or reload:
        metadata_dir = Path(__file__).resolve().parent.parent / "metadata"
        _DEFAULT_REGISTRY = CaseRegistry.from_index(metadata_dir / "case-index.yaml")
    return _DEFAULT_REGISTRY


def reset_registry() -> None:
    """Clear the cached default registry (useful for tests)."""
    global _DEFAULT_REGISTRY
    _DEFAULT_REGISTRY = None

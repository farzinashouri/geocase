"""Case registry — in-memory lookup of all known test cases.

Loads the case-index.yaml, parses every referenced case.yaml into a
CaseMetadata model, and provides fast lookup by case id.

Manifests named by ``GEOCASE_MANIFESTS`` are layered on top: their case ids
become *known* to the registry without being pretended into ``CaseMetadata``.
Nothing here fetches data — see :mod:`geocase.catalog.errors`.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from geocase.catalog.errors import remote_case_unavailable
from geocase.catalog.loader import load_case_index, load_case_metadata
from geocase.catalog.manifests import load_manifest, resolve_manifest_case
from geocase.catalog.models import CaseMetadata, ManifestCaseEntry, ManifestMetadata


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
            RemoteCaseUnavailableError: If the id belongs to a manifest. It
                subclasses ``KeyError``, and its message names the artifact's
                URI instead of leaving the caller to guess why a listed id has
                no metadata.
            KeyError: If the case id is not registered at all.
        """
        try:
            return self._cases[case_id]
        except KeyError:
            pass

        manifest = self._manifest_cases.get(case_id)
        if manifest is not None:
            raise remote_case_unavailable(case_id, manifest) from None

        raise KeyError(
            f"Case '{case_id}' not found in registry. Available: {sorted(self._cases)}"
        ) from None

    def list_ids(self) -> list[str]:
        """Return a sorted list of all registered case ids, bundled and remote."""
        return sorted([*self._cases, *self._manifest_cases])

    def list_cases(self) -> list[CaseMetadata]:
        """Return all *bundled* cases sorted by id.

        Manifest-backed cases are absent by design: a
        :class:`~geocase.catalog.models.ManifestCaseEntry` is not
        ``CaseMetadata``, and returning one here would be a type lie. Use
        :meth:`list_remote_ids` for those.
        """
        return [self._cases[k] for k in sorted(self._cases)]

    def is_remote(self, case_id: str) -> bool:
        """Return True if *case_id* comes from a manifest rather than the wheel."""
        return case_id in self._manifest_cases

    def list_remote_ids(self) -> list[str]:
        """Return a sorted list of the manifest-backed case ids."""
        return sorted(self._manifest_cases)

    def get_manifest(self, case_id: str) -> ManifestMetadata:
        """Return the manifest that lists *case_id*.

        Raises:
            KeyError: If no manifest lists that id.
        """
        try:
            return self._manifest_cases[case_id]
        except KeyError:
            raise KeyError(
                f"Case '{case_id}' is not manifest-backed. "
                f"Remote ids: {self.list_remote_ids()}"
            ) from None

    def get_manifest_entry(self, case_id: str) -> ManifestCaseEntry:
        """Return the manifest entry (path, checksum, version) for *case_id*.

        Raises:
            KeyError: If no manifest lists that id.
        """
        return resolve_manifest_case(self.get_manifest(case_id), case_id)

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

#: Environment variable naming extra manifest sources. Its value is an
#: ``os.pathsep``-separated list of manifest YAML files, or of directories whose
#: ``*.yaml`` files are all manifests.
MANIFESTS_ENV_VAR = "GEOCASE_MANIFESTS"

_DEFAULT_REGISTRY: CaseRegistry | None = None
_DEFAULT_REGISTRY_SOURCES: tuple[Path, ...] | None = None


def manifest_paths_from_env(value: str | None = None) -> list[Path]:
    """Resolve ``GEOCASE_MANIFESTS`` into a list of manifest files.

    Directory entries expand to their ``*.yaml`` files, sorted, so a user can
    point the variable at a whole manifest directory. Non-existent entries are
    kept rather than skipped: loading them raises a ``FileNotFoundError`` that
    names the path, which beats silently ignoring a typo.

    Args:
        value: Raw variable value. Read from the environment when *None*.
    """
    if value is None:
        value = os.environ.get(MANIFESTS_ENV_VAR, "")

    paths: list[Path] = []
    for raw in value.split(os.pathsep):
        entry = raw.strip()
        if not entry:
            continue
        path = Path(entry).expanduser()
        if path.is_dir():
            paths.extend(sorted(path.glob("*.yaml")))
        else:
            paths.append(path)
    return paths


def get_registry(*, reload: bool = False) -> CaseRegistry:
    """Return the singleton registry, loading it on first call.

    The default case-index.yaml is resolved relative to the installed
    package tree. Any manifests named by :data:`MANIFESTS_ENV_VAR` are layered
    on top, making their case ids visible to :meth:`CaseRegistry.is_remote` and
    friends (no data is fetched — see ``docs/remote-datasets.md``).

    The environment variable is read here rather than at import time, and the
    resolved source list is part of the cache key, so a test that monkeypatches
    it gets the registry it asked for instead of a stale singleton.

    Args:
        reload: Force re-reading from disk.

    Returns:
        The global :class:`CaseRegistry`.
    """
    global _DEFAULT_REGISTRY, _DEFAULT_REGISTRY_SOURCES

    sources = tuple(manifest_paths_from_env())
    if _DEFAULT_REGISTRY is None or reload or sources != _DEFAULT_REGISTRY_SOURCES:
        metadata_dir = Path(__file__).resolve().parent.parent / "metadata"
        _DEFAULT_REGISTRY = CaseRegistry.from_sources(
            metadata_dir / "case-index.yaml",
            manifest_paths=list(sources),
        )
        _DEFAULT_REGISTRY_SOURCES = sources
    return _DEFAULT_REGISTRY


def reset_registry() -> None:
    """Clear the cached default registry and the case-root cache.

    Both, not just the registry: ``roots.case_roots_by_id`` is an independent
    ``lru_cache`` over the same on-disk catalog, so leaving it warm makes a
    "reset" registry disagree with the paths it resolves.
    """
    global _DEFAULT_REGISTRY, _DEFAULT_REGISTRY_SOURCES
    _DEFAULT_REGISTRY = None
    _DEFAULT_REGISTRY_SOURCES = None

    # Imported here rather than at module scope: roots.py imports this module
    # to answer is_remote(), so a top-level import would be circular.
    from geocase.catalog.roots import case_roots_by_id

    case_roots_by_id.cache_clear()

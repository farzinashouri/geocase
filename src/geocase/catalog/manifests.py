"""Manifest loading and lookup helpers for external case catalogs."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator
from urllib.parse import urljoin

import yaml

from geocase.catalog.models import ManifestCaseEntry, ManifestMetadata


def _validate_unique_case_ids(manifest: ManifestMetadata) -> ManifestMetadata:
    seen: set[str] = set()
    duplicates: set[str] = set()

    for entry in manifest.cases:
        if entry.case_id in seen:
            duplicates.add(entry.case_id)
        seen.add(entry.case_id)

    if duplicates:
        duplicate_list = ", ".join(sorted(duplicates))
        raise ValueError(
            f"Manifest '{manifest.manifest_key}' contains duplicate case ids: "
            f"{duplicate_list}"
        )

    return manifest


def load_manifest(path: Path) -> ManifestMetadata:
    """Load a manifest YAML file into a validated manifest model."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Manifest file not found: {path}")

    with open(path) as file_handle:
        raw = yaml.safe_load(file_handle)

    if raw is None:
        raise ValueError(f"Empty YAML file: {path}")

    manifest = ManifestMetadata.model_validate(raw)
    return _validate_unique_case_ids(manifest)


def load_manifest_case_ids(path: Path) -> list[str]:
    """Load a manifest and return its listed case ids."""
    manifest = load_manifest(path)
    return [entry.case_id for entry in manifest.cases]


def resolve_manifest_case(
    manifest: ManifestMetadata, case_id: str
) -> ManifestCaseEntry:
    """Return a manifest entry by case id."""
    for entry in manifest.cases:
        if entry.case_id == case_id:
            return entry

    raise KeyError(
        f"Case '{case_id}' not found in manifest '{manifest.manifest_key}'. "
        f"Available: {[entry.case_id for entry in manifest.cases]}"
    )


def build_manifest_uri(manifest: ManifestMetadata, entry: ManifestCaseEntry) -> str:
    """Build a runtime URI by joining the manifest base URI and entry path."""
    base_uri = manifest.storage.base_uri.rstrip("/") + "/"
    relative_path = entry.relative_path.lstrip("/")
    return urljoin(base_uri, relative_path)


def iter_manifest_entries(manifest: ManifestMetadata) -> Iterator[ManifestCaseEntry]:
    """Iterate over manifest case entries in declared order."""
    return iter(manifest.cases)

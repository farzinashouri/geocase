"""Tests for planned manifest catalog support."""

from pathlib import Path

import pytest
import yaml

import geocase.catalog.manifests as manifest_module
import geocase.catalog.models as models_module
from geocase.catalog.registry import CaseRegistry


_EXTENDED_MANIFEST = (
    Path(__file__).resolve().parents[2] / "extended-manifests" / "public-extended.yaml"
)
_CASE_INDEX = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "geocase"
    / "metadata"
    / "case-index.yaml"
)


def _require_attr(obj: object, name: str):
    value = getattr(obj, name, None)
    assert value is not None, (
        f"Expected {obj!r} to define `{name}` for manifest support"
    )
    return value


class TestManifestModels:
    """Cover the typed manifest models described in the manifest support plan."""

    def test_manifest_models_are_exposed_from_catalog_models(self):
        """Exposes dedicated typed models for manifest storage, entries, and top-level metadata."""
        assert hasattr(models_module, "ManifestStorage")
        assert hasattr(models_module, "ManifestCaseEntry")
        assert hasattr(models_module, "ManifestMetadata")

    def test_public_extended_manifest_validates_into_typed_model(self):
        """Parses the sample extended manifest into typed manifest models with nested storage and case entries."""
        manifest_cls = _require_attr(models_module, "ManifestMetadata")

        raw = yaml.safe_load(_EXTENDED_MANIFEST.read_text())
        manifest = manifest_cls.model_validate(raw)

        assert manifest.manifest_key == "public-extended"
        assert manifest.storage.storage_type == "https"
        assert manifest.storage.base_uri == "https://example.org/geocase/public"
        assert [entry.case_id for entry in manifest.cases] == [
            "coastal_scene_small",
            "utm_boundary_scene",
        ]


class TestManifestLoader:
    """Cover loading and lookup behavior for external manifest files."""

    def test_load_manifest_reads_the_sample_manifest(self):
        """Loads the sample extended manifest from disk into a validated manifest model."""
        load_manifest = _require_attr(manifest_module, "load_manifest")

        manifest = load_manifest(_EXTENDED_MANIFEST)

        assert manifest.manifest_key == "public-extended"
        assert len(manifest.cases) == 2

    def test_resolve_manifest_case_returns_entry_for_known_case_id(self):
        """Finds a manifest-backed case entry by case id without downloading any artifacts."""
        load_manifest = _require_attr(manifest_module, "load_manifest")
        resolve_manifest_case = _require_attr(manifest_module, "resolve_manifest_case")

        manifest = load_manifest(_EXTENDED_MANIFEST)
        entry = resolve_manifest_case(manifest, "coastal_scene_small")

        assert entry.case_id == "coastal_scene_small"
        assert entry.relative_path == "coastal_scene_small.zip"
        assert entry.archive_format == "zip"

    def test_build_manifest_uri_joins_base_uri_and_relative_path(self):
        """Builds a deterministic remote artifact URI from manifest storage metadata and the case entry path."""
        load_manifest = _require_attr(manifest_module, "load_manifest")
        resolve_manifest_case = _require_attr(manifest_module, "resolve_manifest_case")
        build_manifest_uri = _require_attr(manifest_module, "build_manifest_uri")

        manifest = load_manifest(_EXTENDED_MANIFEST)
        entry = resolve_manifest_case(manifest, "coastal_scene_small")

        assert (
            build_manifest_uri(manifest, entry)
            == "https://example.org/geocase/public/coastal_scene_small.zip"
        )

    def test_duplicate_case_ids_are_rejected_with_a_clear_error(self, tmp_path):
        """Rejects manifests that declare the same case id more than once."""
        load_manifest = _require_attr(manifest_module, "load_manifest")

        duplicate_manifest = tmp_path / "duplicate-manifest.yaml"
        duplicate_manifest.write_text(
            yaml.safe_dump(
                {
                    "manifest_key": "duplicate-cases",
                    "title": "Duplicate cases",
                    "schema_version": "1.0",
                    "storage": {
                        "storage_type": "https",
                        "base_uri": "https://example.org/geocase/public",
                    },
                    "cases": [
                        {
                            "case_id": "coastal_scene_small",
                            "version": "1.0.0",
                            "relative_path": "coastal_scene_small.zip",
                            "sha256": "abc123",
                        },
                        {
                            "case_id": "coastal_scene_small",
                            "version": "1.0.1",
                            "relative_path": "coastal_scene_small_v2.zip",
                            "sha256": "def456",
                        },
                    ],
                }
            )
        )

        with pytest.raises(ValueError, match="duplicate.*coastal_scene_small"):
            load_manifest(duplicate_manifest)


class TestManifestRegistryIntegration:
    """Cover the explicit registry path that should expose manifest-backed entries."""

    def test_registry_exposes_an_explicit_manifest_aware_constructor(self):
        """Adds a separate constructor for manifest-backed catalogs without changing the bundled-only default path."""
        assert hasattr(CaseRegistry, "from_sources")

    def test_manifest_backed_ids_are_listed_without_breaking_bundled_registry(self):
        """Lists bundled and manifest-backed case ids together when the explicit manifest-aware registry path is used."""
        from_sources = _require_attr(CaseRegistry, "from_sources")

        registry = from_sources(_CASE_INDEX, manifest_paths=[_EXTENDED_MANIFEST])
        ids = registry.list_ids()

        assert "dateline_crossing_polygon" in ids
        assert "coastal_scene_small" in ids
        assert "utm_boundary_scene" in ids

"""Tests for the manifest half of scripts/validate_catalog.py — Step 14.4.

The catalog gate covered bundled cases and suites but never opened
``extended-manifests/``, so a manifest could declare a duplicate id, shadow a
bundled case, or name a bundled_analog that does not exist, and CI would pass.
"""

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

from geocase.catalog.registry import CaseRegistry

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "validate_catalog.py"
_CASE_INDEX = _REPO_ROOT / "src" / "geocase" / "metadata" / "case-index.yaml"


def _load_script():
    """Import validate_catalog.py by path; scripts/ is not a package."""
    spec = importlib.util.spec_from_file_location(
        "validate_catalog_under_test", _SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validate_catalog = _load_script()


@pytest.fixture(scope="module")
def registry():
    """The bundled registry the manifests are validated against."""
    return CaseRegistry.from_index(_CASE_INDEX)


def _write_manifest(directory: Path, name: str, cases: list[dict]) -> Path:
    path = directory / f"{name}.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "manifest_key": name,
                "title": name,
                "schema_version": "1.0",
                "storage": {
                    "storage_type": "https",
                    "base_uri": "https://example.org/geocase/test",
                },
                "cases": cases,
            }
        )
    )
    return path


def _case(case_id: str, **overrides) -> dict:
    entry = {
        "case_id": case_id,
        "version": "1.0.0",
        "relative_path": f"{case_id}.zip",
        "sha256": "a" * 64,
    }
    entry.update(overrides)
    return entry


class TestBundledManifests:
    """The manifests actually shipped in this repository."""

    def test_the_repository_manifests_validate(self, registry):
        """Test extended-manifests/ passes the gate as committed."""
        paths, _ = validate_catalog._validate_manifests(
            _REPO_ROOT / "extended-manifests", registry
        )

        assert [path.name for path in paths] == [
            "public-extended.yaml",
            "satellite-scenes.yaml",
        ]

    def test_placeholder_checksums_warn_rather_than_fail(self, registry):
        """Test `replace_me` is allowed — it is what v1.1 exists to replace.

        Gating on it would block the storage work these manifests were written
        for, so it has to be visible without being fatal.
        """
        _, warnings = validate_catalog._validate_manifests(
            _REPO_ROOT / "extended-manifests", registry
        )

        assert len(warnings) == 7
        assert all("replace_me" in warning for warning in warnings)
        assert any("satellite-scenes/dem_scene" in warning for warning in warnings)

    def test_a_missing_manifest_directory_is_not_an_error(self, registry, tmp_path):
        """Test a checkout without manifests still validates."""
        assert validate_catalog._validate_manifests(tmp_path / "absent", registry) == (
            [],
            [],
        )


class TestManifestDefects:
    """Each defect the gate now catches."""

    def test_a_case_id_shadowing_a_bundled_case_fails(self, registry, tmp_path):
        """Test a manifest cannot claim an id that ships in the wheel."""
        bundled_id = registry.list_cases()[0].id
        _write_manifest(tmp_path, "shadowing", [_case(bundled_id)])

        with pytest.raises(
            validate_catalog.CatalogValidationError, match="already bundled"
        ):
            validate_catalog._validate_manifests(tmp_path, registry)

    def test_a_case_id_declared_by_two_manifests_fails(self, registry, tmp_path):
        """Test cross-manifest duplicates are caught, not just in-file ones."""
        _write_manifest(tmp_path, "first", [_case("shared_scene")])
        _write_manifest(tmp_path, "second", [_case("shared_scene")])

        with pytest.raises(
            validate_catalog.CatalogValidationError, match="declared by both"
        ):
            validate_catalog._validate_manifests(tmp_path, registry)

    def test_a_malformed_checksum_fails(self, registry, tmp_path):
        """Test a truncated digest is rejected; only `replace_me` is exempt."""
        _write_manifest(tmp_path, "bad-digest", [_case("scene", sha256="abc123")])

        with pytest.raises(validate_catalog.CatalogValidationError, match="sha256"):
            validate_catalog._validate_manifests(tmp_path, registry)

    def test_an_unknown_bundled_analog_fails(self, registry, tmp_path):
        """Test `bundled_analog` must name a case that exists.

        The field's whole purpose is answering "what is the big version of this
        fixture?", which a dangling id answers wrongly.
        """
        _write_manifest(
            tmp_path,
            "dangling-analog",
            [_case("scene", bundled_analog="no_such_fixture")],
        )

        with pytest.raises(
            validate_catalog.CatalogValidationError, match="bundled_analog"
        ):
            validate_catalog._validate_manifests(tmp_path, registry)

    def test_a_valid_bundled_analog_passes(self, registry, tmp_path):
        """Test a real analog id is accepted."""
        bundled_id = registry.list_cases()[0].id
        _write_manifest(
            tmp_path, "good-analog", [_case("scene", bundled_analog=bundled_id)]
        )

        paths, warnings = validate_catalog._validate_manifests(tmp_path, registry)

        assert len(paths) == 1
        assert warnings == []

    def test_an_unparseable_manifest_fails(self, registry, tmp_path):
        """Test a manifest missing required fields names itself in the error."""
        (tmp_path / "broken.yaml").write_text(yaml.safe_dump({"title": "no key"}))

        with pytest.raises(
            validate_catalog.CatalogValidationError, match="broken.yaml"
        ):
            validate_catalog._validate_manifests(tmp_path, registry)


class TestScriptEntryPoint:
    """``main()`` wires the manifest check into the CI gate."""

    def test_main_validates_manifests_and_reports_them(self, monkeypatch, capsys):
        """Test a default run reports the manifest count and warnings."""
        monkeypatch.setattr(sys, "argv", ["validate_catalog.py"])

        assert validate_catalog.main() == 0

        out = capsys.readouterr().out
        assert "Validated manifests: 2" in out
        assert "warning:" in out

    def test_cases_only_skips_manifests(self, monkeypatch, capsys):
        """Test --cases-only stays a case-metadata-only run."""
        monkeypatch.setattr(sys, "argv", ["validate_catalog.py", "--cases-only"])

        assert validate_catalog.main() == 0

        out = capsys.readouterr().out
        assert "Manifest validation: skipped (--cases-only)" in out

    def test_main_exits_nonzero_on_a_bad_manifest(self, monkeypatch, capsys, tmp_path):
        """Test the gate actually fails the build."""
        _write_manifest(tmp_path, "duplicate-a", [_case("shared_scene")])
        _write_manifest(tmp_path, "duplicate-b", [_case("shared_scene")])
        monkeypatch.setattr(
            sys, "argv", ["validate_catalog.py", "--manifests-dir", str(tmp_path)]
        )

        assert validate_catalog.main() == 1
        assert "Catalog validation failed" in capsys.readouterr().out

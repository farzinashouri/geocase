"""Tests for the cross-format-canonical half of scripts/validate_catalog.py.

Plan 13. Sixty ``<geomtype>_<format>_baseline`` cases promised "one geometry,
many file formats" via a ``cross_format_canonical`` tag and a
``params.canonical_source_case_id`` link, and nothing in ``src/`` or ``tests/``
ever dereferenced either -- so 53 of them held a different geometry from the
canonical they named, and diffing two of them produced a fabricated
cross-format difference.

This covers the metadata layer only: that the *declarations* are consistent and
resolvable. Whether the bytes actually agree is
``tests/unit/test_cross_format_canonical.py``, which needs geopandas and so
cannot live in the geopandas-free CI ``catalog`` job.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

from geocase.catalog.models import CaseMetadata
from geocase.catalog.registry import CaseRegistry

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "validate_catalog.py"
_CASE_INDEX = _REPO_ROOT / "src" / "geocase" / "metadata" / "case-index.yaml"


def _load_script():
    """Import validate_catalog.py by path; scripts/ is not a package."""
    spec = importlib.util.spec_from_file_location(
        "validate_catalog_canonical_under_test", _SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validate_catalog = _load_script()


@pytest.fixture(scope="module")
def registry():
    """The bundled registry as committed."""
    return CaseRegistry.from_index(_CASE_INDEX)


def _meta(case_id: str, **overrides) -> CaseMetadata:
    """Build a minimal vector CaseMetadata; *overrides* replace any field."""
    payload = {
        "id": case_id,
        "title": case_id,
        "description": case_id,
        "category": "vector",
        "format": "GeoJSON",
        "test_tier": "unit",
        "size_class": "tiny",
        "storage_class": "bundled",
        "redistributable": True,
        "loader_hint": "geopandas",
        "schema_version": "1.0",
        "status": "validated",
        "geometry_type": "Point",
        "crs": "EPSG:4326",
        "files": {"primary": "geometry.geojson"},
        "tags": [],
        "params": {},
    }
    payload.update(overrides)
    return CaseMetadata.model_validate(payload)


def _registry_of(*cases: CaseMetadata) -> CaseRegistry:
    return CaseRegistry({case.id: case for case in cases})


def _canonical() -> CaseMetadata:
    return _meta("simple_valid_point")


def _member(**overrides) -> CaseMetadata:
    defaults = {
        "format": "KML",
        "tags": ["cross_format_canonical"],
        "params": {"canonical_source_case_id": "simple_valid_point"},
    }
    defaults.update(overrides)
    return _meta("point_kml_baseline", **defaults)


class TestBundledCatalog:
    """The catalog as actually committed."""

    def test_every_bundled_declaration_is_consistent(self, registry):
        """Test the shipped catalog passes the gate."""
        assert validate_catalog._validate_cross_format_canonical(registry) == 60

    def test_the_tag_and_the_param_agree_across_the_catalog(self, registry):
        """Test the 59-vs-60 gap that motivated this check is closed.

        ``point_gml_baseline`` carried the tag while declaring an unrelated
        ``canonical_location`` literal instead of a source id, so it was the one
        case the biconditional would have caught before this plan.
        """
        tagged = {
            case.id
            for case in registry.list_cases()
            if "cross_format_canonical" in case.tags
        }
        declaring = {
            case.id
            for case in registry.list_cases()
            if "canonical_source_case_id" in case.params
        }

        assert tagged == declaring
        assert "point_gml_baseline" in tagged

    def test_main_reports_the_link_count(self, monkeypatch, capsys):
        """Test the count is surfaced, so a silent drop to zero is visible."""
        monkeypatch.setattr(sys, "argv", ["validate_catalog.py"])

        assert validate_catalog.main() == 0

        assert "Cross-format canonical links: 60" in capsys.readouterr().out


class TestDeclarationDefects:
    """Each defect the gate catches, one per test."""

    def test_a_valid_declaration_passes(self):
        """Test the happy path, so the failures below mean something."""
        assert (
            validate_catalog._validate_cross_format_canonical(
                _registry_of(_canonical(), _member())
            )
            == 1
        )

    def test_the_tag_without_the_param_fails(self):
        """Test a tagged case must name what it mirrors."""
        broken = _member(params={})

        with pytest.raises(
            validate_catalog.CatalogValidationError, match="declares no"
        ):
            validate_catalog._validate_cross_format_canonical(
                _registry_of(_canonical(), broken)
            )

    def test_the_param_without_the_tag_fails(self):
        """Test an untagged case cannot claim a canonical.

        Tag-based selection is how the family is picked up, so a member without
        the tag is invisible to the very comparison it declares itself part of.
        """
        broken = _member(tags=["vector", "kml"])

        with pytest.raises(
            validate_catalog.CatalogValidationError, match="is not tagged"
        ):
            validate_catalog._validate_cross_format_canonical(
                _registry_of(_canonical(), broken)
            )

    def test_an_unresolvable_source_id_fails(self):
        """Test a dangling link is caught rather than skipped."""
        broken = _member(params={"canonical_source_case_id": "no_such_case"})

        with pytest.raises(
            validate_catalog.CatalogValidationError, match="not a known case id"
        ):
            validate_catalog._validate_cross_format_canonical(
                _registry_of(_canonical(), broken)
            )

    def test_a_non_string_source_id_fails(self):
        """Test the old ``canonical_location`` mapping shape is rejected.

        ``point_gml_baseline`` shipped exactly this: a ``{lon, lat}`` dict under
        ``params``. Naming a different key let it pass unnoticed; naming this one
        with a dict value must not.
        """
        broken = _member(
            params={"canonical_source_case_id": {"lon": 10.5, "lat": 50.5}}
        )

        with pytest.raises(
            validate_catalog.CatalogValidationError, match="not a case id string"
        ):
            validate_catalog._validate_cross_format_canonical(
                _registry_of(_canonical(), broken)
            )

    def test_a_non_geojson_source_fails(self):
        """Test the canonical must be the GeoJSON reference, not a peer format."""
        shapefile_source = _meta("simple_valid_point", format="Shapefile")

        with pytest.raises(
            validate_catalog.CatalogValidationError, match="rather than 'GeoJSON'"
        ):
            validate_catalog._validate_cross_format_canonical(
                _registry_of(shapefile_source, _member())
            )

    def test_a_geometry_type_mismatch_fails(self):
        """Test a Point case cannot name a Polygon canonical."""
        broken = _member(geometry_type="Polygon")

        with pytest.raises(
            validate_catalog.CatalogValidationError, match="geometry_type"
        ):
            validate_catalog._validate_cross_format_canonical(
                _registry_of(_canonical(), broken)
            )

    def test_a_canonical_that_is_itself_a_member_fails(self):
        """Test the reference cannot be a chain.

        If a canonical could point at another canonical, "the geometry" stops
        having a single definition and the family can drift as a unit.
        """
        chained = _meta(
            "simple_valid_point",
            tags=["cross_format_canonical"],
            params={"canonical_source_case_id": "simple_valid_point"},
        )

        with pytest.raises(
            validate_catalog.CatalogValidationError, match="single source of truth"
        ):
            validate_catalog._validate_cross_format_canonical(
                _registry_of(chained, _member())
            )

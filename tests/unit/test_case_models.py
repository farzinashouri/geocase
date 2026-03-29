"""Tests for geocase.catalog.models — Pydantic metadata models."""

import pytest
from pydantic import ValidationError

from geocase.catalog.models import (
    AssertionHints,
    CaseMetadata,
    FileMap,
    RemoteInfo,
    SourceInfo,
    SuiteMetadata,
    SuiteSelection,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_case(**overrides) -> dict:
    """Return a minimal valid CaseMetadata dict, with optional overrides."""
    base = {
        "id": "test_case",
        "title": "Test Case",
        "category": "vector",
        "format": "GeoJSON",
        "test_tier": "unit",
        "size_class": "tiny",
        "storage_class": "bundled",
        "redistributable": True,
        "schema_version": "1.0",
        "loader_hint": "geopandas",
        "files": {"primary": "data.geojson"},
    }
    base.update(overrides)
    return base


def _minimal_suite(**overrides) -> dict:
    """Return a minimal valid SuiteMetadata dict."""
    base = {
        "suite_key": "my-suite",
        "title": "My Suite",
        "description": "A test suite.",
        "schema_version": "1.0",
        "selection": {},
    }
    base.update(overrides)
    return base


# ===================================================================
# CaseMetadata — happy paths
# ===================================================================

class TestCaseMetadataValid:
    """Valid CaseMetadata construction."""

    def test_minimal(self):
        case = CaseMetadata(**_minimal_case())
        assert case.id == "test_case"
        assert case.category == "vector"
        assert case.status == "draft"  # default

    def test_all_fields(self):
        case = CaseMetadata(**_minimal_case(
            description="Full description.",
            status="validated",
            tags=["tag1", "tag2"],
            risk_types=["risk_a"],
            behavioral_goal="Find bugs.",
            expected_capabilities=["load"],
            geometry_type="Polygon",
            crs="EPSG:4326",
            remote={"uri": "https://example.com/data.zip"},
            source={"name": "test", "license": "MIT"},
            assertions={
                "expect_loadable": True,
                "expect_valid_geometry": True,
                "expected_epsg": 4326,
                "expected_geometry_types": ["Polygon"],
            },
            params={"custom_key": 42},
        ))
        assert case.status == "validated"
        assert case.tags == ["tag1", "tag2"]
        assert case.assertions.expected_epsg == 4326
        assert case.params["custom_key"] == 42
        assert case.remote is not None
        assert case.remote.uri == "https://example.com/data.zip"

    def test_defaults_are_sane(self):
        case = CaseMetadata(**_minimal_case())
        assert case.tags == []
        assert case.risk_types == []
        assert case.expected_capabilities == []
        assert case.params == {}
        assert case.remote is None
        assert case.source is None
        assert case.assertions.expect_loadable is True
        assert case.assertions.expected_geometry_types == []


# ===================================================================
# CaseMetadata — validation errors
# ===================================================================

class TestCaseMetadataInvalid:
    """CaseMetadata should reject bad data."""

    def test_empty_id(self):
        with pytest.raises(ValidationError, match="empty"):
            CaseMetadata(**_minimal_case(id=""))

    def test_uppercase_id(self):
        with pytest.raises(ValidationError, match="lowercase"):
            CaseMetadata(**_minimal_case(id="Bad_Case"))

    def test_id_with_spaces(self):
        with pytest.raises(ValidationError, match="spaces"):
            CaseMetadata(**_minimal_case(id="bad case"))

    def test_invalid_category(self):
        with pytest.raises(ValidationError):
            CaseMetadata(**_minimal_case(category="audio"))

    def test_invalid_format(self):
        with pytest.raises(ValidationError):
            CaseMetadata(**_minimal_case(format="BMP"))

    def test_invalid_test_tier(self):
        with pytest.raises(ValidationError):
            CaseMetadata(**_minimal_case(test_tier="nightly"))

    def test_invalid_size_class(self):
        with pytest.raises(ValidationError):
            CaseMetadata(**_minimal_case(size_class="huge"))

    def test_invalid_storage_class(self):
        with pytest.raises(ValidationError):
            CaseMetadata(**_minimal_case(storage_class="s3"))

    def test_invalid_loader_hint(self):
        with pytest.raises(ValidationError):
            CaseMetadata(**_minimal_case(loader_hint="pandas"))

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            CaseMetadata(**_minimal_case(status="deleted"))

    def test_missing_required_field(self):
        data = _minimal_case()
        del data["files"]
        with pytest.raises(ValidationError):
            CaseMetadata(**data)

    def test_missing_primary_in_files(self):
        with pytest.raises(ValidationError):
            CaseMetadata(**_minimal_case(files={"notes": "notes.md"}))


# ===================================================================
# FileMap
# ===================================================================

class TestFileMap:
    def test_minimal(self):
        fm = FileMap(primary="data.geojson")
        assert fm.primary == "data.geojson"
        assert fm.sidecars == []

    def test_full(self):
        fm = FileMap(
            primary="data.geojson",
            preview="thumb.png",
            notes="notes.md",
            sidecars=["extra.csv"],
        )
        assert fm.preview == "thumb.png"
        assert fm.sidecars == ["extra.csv"]


# ===================================================================
# RemoteInfo / SourceInfo / AssertionHints
# ===================================================================

class TestSupportingModels:
    def test_remote_info_defaults(self):
        ri = RemoteInfo()
        assert ri.uri is None
        assert ri.byte_size is None

    def test_source_info(self):
        si = SourceInfo(name="test", license="MIT")
        assert si.name == "test"

    def test_assertion_hints_defaults(self):
        ah = AssertionHints()
        assert ah.expect_loadable is True
        assert ah.expect_nodata is None


# ===================================================================
# SuiteSelection
# ===================================================================

class TestSuiteSelection:
    def test_empty_selection(self):
        sel = SuiteSelection()
        assert sel.category is None
        assert sel.tags_any == []

    def test_typed_fields(self):
        sel = SuiteSelection(
            category="vector",
            test_tier="unit",
            storage_class="bundled",
            format="GeoJSON",
            size_class="tiny",
        )
        assert sel.category == "vector"
        assert sel.format == "GeoJSON"

    def test_invalid_category_rejected(self):
        with pytest.raises(ValidationError):
            SuiteSelection(category="audio")

    def test_invalid_test_tier_rejected(self):
        with pytest.raises(ValidationError):
            SuiteSelection(test_tier="nightly")


# ===================================================================
# SuiteMetadata
# ===================================================================

class TestSuiteMetadata:
    def test_minimal(self):
        suite = SuiteMetadata(**_minimal_suite())
        assert suite.suite_key == "my-suite"
        assert suite.case_order == []
        assert suite.notes is None

    def test_with_selection(self):
        suite = SuiteMetadata(**_minimal_suite(
            selection={"category": "vector", "tags_any": ["crs"]},
            case_order=["case_a", "case_b"],
            notes="Some notes.",
        ))
        assert suite.selection.category == "vector"
        assert suite.selection.tags_any == ["crs"]
        assert suite.case_order == ["case_a", "case_b"]

    def test_missing_required(self):
        with pytest.raises(ValidationError):
            SuiteMetadata(suite_key="x")  # type: ignore[call-arg]

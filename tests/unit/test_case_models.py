"""Tests for geocase.catalog.models — Pydantic metadata models."""

from pathlib import Path
from typing import get_args

import pytest
import yaml
from pydantic import ValidationError

from geocase.catalog import models
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
        """Constructs minimal valid case metadata with the default status."""
        case = CaseMetadata(**_minimal_case())
        assert case.id == "test_case"
        assert case.category == "vector"
        assert case.status == "draft"  # default

    def test_all_fields(self):
        """Preserves fully populated metadata, nested source info, and custom params."""
        case = CaseMetadata(
            **_minimal_case(
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
            )
        )
        assert case.status == "validated"
        assert case.tags == ["tag1", "tag2"]
        assert case.assertions.expected_epsg == 4326
        assert case.params["custom_key"] == 42
        assert case.remote is not None
        assert case.remote.uri == "https://example.com/data.zip"

    def test_defaults_are_sane(self):
        """Applies empty-list defaults and default assertion hints to omitted fields."""
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
        """Rejects empty case ids."""
        with pytest.raises(ValidationError, match="empty"):
            CaseMetadata(**_minimal_case(id=""))

    def test_uppercase_id(self):
        """Rejects ids that are not lowercase."""
        with pytest.raises(ValidationError, match="lowercase"):
            CaseMetadata(**_minimal_case(id="Bad_Case"))

    def test_id_with_spaces(self):
        """Rejects ids containing spaces."""
        with pytest.raises(ValidationError, match="spaces"):
            CaseMetadata(**_minimal_case(id="bad case"))

    def test_invalid_category(self):
        """Rejects unsupported case categories."""
        with pytest.raises(ValidationError):
            CaseMetadata(**_minimal_case(category="audio"))

    def test_invalid_format(self):
        """Rejects unsupported format values."""
        with pytest.raises(ValidationError):
            CaseMetadata(**_minimal_case(format="BMP"))

    def test_invalid_test_tier(self):
        """Rejects unsupported test-tier values."""
        with pytest.raises(ValidationError):
            CaseMetadata(**_minimal_case(test_tier="nightly"))

    def test_invalid_size_class(self):
        """Rejects unsupported size classes."""
        with pytest.raises(ValidationError):
            CaseMetadata(**_minimal_case(size_class="huge"))

    def test_invalid_storage_class(self):
        """Rejects unsupported storage classes."""
        with pytest.raises(ValidationError):
            CaseMetadata(**_minimal_case(storage_class="s3"))

    def test_invalid_loader_hint(self):
        """Rejects unsupported loader hints."""
        with pytest.raises(ValidationError):
            CaseMetadata(**_minimal_case(loader_hint="pandas"))

    def test_invalid_status(self):
        """Rejects unsupported case status values."""
        with pytest.raises(ValidationError):
            CaseMetadata(**_minimal_case(status="deleted"))

    def test_missing_required_field(self):
        """Requires the `files` field on case metadata."""
        data = _minimal_case()
        del data["files"]
        with pytest.raises(ValidationError):
            CaseMetadata(**data)

    def test_missing_primary_in_files(self):
        """Requires `files.primary` to be present."""
        with pytest.raises(ValidationError):
            CaseMetadata(**_minimal_case(files={"notes": "notes.md"}))


# ===================================================================
# FileMap
# ===================================================================


class TestFileMap:
    def test_minimal(self):
        """Builds a file map with an empty sidecar list by default."""
        fm = FileMap(primary="data.geojson")
        assert fm.primary == "data.geojson"
        assert fm.sidecars == []

    def test_full(self):
        """Preserves optional preview and sidecar file paths."""
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
        """Defaults remote metadata fields to `None`."""
        ri = RemoteInfo()
        assert ri.uri is None
        assert ri.byte_size is None

    def test_source_info(self):
        """Stores source name and license metadata."""
        si = SourceInfo(name="test", license="MIT")
        assert si.name == "test"

    def test_assertion_hints_defaults(self):
        """Defaults assertion hints to loadable with no explicit NoData expectation."""
        ah = AssertionHints()
        assert ah.expect_loadable is True
        assert ah.expect_nodata is None


# ===================================================================
# SuiteSelection
# ===================================================================


class TestSuiteSelection:
    def test_empty_selection(self):
        """Creates an empty suite selection with no active filters."""
        sel = SuiteSelection()
        assert sel.category is None
        assert sel.tags_any == []

    def test_typed_fields(self):
        """Parses typed suite selection filters into the model."""
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
        """Rejects unsupported suite selection categories."""
        with pytest.raises(ValidationError):
            SuiteSelection(category="audio")

    def test_invalid_test_tier_rejected(self):
        """Rejects unsupported suite selection tiers."""
        with pytest.raises(ValidationError):
            SuiteSelection(test_tier="nightly")


# ===================================================================
# SuiteMetadata
# ===================================================================


class TestSuiteMetadata:
    def test_minimal(self):
        """Constructs minimal suite metadata with no notes or case order."""
        suite = SuiteMetadata(**_minimal_suite())
        assert suite.suite_key == "my-suite"
        assert suite.case_order == []
        assert suite.notes is None

    def test_with_selection(self):
        """Preserves embedded selection filters and explicit case order."""
        suite = SuiteMetadata(
            **_minimal_suite(
                selection={"category": "vector", "tags_any": ["crs"]},
                case_order=["case_a", "case_b"],
                notes="Some notes.",
            )
        )
        assert suite.selection.category == "vector"
        assert suite.selection.tags_any == ["crs"]
        assert suite.case_order == ["case_a", "case_b"]

    def test_missing_required(self):
        """Requires the mandatory suite metadata fields."""
        with pytest.raises(ValidationError):
            SuiteMetadata(suite_key="x")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Schema / model agreement
# ---------------------------------------------------------------------------


class TestCaseSchemaMatchesModels:
    """`case.schema.yaml` documents the same contract `models.py` enforces.

    Nothing at runtime reads the schema file — it is documentation for case
    authors — which is exactly why it drifted: its `format` enum listed 7 of
    the 17 values `FormatType` accepts, so it could not have validated 10 of
    the formats already in the catalog, `SQLite` among them.
    """

    @staticmethod
    def _schema() -> dict:
        schema_path = (
            Path(models.__file__).resolve().parents[1]
            / "metadata"
            / "schemas"
            / "case.schema.yaml"
        )
        with schema_path.open() as handle:
            return yaml.safe_load(handle)

    @pytest.mark.parametrize(
        ("property_name", "literal"),
        [
            ("category", models.Category),
            ("format", models.FormatType),
            ("test_tier", models.TestTier),
            ("size_class", models.SizeClass),
            ("storage_class", models.StorageClass),
            ("loader_hint", models.LoaderHint),
            ("status", models.Status),
        ],
    )
    def test_enum_matches_literal(self, property_name: str, literal: object) -> None:
        """Keeps each schema enum identical to the Literal that enforces it."""
        schema_values = self._schema()["properties"][property_name]["enum"]
        assert schema_values == list(get_args(literal))

    def test_top_level_properties_match_case_metadata_fields(self) -> None:
        """Documents every CaseMetadata field, and no field that does not exist."""
        schema_properties = set(self._schema()["properties"])
        assert schema_properties == set(CaseMetadata.model_fields)

    def test_assertion_properties_match_assertion_hints_fields(self) -> None:
        """Documents every AssertionHints field, including the raster ones."""
        schema_properties = set(
            self._schema()["properties"]["assertions"]["properties"]
        )
        assert schema_properties == set(AssertionHints.model_fields)

    def test_nodata_convention_enum_matches_literal(self) -> None:
        """Keeps the nested nodata_convention enum in step as well."""
        prop = self._schema()["properties"]["assertions"]["properties"]
        assert prop["nodata_convention"]["enum"] == list(
            get_args(models.NodataConvention)
        )

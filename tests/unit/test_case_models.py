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
    KnownDivergence,
    RemoteInfo,
    SourceInfo,
    SpatialExtent,
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

    def test_extent_and_region_round_trip(self):
        """Accepts a WGS84 extent and an editorial region label."""
        case = CaseMetadata(
            **_minimal_case(
                extent={"west": 10.0, "south": 50.0, "east": 11.0, "north": 51.0},
                region="Central Europe (synthetic)",
            )
        )
        assert case.extent is not None
        assert case.extent.west == 10.0
        assert case.extent.north == 51.0
        assert case.region == "Central Europe (synthetic)"

    def test_extent_and_region_are_optional(self):
        """Omitting both keeps the 130 existing case files parseable."""
        case = CaseMetadata(**_minimal_case())
        assert case.extent is None
        assert case.region is None

    def test_extent_may_wrap_the_antimeridian(self):
        """``west > east`` is the antimeridian convention, not an error."""
        case = CaseMetadata(
            **_minimal_case(
                extent={"west": 170.0, "south": -10.0, "east": -170.0, "north": 10.0}
            )
        )
        assert case.extent is not None
        assert case.extent.west > case.extent.east


# ===================================================================
# SpatialExtent
# ===================================================================


class TestSpatialExtent:
    """SpatialExtent should police WGS84 coordinate ranges."""

    def test_rejects_inverted_latitudes(self):
        """``north < south`` has no antimeridian analogue -- it is just wrong."""
        with pytest.raises(ValidationError):
            SpatialExtent(west=10.0, south=51.0, east=11.0, north=50.0)

    def test_rejects_longitude_out_of_range(self):
        with pytest.raises(ValidationError):
            SpatialExtent(west=-181.0, south=50.0, east=11.0, north=51.0)

    def test_rejects_latitude_out_of_range(self):
        with pytest.raises(ValidationError):
            SpatialExtent(west=10.0, south=50.0, east=11.0, north=91.0)

    def test_crosses_antimeridian_flag(self):
        assert SpatialExtent(
            west=170.0, south=-10.0, east=-170.0, north=10.0
        ).crosses_antimeridian
        assert not SpatialExtent(
            west=10.0, south=50.0, east=11.0, north=51.0
        ).crosses_antimeridian


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

    def test_required_drivers_defaults_to_empty(self):
        """Defaults required_drivers to [], so existing case.yaml stays valid."""
        assert AssertionHints().required_drivers == []

    def test_required_drivers_accepts_driver_names(self):
        """Stores the OGR driver names a consumer needs before opening a case."""
        ah = AssertionHints(required_drivers=["Parquet"])
        assert ah.required_drivers == ["Parquet"]

    def test_required_drivers_rejects_a_bare_string(self):
        """Rejects a scalar: the field is a list even when there is one driver."""
        with pytest.raises(ValidationError):
            AssertionHints(required_drivers="Parquet")

    def test_expected_error_kind_defaults_to_none(self):
        """Defaults expected_error_kind to None, so existing case.yaml stays valid."""
        assert AssertionHints().expected_error_kind is None

    def test_expected_error_kind_accepts_a_vocabulary_term(self):
        """Stores how a curated-failure case is expected to fail."""
        ah = AssertionHints(
            expect_loadable=False, expected_error_kind="unparseable_geometry"
        )
        assert ah.expected_error_kind == "unparseable_geometry"

    def test_expected_error_kind_rejects_an_exception_class_name(self):
        """Rejects consumer-specific exception names: the field is a vocabulary."""
        with pytest.raises(ValidationError):
            AssertionHints(expect_loadable=False, expected_error_kind="GEOSException")

    def test_expected_error_kind_requires_a_case_that_actually_fails(self):
        """Rejects a failure mode on a case declared loadable -- it never fails."""
        with pytest.raises(ValidationError, match="expect_loadable"):
            AssertionHints(expected_error_kind="unparseable_geometry")

    # --- plan 40 phase 2: ground truth ------------------------------------

    def test_ground_truth_fields_default_to_none(self):
        """Defaults every ground-truth field, so existing case.yaml stays valid."""
        ah = AssertionHints()
        assert ah.expected_mean_masked is None
        assert ah.expected_mean_naive is None
        assert ah.nodata_pixel_count is None
        assert ah.expected_bounds is None

    def test_ground_truth_fields_parse(self):
        """Stores the declared answer a consumer can be graded against."""
        ah = AssertionHints(
            expected_mean_masked=12.5,
            expected_mean_naive=-1234.0,
            nodata_pixel_count=28,
            expected_bounds=[500000.0, 4499920.0, 500080.0, 4500000.0],
        )
        assert ah.expected_mean_masked == 12.5
        assert ah.expected_mean_naive == -1234.0
        assert ah.nodata_pixel_count == 28
        assert ah.expected_bounds == [500000.0, 4499920.0, 500080.0, 4500000.0]

    def test_expected_bounds_rejects_a_scalar(self):
        """Rejects a scalar: the field is [west, south, east, north]."""
        with pytest.raises(ValidationError):
            AssertionHints(expected_bounds=500000.0)

    def test_nodata_pixel_count_rejects_a_non_integer(self):
        """Rejects a fractional count: pixels are counted, not measured."""
        with pytest.raises(ValidationError):
            AssertionHints(nodata_pixel_count=1.5)


# ===================================================================
# KnownDivergence -- plan 28 phase 2.5
# ===================================================================


class TestKnownDivergence:
    """A catalogued consumer disagreement, so repeat runs stay cumulative."""

    def test_requires_a_consumer_and_a_description(self):
        """Both are the minimum for the record to mean anything to a reader."""
        kd = KnownDivergence(
            consumer="pyogrio",
            description="use_arrow=True returns a NULL-geometry row under bbox",
        )
        assert kd.consumer == "pyogrio"
        assert kd.version_range is None
        assert kd.upstream_url is None

    def test_rejects_a_record_with_no_consumer(self):
        """An unattributed divergence cannot be matched against anything."""
        with pytest.raises(ValidationError):
            KnownDivergence(description="something diverges")

    def test_rejects_a_blank_consumer(self):
        """Whitespace is not a consumer name."""
        with pytest.raises(ValidationError):
            KnownDivergence(consumer="   ", description="something diverges")

    def test_rejects_a_blank_description(self):
        """A record nobody can read is worse than no record."""
        with pytest.raises(ValidationError):
            KnownDivergence(consumer="pyogrio", description="  ")

    def test_carries_a_version_range_and_upstream_link(self):
        """The two fields that let a reader tell "still open" from "fixed"."""
        kd = KnownDivergence(
            consumer="pyogrio",
            version_range=">=0.8",
            description="Arrow path keeps NULL geometries under a spatial filter",
            upstream_url="https://github.com/OSGeo/gdal/issues/1",
        )
        assert kd.version_range == ">=0.8"
        assert kd.upstream_url.endswith("/1")


class TestCaseMetadataKnownDivergences:
    def test_defaults_to_empty(self):
        """Additive with a [] default, so every existing case.yaml stays valid."""
        case = CaseMetadata(**_minimal_case())
        assert case.known_divergences == []

    def test_accepts_records(self):
        """Stores the catalogued divergences alongside the case they belong to."""
        case = CaseMetadata(
            **_minimal_case(
                known_divergences=[
                    {
                        "consumer": "pyogrio",
                        "version_range": ">=0.8",
                        "description": "numpy and Arrow paths disagree on row count",
                        "upstream_url": "https://github.com/OSGeo/gdal/issues/1",
                    }
                ]
            )
        )
        assert len(case.known_divergences) == 1
        assert case.known_divergences[0].consumer == "pyogrio"


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

    def test_known_divergence_properties_match_the_model(self) -> None:
        """Keeps the nested known_divergences item schema in step with the model."""
        item = self._schema()["properties"]["known_divergences"]["items"]
        assert set(item["properties"]) == set(KnownDivergence.model_fields)
        assert set(item["required"]) == {"consumer", "description"}

    def test_nodata_convention_enum_matches_literal(self) -> None:
        """Keeps the nested nodata_convention enum in step as well."""
        prop = self._schema()["properties"]["assertions"]["properties"]
        assert prop["nodata_convention"]["enum"] == list(
            get_args(models.NodataConvention)
        )

    def test_pixel_anchor_enum_matches_literal(self) -> None:
        """Same for pixel_anchor, which is nested rather than top-level.

        Deliberately not a row in ``test_enum_matches_literal`` above: that one
        indexes ``["properties"][name]["enum"]``, and this enum lives under
        ``assertions``, so a row there would raise KeyError rather than check
        anything.
        """
        prop = self._schema()["properties"]["assertions"]["properties"]
        assert prop["expected_pixel_anchor"]["enum"] == list(
            get_args(models.PixelAnchor)
        )


class TestCaseIdDiscoverability:
    """Plan 41 phase 4 -- ``c.case_id`` is the name people reach for first.

    ``KnownDivergence`` already spells the concept ``case_id`` while
    ``CaseMetadata`` spells it ``id``, so the package uses both spellings for
    one concept. The reporter's very first call was ``c.case_id`` and it raised
    a bare pydantic ``AttributeError`` naming nothing useful.
    """

    def test_case_id_returns_the_id(self) -> None:
        meta = CaseMetadata(**_minimal_case())
        assert meta.case_id == meta.id == "test_case"

    def test_case_id_is_read_only(self) -> None:
        """An alias that could be assigned would be a second source of truth."""
        meta = CaseMetadata(**_minimal_case())
        with pytest.raises((AttributeError, ValueError)):
            meta.case_id = "something_else"

    def test_unknown_near_miss_names_the_right_attribute(self) -> None:
        """The message must carry the answer, not just the complaint."""
        meta = CaseMetadata(**_minimal_case())
        with pytest.raises(AttributeError) as exc:
            _ = meta.identifier
        message = str(exc.value)
        assert "'id'" in message
        assert "case_id" in message

    def test_unrelated_attribute_still_raises_attribute_error(self) -> None:
        meta = CaseMetadata(**_minimal_case())
        with pytest.raises(AttributeError):
            _ = meta.totally_unrelated_thing

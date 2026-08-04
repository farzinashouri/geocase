"""Tests for the public API surface — geocase.__all__ and geocase.api.

The ``__all__`` literal below is the v1.0 compatibility promise written down.
Changing it is a deliberate act: adding a name is a minor release, removing or
renaming one is a breaking change.
"""

import pytest

import geocase
from geocase.catalog.models import CaseMetadata
from geocase.catalog.registry import get_registry
from geocase.catalog.suites import ResolvedSuite

_PUBLIC_SURFACE = sorted(
    [
        "__version__",
        # Functions
        "list_cases",
        "get_case",
        "load_case",
        "show_case",
        "list_suites",
        "get_suite",
        # Errors
        "RemoteCaseUnavailableError",
        # Types
        "BaseCase",
        "VectorCase",
        "RasterCase",
        "NetCDFCase",
        "CaseMetadata",
        "SuiteMetadata",
        "SuiteSelection",
        "ResolvedSuite",
        "AssertionHints",
        "FileMap",
        "SourceInfo",
        "Category",
        "FormatType",
        "TestTier",
        "SizeClass",
        "StorageClass",
        "LoaderHint",
        "Status",
        "NodataConvention",
    ]
)


class TestImportSurface:
    """The names users are allowed to depend on."""

    def test_all_matches_the_pinned_surface(self):
        """Test __all__ matches the pinned public surface."""
        assert sorted(geocase.__all__) == _PUBLIC_SURFACE

    def test_every_exported_name_is_importable(self):
        """Test every name in __all__ actually resolves on the package."""
        missing = [name for name in geocase.__all__ if not hasattr(geocase, name)]
        assert missing == []

    def test_version_comes_from_distribution_metadata(self):
        """Test __version__ is read from installed metadata, not a literal."""
        from importlib.metadata import version

        assert geocase.__version__ == version("geocase")

    def test_manifest_models_are_not_part_of_the_promise(self):
        """Test manifest models stay in geocase.catalog until v1.1."""
        for name in ("ManifestMetadata", "ManifestCaseEntry", "ManifestStorage"):
            assert name not in geocase.__all__


class TestListCases:
    """``list_cases`` — filtered metadata, not case objects."""

    def test_returns_the_whole_catalog_unfiltered(self):
        """Test an unfiltered call returns every registered case."""
        assert len(geocase.list_cases()) == len(get_registry().list_cases())

    def test_returns_case_metadata_not_case_objects(self):
        """Test the documented asymmetry with the geocase fixture."""
        cases = geocase.list_cases(category="raster")
        assert cases
        assert all(isinstance(case, CaseMetadata) for case in cases)

    def test_keyword_filters_narrow_the_result(self):
        """Test keyword filters apply the same way suite selections do."""
        rasters = geocase.list_cases(category="raster")
        assert all(case.category == "raster" for case in rasters)
        assert len(rasters) < len(geocase.list_cases())

    def test_results_are_sorted_by_id(self):
        """Test the order is stable across calls."""
        ids = [case.id for case in geocase.list_cases()]
        assert ids == sorted(ids)


class TestGetAndLoadCase:
    """``get_case`` / ``load_case``."""

    def test_get_case_returns_metadata_for_a_known_id(self):
        """Test a known case id resolves to its metadata."""
        case_id = geocase.list_cases()[0].id
        assert geocase.get_case(case_id).id == case_id

    def test_get_case_raises_key_error_for_an_unknown_id(self):
        """Test an unknown id raises KeyError."""
        with pytest.raises(KeyError):
            geocase.get_case("no_such_case_id")

    def test_load_case_returns_a_case_object_with_its_data_on_disk(self):
        """Test load_case materializes a case whose primary file exists."""
        case_id = geocase.list_cases(category="vector")[0].id
        case = geocase.load_case(case_id)

        assert isinstance(case, geocase.BaseCase)
        assert case.id == case_id
        assert case.primary_exists()


class TestShowCase:
    """``show_case`` — the human-readable summary."""

    def test_includes_the_identifying_fields(self):
        """Test the summary names the case and its core metadata."""
        meta = geocase.list_cases(category="raster")[0]
        text = geocase.show_case(meta.id)

        assert meta.id in text
        assert meta.title in text
        assert meta.category in text
        assert meta.format in text

    def test_reports_where_bundled_data_lives(self):
        """Test a bundled case reports its on-disk primary path."""
        meta = geocase.list_cases(category="vector")[0]
        text = geocase.show_case(meta.id)

        assert "bundled at" in text
        assert str(geocase.load_case(meta.id).primary_path) in text

    def test_raises_key_error_for_an_unknown_id(self):
        """Test an unknown id raises KeyError rather than printing nothing."""
        with pytest.raises(KeyError):
            geocase.show_case("no_such_case_id")


class TestSuites:
    """``list_suites`` / ``get_suite``."""

    def test_list_suites_resolves_every_bundled_suite(self):
        """Test every bundled suite resolves to at least one case."""
        suites = geocase.list_suites()

        assert suites
        assert all(isinstance(suite, ResolvedSuite) for suite in suites)
        assert all(len(suite) > 0 for suite in suites)

    def test_get_suite_returns_the_named_suite(self):
        """Test a known suite key resolves to that suite."""
        key = geocase.list_suites()[0].suite_key
        assert geocase.get_suite(key).suite_key == key

    def test_get_suite_lists_the_available_keys_when_unknown(self):
        """Test the error names the suites the user could have meant."""
        with pytest.raises(KeyError) as excinfo:
            geocase.get_suite("no-such-suite")

        assert geocase.list_suites()[0].suite_key in str(excinfo.value)


class TestPluginSharesOnePathResolver:
    """The plugin must not keep its own copy of the case-root cache."""

    def test_plugin_materializes_via_the_shared_resolver(self):
        """Test fixtures.py imports the shared materialize_case."""
        from geocase.catalog import roots
        from geocase.pytest_plugin import fixtures

        assert fixtures.materialize_case is roots.materialize_case

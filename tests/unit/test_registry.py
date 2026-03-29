"""Tests for geocase.catalog.registry — in-memory case lookup."""

from pathlib import Path

import pytest

from geocase.catalog.models import CaseMetadata
from geocase.catalog.registry import CaseRegistry, get_registry, reset_registry


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_SRC = Path(__file__).resolve().parents[2] / "src" / "geocase"
_METADATA = _SRC / "metadata"
_CASE_INDEX = _METADATA / "case-index.yaml"


# ===================================================================
# CaseRegistry.from_index
# ===================================================================

class TestCaseRegistryFromIndex:
    """Build a registry from the bundled case-index.yaml."""

    def test_loads_all_indexed_cases(self):
        reg = CaseRegistry.from_index(_CASE_INDEX)
        assert len(reg) == 8

    def test_all_entries_are_case_metadata(self):
        reg = CaseRegistry.from_index(_CASE_INDEX)
        for case in reg:
            assert isinstance(case, CaseMetadata)

    def test_ids_are_sorted(self):
        reg = CaseRegistry.from_index(_CASE_INDEX)
        ids = reg.list_ids()
        assert ids == sorted(ids)

    def test_missing_index_raises(self):
        with pytest.raises(FileNotFoundError):
            CaseRegistry.from_index(Path("/nonexistent/case-index.yaml"))


# ===================================================================
# CaseRegistry.get / lookup
# ===================================================================

class TestCaseRegistryLookup:
    """Test lookup operations on a pre-built registry."""

    @pytest.fixture()
    def registry(self) -> CaseRegistry:
        return CaseRegistry.from_index(_CASE_INDEX)

    def test_get_existing_case(self, registry: CaseRegistry):
        case = registry.get("dateline_crossing_polygon")
        assert case.id == "dateline_crossing_polygon"
        assert case.category == "vector"

    def test_get_raster_case(self, registry: CaseRegistry):
        case = registry.get("geotiff_nodata_small")
        assert case.id == "geotiff_nodata_small"
        assert case.category == "raster"

    def test_get_netcdf_case(self, registry: CaseRegistry):
        case = registry.get("latlon_small")
        assert case.category == "netcdf"

    def test_get_missing_raises_key_error(self, registry: CaseRegistry):
        with pytest.raises(KeyError, match="no_such_case"):
            registry.get("no_such_case")

    def test_contains(self, registry: CaseRegistry):
        assert "simple_valid_polygon" in registry
        assert "nonexistent" not in registry

    def test_list_cases_length(self, registry: CaseRegistry):
        assert len(registry.list_cases()) == 8

    def test_list_ids_contains_known(self, registry: CaseRegistry):
        ids = registry.list_ids()
        assert "dateline_crossing_polygon" in ids
        assert "polygon_with_hole" in ids
        assert "geotiff_utm_boundary" in ids

    def test_iter(self, registry: CaseRegistry):
        cases = list(registry)
        assert len(cases) == 8
        assert all(isinstance(c, CaseMetadata) for c in cases)

    def test_repr(self, registry: CaseRegistry):
        assert "8 cases" in repr(registry)


# ===================================================================
# get_registry / reset_registry (singleton)
# ===================================================================

class TestDefaultRegistry:
    """Test the module-level singleton helpers."""

    def setup_method(self):
        reset_registry()

    def teardown_method(self):
        reset_registry()

    def test_get_registry_returns_registry(self):
        reg = get_registry()
        assert isinstance(reg, CaseRegistry)
        assert len(reg) == 8

    def test_get_registry_is_cached(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_reload_creates_new_instance(self):
        r1 = get_registry()
        r2 = get_registry(reload=True)
        assert r1 is not r2
        assert len(r2) == 8

    def test_reset_clears_cache(self):
        r1 = get_registry()
        reset_registry()
        r2 = get_registry()
        assert r1 is not r2

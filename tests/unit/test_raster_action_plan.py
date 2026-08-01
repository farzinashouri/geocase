"""Failing TDD tests codifying ``docs/plans/archive/08-raster-action-plan.md``.

Each test class maps to a step in the raster action plan. These are written
*before* implementation, so they are expected to FAIL until the corresponding
step lands. They define the acceptance criteria for the raster expansion phase.

See: docs/plans/archive/08-raster-action-plan.md
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from geocase.catalog.models import AssertionHints, CaseMetadata
from geocase.catalog.registry import get_registry

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src" / "geocase"
_RASTER_DATA = _SRC / "data" / "core" / "raster"
_SCRIPTS = _ROOT / "scripts"


def _load_script_module(name: str):
    """Import a ``scripts/<name>.py`` file by path (scripts is not a package)."""
    path = _SCRIPTS / f"{name}.py"
    if not path.exists():
        pytest.fail(f"Expected script {path} to exist")
    spec = importlib.util.spec_from_file_location(f"_script_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ===================================================================
# Step 2 — Typed raster metadata expectations on AssertionHints
# ===================================================================


class TestStep2TypedRasterHints:
    """``AssertionHints`` should carry typed raster expectation fields."""

    @pytest.mark.parametrize(
        "field",
        [
            "expected_band_count",
            "expected_dtype",
            "expected_shape",
            "expected_nodata_value",
            "nodata_convention",
            "expected_compression",
            "expected_overviews",
            "expected_band_names",
            "expected_scale_factor",
            "expected_colormap_present",
            "is_cog",
        ],
    )
    def test_assertion_hints_has_raster_field(self, field):
        """Each planned raster expectation field exists on the model."""
        assert field in AssertionHints.model_fields, (
            f"AssertionHints is missing typed raster field '{field}'"
        )

    def test_raster_fields_accept_values(self):
        """The new fields are usable together on a single hints object."""
        hints = AssertionHints(
            expected_band_count=3,
            expected_dtype="uint8",
            expected_shape=[16, 16],
            expected_nodata_value=0,
            nodata_convention="sentinel",
            expected_compression="deflate",
            expected_overviews=True,
            expected_band_names=["red", "green", "blue"],
            expected_scale_factor=0.0001,
            expected_colormap_present=False,
            is_cog=True,
        )
        assert hints.expected_band_count == 3
        assert hints.expected_band_names == ["red", "green", "blue"]
        assert hints.is_cog is True


# ===================================================================
# Step 3 — Reproducible raster fixture-generation tooling
# ===================================================================


class TestStep3GenerationTooling:
    """Checksum + raster generator scripts should be real, not stubs."""

    def test_generate_checksums_has_entrypoint(self):
        """``scripts/generate_checksums.py`` exposes a callable main()."""
        module = _load_script_module("generate_checksums")
        assert hasattr(module, "main") and callable(module.main), (
            "generate_checksums.py must expose a callable main()"
        )

    def test_a_raster_generator_script_exists(self):
        """At least one reproducible raster generator script exists."""
        candidates = list(_SCRIPTS.glob("generate_*raster*.py"))
        assert candidates, "Expected a scripts/generate_*raster*.py fixture generator"


# ===================================================================
# Step 4 — Priority 1 EO fixture tranche
# ===================================================================

_PRIORITY_1_CASES = [
    "optical_rgb_small",
    "multispectral_s2_like_small",
    "water_mask_small",
    "dem_small",
    "ndvi_small",
]


class TestStep4Priority1Fixtures:
    """The first EO-oriented bundled raster tranche should be registered."""

    @pytest.fixture(scope="class")
    def registry(self):
        return get_registry(reload=True)

    @pytest.mark.parametrize("case_id", _PRIORITY_1_CASES)
    def test_case_registered(self, registry, case_id):
        """Each Priority 1 case is in the live registry."""
        assert case_id in registry, f"Priority 1 case '{case_id}' not registered"

    @pytest.mark.parametrize("case_id", _PRIORITY_1_CASES)
    def test_case_fixture_dir_exists(self, case_id):
        """Each Priority 1 case has a bundled fixture directory."""
        assert (_RASTER_DATA / case_id).is_dir(), f"Missing fixture dir for '{case_id}'"

    @pytest.mark.parametrize("case_id", _PRIORITY_1_CASES)
    def test_case_is_raster_geotiff(self, registry, case_id):
        """Priority 1 cases are bundled raster GeoTIFFs."""
        case: CaseMetadata = registry.get(case_id)
        assert case.category == "raster"
        assert case.format == "GeoTIFF"
        assert case.storage_class == "bundled"

    @pytest.mark.parametrize("case_id", _PRIORITY_1_CASES)
    def test_case_has_typed_raster_hints(self, registry, case_id):
        """Priority 1 cases declare typed band-count + dtype expectations."""
        hints = registry.get(case_id).assertions
        assert hints.expected_band_count is not None, (
            f"'{case_id}' should declare expected_band_count"
        )
        assert hints.expected_dtype is not None, (
            f"'{case_id}' should declare expected_dtype"
        )


# ===================================================================
# Step 5 — Expanded, metadata-driven raster assertions
# ===================================================================


class TestStep5RasterAssertions:
    """New raster assertion helpers should exist in assertions.raster."""

    @pytest.mark.parametrize(
        "name",
        [
            "assert_compression",
            "assert_has_overviews",
            "assert_nan_nodata",
            "assert_is_cog",
            "assert_band_names",
            "assert_colormap_present",
        ],
    )
    def test_assertion_helper_exists(self, name):
        from geocase.assertions import raster as raster_assertions

        assert hasattr(raster_assertions, name) and callable(
            getattr(raster_assertions, name)
        ), f"Missing raster assertion helper '{name}'"

    def test_metadata_dispatch_covers_new_fields(self):
        """``assert_matches_raster_hints`` dispatches the new typed fields.

        The dispatcher should consult band-count / dtype / shape hints, not
        only the legacy expect_crs / expect_nodata path.
        """
        import inspect

        from geocase.assertions import metadata

        source = inspect.getsource(metadata.assert_matches_raster_hints)
        for field in ("expected_band_count", "expected_dtype", "expected_shape"):
            assert field in source, (
                f"assert_matches_raster_hints does not dispatch '{field}'"
            )


# ===================================================================
# Step 6 — Canonical raster integration suite (smoke import)
# ===================================================================


class TestStep6IntegrationSuite:
    """The integration suite stub should become a real, populated module."""

    def test_suite_module_is_not_a_stub(self):
        path = _ROOT / "tests" / "integration" / "test_core_raster_suite.py"
        text = path.read_text()
        assert "def test" in text, (
            "test_core_raster_suite.py is still a stub with no tests"
        )
        assert "get_registry" in text or "CaseRegistry" in text, (
            "Integration suite should be registry-driven"
        )


# ===================================================================
# Loaders — rasterio loader should be implemented, not a docstring stub
# ===================================================================


class TestRasterioLoaderImplemented:
    """``geocase.loaders.rasterio_loader`` should expose a load callable."""

    def test_loader_exposes_callable(self):
        from geocase.loaders import rasterio_loader

        candidates = [
            n
            for n in ("load", "load_raster", "open_raster", "read_raster")
            if hasattr(rasterio_loader, n) and callable(getattr(rasterio_loader, n))
        ]
        assert candidates, (
            "rasterio_loader exposes no load/open callable (still a stub)"
        )

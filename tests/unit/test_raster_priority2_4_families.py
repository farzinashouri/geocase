"""Failing-first unit tests for Step 9 of the raster action plan.

These cover the Priority 2 through Priority 4 raster families described in
``docs/plans/archive/08-raster-action-plan.md`` (Step 9). None of these cases exist in
the bundled catalog yet, so every test here is expected to **fail** until the
fixtures, ``case.yaml`` metadata, and typed expectations are added through the
generator path established in Steps 2–4.

The tests are written against the existing public surfaces only:

* ``geocase.catalog.registry.get_registry`` for catalog membership,
* ``geocase.cases.factory.create_case`` + the rasterio loader for I/O,
* ``geocase.assertions.metadata.assert_matches_raster_hints`` for dispatch.

Each family also asserts the *characteristic* typed metadata the plan calls
for (COG structure, compression variants, SAR polarisation bands, NaN NoData
DEMs, scaled int16 NDVI, categorical land cover), so a fixture that merely
exists but is mis-typed still fails loudly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from geocase.catalog.loader import load_case_index, load_case_metadata
from geocase.catalog.registry import get_registry

pytest.importorskip("rasterio")

from geocase.assertions.metadata import assert_matches_raster_hints  # noqa: E402
from geocase.cases.factory import create_case  # noqa: E402
from geocase.loaders.rasterio_loader import open_raster  # noqa: E402

_PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "src" / "geocase"


# ---------------------------------------------------------------------------
# Expected Step 9 catalog membership
# ---------------------------------------------------------------------------

PRIORITY_2_CASE_IDS = [
    "cog_singleband_small",
    "cog_multispectral_small",
    "geotiff_external_overviews_small",
]

PRIORITY_3_CASE_IDS = [
    "sar_vv_small",
    "sar_dualpol_small",
    "optical_polar_small",
    "optical_dateline_small",
    "optical_equator_small",
]

PRIORITY_4_CASE_IDS = [
    "multispectral_mixed_resolution_small",
    "dem_nan_nodata_small",
    "ndvi_scaled_int16_small",
    "landcover_small",
]

ALL_STEP9_CASE_IDS = PRIORITY_2_CASE_IDS + PRIORITY_3_CASE_IDS + PRIORITY_4_CASE_IDS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _case_roots_by_id() -> dict[str, Path]:
    """Map every indexed case id to its on-disk case directory."""
    case_index_path = _PACKAGE_ROOT / "metadata" / "case-index.yaml"
    roots: dict[str, Path] = {}
    for rel in load_case_index(case_index_path):
        case_yaml = _PACKAGE_ROOT / rel
        meta = load_case_metadata(case_yaml)
        roots[meta.id] = case_yaml.parent
    return roots


@pytest.fixture(scope="module")
def case_roots() -> dict[str, Path]:
    return _case_roots_by_id()


def _require_case(case_id: str):
    registry = get_registry(reload=True)
    if case_id not in registry:
        pytest.fail(
            f"Step 9 raster case '{case_id}' is not registered yet "
            f"(see docs/plans/archive/08-raster-action-plan.md, Step 9)"
        )
    return registry.get(case_id)


# ---------------------------------------------------------------------------
# Catalog membership
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_id", ALL_STEP9_CASE_IDS)
def test_step9_case_is_registered(case_id):
    registry = get_registry(reload=True)
    assert case_id in registry, (
        f"Expected Step 9 raster case '{case_id}' in the registry"
    )


@pytest.mark.parametrize("case_id", ALL_STEP9_CASE_IDS)
def test_step9_case_is_bundled_geotiff_raster(case_id):
    meta = _require_case(case_id)
    assert meta.category == "raster"
    assert meta.format == "GeoTIFF"
    assert meta.storage_class == "bundled"
    assert meta.redistributable is True
    assert meta.loader_hint == "rasterio"


@pytest.mark.parametrize("case_id", ALL_STEP9_CASE_IDS)
def test_step9_case_primary_loads_and_matches_typed_hints(case_id, case_roots):
    meta = _require_case(case_id)
    root = case_roots.get(case_id)
    assert root is not None, f"No on-disk case dir resolved for '{case_id}'"

    case = create_case(meta, root)
    assert case.primary_exists(), f"Missing primary file for '{case_id}'"

    with open_raster(case.primary_path) as src:
        assert_matches_raster_hints(case, src)


# ---------------------------------------------------------------------------
# Priority 2 — COG / overviews / compression structure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_id", ["cog_singleband_small", "cog_multispectral_small"])
def test_cog_cases_declare_cog_structure(case_id):
    meta = _require_case(case_id)
    hints = meta.assertions
    assert hints.is_cog is True, f"'{case_id}' should declare is_cog: true"
    assert hints.expected_overviews is True, (
        f"COG case '{case_id}' should expect overviews"
    )


def test_cog_singleband_is_single_band():
    meta = _require_case("cog_singleband_small")
    assert meta.assertions.expected_band_count == 1


def test_cog_multispectral_is_multi_band():
    meta = _require_case("cog_multispectral_small")
    assert (meta.assertions.expected_band_count or 0) >= 3


def test_external_overviews_case_expects_overviews_and_sidecar():
    meta = _require_case("geotiff_external_overviews_small")
    assert meta.assertions.expected_overviews is True
    # External overviews ship as a .ovr sidecar alongside the primary GeoTIFF.
    assert any(s.endswith(".ovr") for s in meta.files.sidecars), (
        "Expected a .ovr sidecar for external overviews"
    )


@pytest.mark.parametrize("case_id", ["cog_singleband_small", "cog_multispectral_small"])
def test_cog_cases_satisfy_cog_assertion_at_runtime(case_id, case_roots):
    from geocase.assertions.raster import assert_is_cog

    meta = _require_case(case_id)
    case = create_case(meta, case_roots[case_id])
    with open_raster(case.primary_path) as src:
        assert_is_cog(src)


# ---------------------------------------------------------------------------
# Priority 3 — SAR + geography edge cases
# ---------------------------------------------------------------------------


def test_sar_vv_single_polarisation():
    meta = _require_case("sar_vv_small")
    assert meta.assertions.expected_band_count == 1
    assert meta.assertions.expected_band_names == ["VV"]
    assert "product:sar" in meta.tags


def test_sar_dualpol_two_polarisations():
    meta = _require_case("sar_dualpol_small")
    assert meta.assertions.expected_band_count == 2
    assert meta.assertions.expected_band_names == ["VV", "VH"]
    assert "product:sar" in meta.tags


@pytest.mark.parametrize(
    "case_id, geo_tag",
    [
        ("optical_polar_small", "geography:polar"),
        ("optical_dateline_small", "geography:dateline"),
        ("optical_equator_small", "geography:equator"),
    ],
)
def test_optical_geography_cases_tagged(case_id, geo_tag):
    meta = _require_case(case_id)
    assert geo_tag in meta.tags, f"'{case_id}' should carry tag '{geo_tag}'"


def test_dateline_case_crosses_antimeridian(case_roots):
    """The dateline scene's bounds should straddle +/-180 longitude."""
    meta = _require_case("optical_dateline_small")
    case = create_case(meta, case_roots["optical_dateline_small"])
    with open_raster(case.primary_path) as src:
        bounds = src.bounds
    assert bounds.left > 0 > bounds.right or abs(bounds.left) > 170, (
        "Expected the dateline fixture to span the antimeridian"
    )


# ---------------------------------------------------------------------------
# Priority 4 — mixed resolution, NaN nodata, scaled int16, land cover
# ---------------------------------------------------------------------------


def test_dem_nan_nodata_uses_nan_convention():
    meta = _require_case("dem_nan_nodata_small")
    hints = meta.assertions
    assert hints.nodata_convention == "nan"
    assert hints.expected_dtype in {"float32", "float64"}


def test_dem_nan_nodata_runtime_has_nan(case_roots):
    import numpy as np

    from geocase.assertions.raster import assert_nan_nodata

    meta = _require_case("dem_nan_nodata_small")
    case = create_case(meta, case_roots["dem_nan_nodata_small"])
    with open_raster(case.primary_path) as src:
        assert_nan_nodata(src)
        data = src.read(1)
    assert np.isnan(data).any(), "Expected NaN NoData pixels in the DEM"


def test_ndvi_scaled_int16_declares_scale_factor():
    meta = _require_case("ndvi_scaled_int16_small")
    hints = meta.assertions
    assert hints.expected_dtype == "int16"
    assert hints.expected_scale_factor is not None
    assert hints.expected_scale_factor != 0


# --- Plan 32 Phase 2: the ``ambiguous_zero`` sibling ----------------------


def test_landcover_ambiguous_zero_case_exists():
    """The case ``landcover_small``'s description has always pointed at.

    Plan 28 removed a phantom ``nodata: 0`` from ``landcover_small`` on the
    reasoning that 0-as-both-class-and-sentinel deserves an explicit case; the
    case was never added, so the corpus named a risk it did not cover.
    """
    meta = _require_case("landcover_ambiguous_zero_small")
    assert meta.assertions.expect_nodata is True
    assert "nodata/ambiguous_zero" in meta.risk_types
    assert "nodata/ignored" in meta.risk_types


def test_landcover_ambiguous_zero_declares_zero_as_nodata(case_roots):
    """Zero is the declared sentinel *and* a real, meaningful class value.

    That indistinguishability is the case: a consumer masking ``data ==
    nodata`` silently deletes a legitimate class, and nothing in the file
    distinguishes the two.
    """
    rasterio = pytest.importorskip("rasterio")
    import numpy as np

    root = case_roots["landcover_ambiguous_zero_small"]
    meta = _require_case("landcover_ambiguous_zero_small")
    with rasterio.open(root / meta.files.primary) as src:
        assert src.nodata == 0
        data = src.read(1)

    # The sentinel is present as real pixels, so the case is not inert...
    assert int((data == 0).sum()) > 0
    # ...and 0 is not the *only* thing there: it sits alongside the same
    # classes ``landcover_small`` carries, which is what makes it ambiguous
    # rather than an ordinary nodata collar.
    assert set(np.unique(data)) >= {0, 1, 2, 3}


def test_landcover_ambiguous_zero_is_the_sibling_of_landcover_small():
    """The pair is the useful artifact, so each must name the other."""
    ambiguous = _require_case("landcover_ambiguous_zero_small")
    plain = _require_case("landcover_small")
    assert "landcover_small" in ambiguous.behavioral_goal
    assert "landcover_ambiguous_zero_small" in plain.behavioral_goal


def test_landcover_is_categorical_with_colormap():
    meta = _require_case("landcover_small")
    hints = meta.assertions
    assert hints.expected_dtype in {"uint8", "uint16"}
    assert hints.expected_colormap_present is True
    assert "product:landcover" in meta.tags


def test_landcover_runtime_has_colormap(case_roots):
    from geocase.assertions.raster import assert_colormap_present

    meta = _require_case("landcover_small")
    case = create_case(meta, case_roots["landcover_small"])
    with open_raster(case.primary_path) as src:
        assert_colormap_present(src)


def test_mixed_resolution_case_documents_multiple_resolutions():
    meta = _require_case("multispectral_mixed_resolution_small")
    # Mixed-resolution stacks are documented via params (resampled to a common
    # grid for a single GeoTIFF); at minimum the case should advertise it.
    assert "mixed-resolution" in meta.tags or "resolutions" in meta.params, (
        "Expected the mixed-resolution case to document its resolutions"
    )

"""Content gate — declared assertions must agree with the actual bytes.

``validate_catalog.py`` checks schema, file existence and byte size; it opens
no data file. These tests cover :mod:`geocase.catalog.content`, which is the
gate that compares every declared assertion against real pixels and features.

See docs/plans/28-validate-geocase.md, Phase 1.
"""

from __future__ import annotations

import json

import pytest

from geocase.catalog.models import (
    AssertionHints,
    CaseMetadata,
    FileMap,
    SpatialExtent,
)

rasterio = pytest.importorskip("rasterio")


def _raster_metadata(case_id: str, primary: str, **hints) -> CaseMetadata:
    return CaseMetadata(
        id=case_id,
        title=case_id,
        category="raster",
        format="GeoTIFF",
        test_tier="unit",
        size_class="tiny",
        storage_class="bundled",
        redistributable=True,
        schema_version="1.0",
        loader_hint="rasterio",
        files=FileMap(primary=primary),
        assertions=AssertionHints(**hints),
    )


def _vector_metadata(case_id: str, primary: str, **hints) -> CaseMetadata:
    return CaseMetadata(
        id=case_id,
        title=case_id,
        category="vector",
        format="GeoJSON",
        test_tier="unit",
        size_class="tiny",
        storage_class="bundled",
        redistributable=True,
        schema_version="1.0",
        loader_hint="geopandas",
        files=FileMap(primary=primary),
        assertions=AssertionHints(**hints),
    )


def _write_geojson(path, features):
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))


def _point(x, y):
    return {
        "type": "Feature",
        "properties": {},
        "geometry": {"type": "Point", "coordinates": [x, y]},
    }


# --- 1.1 / 1.2.1: phantom nodata ------------------------------------------


def test_expect_nodata_true_with_zero_matching_pixels_is_an_error(tmp_path):
    """The defect behind all 6 phantom-nodata cases.

    A tag alone is not nodata. Declaring ``expect_nodata`` on a raster whose
    pixels never take the sentinel makes the case inert: a consumer testing
    nodata handling gets a green light from data that cannot test it.
    """
    from geocase.catalog.content import check_case_content
    from geocase.raster import raster_fixture

    spec = raster_fixture(
        dtype="float32", nodata=-9999, nodata_border=0, fill="constant", constant=1.0
    )
    spec.write(tmp_path / "phantom.tif")

    meta = _raster_metadata("phantom_nodata", "phantom.tif", expect_nodata=True)
    errors = check_case_content(tmp_path, meta)

    assert len(errors) == 1
    assert "phantom_nodata" in errors[0]
    assert "expect_nodata" in errors[0]


def test_expect_nodata_true_with_real_nodata_pixels_passes(tmp_path):
    from geocase.catalog.content import check_case_content
    from geocase.raster import raster_fixture

    spec = raster_fixture(dtype="float32", nodata=-9999, nodata_border=1)
    spec.write(tmp_path / "real.tif")

    meta = _raster_metadata("real_nodata", "real.tif", expect_nodata=True)
    assert check_case_content(tmp_path, meta) == []


# --- 1.2.2: expected_nodata_value -----------------------------------------


def test_expected_nodata_value_mismatch_is_an_error(tmp_path):
    from geocase.catalog.content import check_case_content
    from geocase.raster import raster_fixture

    spec = raster_fixture(dtype="float32", nodata=-9999, nodata_border=1)
    spec.write(tmp_path / "r.tif")

    meta = _raster_metadata("wrong_value", "r.tif", expected_nodata_value=0)
    errors = check_case_content(tmp_path, meta)

    assert errors
    assert any("expected_nodata_value" in e for e in errors)


def test_nan_nodata_convention_is_detected(tmp_path):
    """NaN never equals itself, so ``== nodata`` counting must be NaN-aware."""
    from geocase.catalog.content import check_case_content
    from geocase.raster import raster_fixture

    spec = raster_fixture(dtype="float32", nodata=float("nan"), nodata_border=1)
    spec.write(tmp_path / "nan.tif")

    meta = _raster_metadata(
        "nan_nodata", "nan.tif", expect_nodata=True, nodata_convention="nan"
    )
    assert check_case_content(tmp_path, meta) == []


# --- 1.2.3: typed raster expectations -------------------------------------


def test_dtype_shape_and_band_count_mismatches_are_errors(tmp_path):
    from geocase.catalog.content import check_case_content
    from geocase.raster import raster_fixture

    spec = raster_fixture(bands=2, dtype="uint16", size=(8, 8))
    spec.write(tmp_path / "r.tif")

    meta = _raster_metadata(
        "typed",
        "r.tif",
        expected_dtype="float32",
        expected_shape=[16, 16],
        expected_band_count=3,
    )
    errors = check_case_content(tmp_path, meta)

    joined = " ".join(errors)
    assert "expected_dtype" in joined
    assert "expected_shape" in joined
    assert "expected_band_count" in joined


def test_expected_epsg_mismatch_is_an_error(tmp_path):
    from geocase.catalog.content import check_case_content
    from geocase.raster import raster_fixture

    spec = raster_fixture(crs="EPSG:32633")
    spec.write(tmp_path / "r.tif")

    meta = _raster_metadata("epsg", "r.tif", expected_epsg=4326)
    errors = check_case_content(tmp_path, meta)

    assert any("expected_epsg" in e for e in errors)


def test_matching_typed_expectations_pass(tmp_path):
    from geocase.catalog.content import check_case_content
    from geocase.raster import raster_fixture

    spec = raster_fixture(bands=2, dtype="uint16", size=(8, 8), crs="EPSG:32633")
    spec.write(tmp_path / "r.tif")

    meta = _raster_metadata(
        "typed_ok",
        "r.tif",
        expected_dtype="uint16",
        expected_shape=[8, 8],
        expected_band_count=2,
        expected_epsg=32633,
        expect_crs=True,
    )
    assert check_case_content(tmp_path, meta) == []


# --- 1.2.4: vector (the validated surface) --------------------------------


def test_vector_geometry_type_mismatch_is_an_error(tmp_path):
    pytest.importorskip("geopandas")
    from geocase.catalog.content import check_case_content

    _write_geojson(tmp_path / "v.geojson", [_point(0, 0)])
    meta = _vector_metadata(
        "geom_type", "v.geojson", expected_geometry_types=["Polygon"]
    )
    errors = check_case_content(tmp_path, meta)

    assert any("expected_geometry_types" in e for e in errors)


def test_vector_invalid_geometry_declared_valid_is_an_error(tmp_path):
    pytest.importorskip("geopandas")
    from geocase.catalog.content import check_case_content

    bowtie = {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]],
        },
    }
    _write_geojson(tmp_path / "v.geojson", [bowtie])
    meta = _vector_metadata("bowtie", "v.geojson", expect_valid_geometry=True)
    errors = check_case_content(tmp_path, meta)

    assert any("expect_valid_geometry" in e for e in errors)


def test_expect_valid_geometry_false_is_not_enforced_as_invalidity(tmp_path):
    """Phase 1 cut the tri-state field, so ``False`` stays unenforced.

    Four shipped cases (null island, a lat/lon swap, an engine-dependent
    touching ring, EMPTY-vs-NULL) are OGC-*valid* but semantically suspect.
    Asserting invalidity would fail them for a schema limitation.
    """
    pytest.importorskip("geopandas")
    from geocase.catalog.content import check_case_content

    _write_geojson(tmp_path / "v.geojson", [_point(0, 0)])
    meta = _vector_metadata(
        "null_island_like", "v.geojson", expect_valid_geometry=False
    )
    assert check_case_content(tmp_path, meta) == []


def test_null_geometries_do_not_break_the_geometry_type_check(tmp_path):
    """A NULL geometry reports ``geom_type`` NaN — not a type claim to satisfy."""
    pytest.importorskip("geopandas")
    from geocase.catalog.content import check_case_content

    null_feature = {"type": "Feature", "properties": {}, "geometry": None}
    _write_geojson(tmp_path / "v.geojson", [_point(0, 0), null_feature])

    meta = _vector_metadata("with_null", "v.geojson", expected_geometry_types=["Point"])
    assert check_case_content(tmp_path, meta) == []


def test_vector_declared_feature_count_is_checked(tmp_path):
    pytest.importorskip("geopandas")
    from geocase.catalog.content import check_case_content

    _write_geojson(tmp_path / "v.geojson", [_point(0, 0), _point(1, 1)])
    meta = _vector_metadata("fcount", "v.geojson")
    meta.params["expected_feature_count"] = 5
    errors = check_case_content(tmp_path, meta)

    assert any("expected_feature_count" in e for e in errors)


def test_vector_matching_declarations_pass(tmp_path):
    pytest.importorskip("geopandas")
    from geocase.catalog.content import check_case_content

    _write_geojson(tmp_path / "v.geojson", [_point(0, 0), _point(1, 1)])
    meta = _vector_metadata(
        "vec_ok",
        "v.geojson",
        expected_geometry_types=["Point"],
        expect_valid_geometry=True,
    )
    meta.params["expected_feature_count"] = 2
    assert check_case_content(tmp_path, meta) == []


# --- 1.2.5: expect_loadable: false must actually fail ----------------------


def test_expect_loadable_false_that_loads_fine_is_an_error(tmp_path):
    """An expected-failure that silently stopped failing is a corpus defect."""
    pytest.importorskip("geopandas")
    from geocase.catalog.content import check_case_content

    _write_geojson(tmp_path / "v.geojson", [_point(0, 0)])
    meta = _vector_metadata("should_fail", "v.geojson", expect_loadable=False)
    errors = check_case_content(tmp_path, meta)

    assert any("expect_loadable" in e for e in errors)


def test_expect_loadable_false_that_really_fails_passes(tmp_path):
    pytest.importorskip("geopandas")
    from geocase.catalog.content import check_case_content

    (tmp_path / "v.geojson").write_text("{ this is not json")
    meta = _vector_metadata("truly_broken", "v.geojson", expect_loadable=False)
    assert check_case_content(tmp_path, meta) == []


# --- 1.2.6: footprint derived from the actual mask ------------------------


def test_declared_footprint_hole_count_must_match_the_mask(tmp_path):
    """The check that catches ``hole_center_nodata``.

    A footprint claiming an interior void, over a raster whose nodata sits on
    the outer border, has zero holes in reality and one in the declaration.
    """
    from geocase.catalog.content import check_case_content
    from geocase.raster import raster_fixture

    # nodata on the border only -> footprint of valid data has NO hole
    spec = raster_fixture(dtype="float32", size=(12, 12), nodata=-9999, nodata_border=1)
    spec.write(tmp_path / "r.tif")

    # ...but the declared footprint claims a hole in the middle.
    declared = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
                        [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]],
                    ],
                },
            }
        ],
    }
    (tmp_path / "footprint.geojson").write_text(json.dumps(declared))

    meta = _raster_metadata("holey", "r.tif", expect_nodata=True)
    meta.params["expected_footprint"] = "footprint.geojson"
    errors = check_case_content(tmp_path, meta)

    assert any("expected_footprint" in e for e in errors), errors


def test_border_only_nodata_cannot_claim_footprint_generation_error(tmp_path):
    """The check that actually catches ``hole_center_nodata``.

    Its committed footprint was regenerated from the drifted raster, so the
    declaration and the mask agree -- both hole-free. Only the risk-type
    contract exposes it: a nodata collar cannot make a footprint generator
    diverge, so the case is inert for the risk it advertises.
    """
    import json

    from geocase.catalog.content import check_case_content
    from geocase.raster import raster_fixture

    spec = raster_fixture(dtype="float32", size=(12, 12), nodata=-9999, nodata_border=1)
    spec.write(tmp_path / "r.tif")

    # a footprint faithfully derived from that border-nodata raster: no hole
    declared = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]],
                },
            }
        ],
    }
    (tmp_path / "footprint.geojson").write_text(json.dumps(declared))

    meta = _raster_metadata("collar", "r.tif", expect_nodata=True)
    meta.params["expected_footprint"] = "footprint.geojson"
    meta.risk_types = ["footprint_generation_error"]
    errors = check_case_content(tmp_path, meta)

    assert any("footprint_generation_error" in e for e in errors), errors


def test_interior_void_satisfies_footprint_generation_error(tmp_path):
    """The shape ``hole_center_nodata`` has always claimed."""

    import numpy as np

    from geocase.catalog.content import check_case_content
    from geocase.raster import raster_fixture

    values = np.ones((1, 12, 12), dtype="float32")
    values[0, 4:8, 4:8] = -9999
    spec = raster_fixture(dtype="float32", size=(12, 12), nodata=-9999, values=values)
    spec.write(tmp_path / "r.tif")

    meta = _raster_metadata("void", "r.tif", expect_nodata=True)
    meta.risk_types = ["footprint_generation_error", "nodata_ignored"]
    assert check_case_content(tmp_path, meta) == []


def _two_island_raster(tmp_path):
    """A raster with two disjoint valid blobs."""
    import numpy as np

    from geocase.raster import raster_fixture

    values = np.full((1, 8, 8), -9999.0, dtype="float32")
    values[0, 0:3, 0:3] = 1.0
    values[0, 5:8, 5:8] = 1.0
    spec = raster_fixture(dtype="float32", size=(8, 8), nodata=-9999, values=values)
    spec.write(tmp_path / "r.tif")
    return tmp_path / "r.tif"


def _write_declared_footprint(tmp_path, geometry):
    (tmp_path / "footprint.geojson").write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "properties": {}, "geometry": geometry}
                ],
            }
        )
    )


def _mask_geometry(path):
    import rasterio.features
    from shapely.geometry import shape
    from shapely.ops import unary_union

    with rasterio.open(path) as src:
        mask = src.dataset_mask()
        parts = [
            shape(geom)
            for geom, value in rasterio.features.shapes(
                mask, mask=mask.astype(bool), transform=src.transform
            )
            if value != 0
        ]
    return unary_union(parts)


def test_declared_footprint_part_count_must_match_the_mask(tmp_path):
    """Plan 32 1.1 -- a convex hull over two islands is not the footprint.

    The hull is one polygon with no holes, so the hole-count check on its own
    is satisfied while the declaration merges two disjoint regions into one
    and nearly doubles the area. This is ``rotated_two_islands``.
    """
    pytest.importorskip("geopandas")

    from shapely.geometry import mapping

    from geocase.catalog.content import check_case_content

    raster = _two_island_raster(tmp_path)
    _write_declared_footprint(tmp_path, mapping(_mask_geometry(raster).convex_hull))

    meta = _raster_metadata("hull_over_islands", "r.tif", expect_nodata=True)
    meta.params["expected_footprint"] = "footprint.geojson"
    errors = check_case_content(tmp_path, meta)

    assert any("expected_footprint" in e for e in errors), errors
    assert any("part" in e for e in errors), errors
    assert any("area" in e for e in errors), errors


def test_mask_exact_declared_footprint_passes(tmp_path):
    """The control: the mask-derived geometry itself must be accepted."""
    pytest.importorskip("geopandas")

    from shapely.geometry import mapping

    from geocase.catalog.content import check_case_content

    raster = _two_island_raster(tmp_path)
    _write_declared_footprint(tmp_path, mapping(_mask_geometry(raster)))

    meta = _raster_metadata("islands_truth", "r.tif", expect_nodata=True)
    meta.params["expected_footprint"] = "footprint.geojson"
    assert check_case_content(tmp_path, meta) == []


# --- 1.3: risk_types as contract ------------------------------------------


def test_nodata_ignored_risk_requires_real_nodata_pixels(tmp_path):
    """Keyed on the vocabulary, not on prose: risk_types is checkable."""
    from geocase.catalog.content import check_case_content
    from geocase.raster import raster_fixture

    spec = raster_fixture(
        dtype="float32", nodata=-9999, nodata_border=0, fill="constant", constant=1.0
    )
    spec.write(tmp_path / "r.tif")

    meta = _raster_metadata("risk_case", "r.tif")
    meta.risk_types = ["nodata_ignored"]
    errors = check_case_content(tmp_path, meta)

    assert any("nodata_ignored" in e for e in errors)


# --- dispatch / missing files ---------------------------------------------


def test_missing_primary_file_is_reported_not_raised(tmp_path):
    from geocase.catalog.content import check_case_content

    meta = _raster_metadata("gone", "absent.tif", expect_nodata=True)
    errors = check_case_content(tmp_path, meta)

    assert len(errors) == 1
    assert "absent.tif" in errors[0]


# --- shape coverage across the bundled raster catalog ----------------------


def test_every_bundled_raster_case_declares_expected_shape():
    """A bundled raster whose pixels we ship should say what shape they are.

    ``expected_shape`` is also the selector that earns a case a pixel preview
    (see ``scripts/catalog_raster.preview_cases``), so an undeclared shape
    costs the catalog page its preview as well as the content check.
    """
    from geocase.catalog.registry import get_registry

    missing = sorted(
        case.id
        for case in get_registry().list_cases()
        if str(getattr(case.category, "value", case.category)) == "raster"
        and str(getattr(case.storage_class, "value", case.storage_class)) == "bundled"
        and (case.assertions is None or case.assertions.expected_shape is None)
    )

    assert missing == [], f"bundled raster cases with no expected_shape: {missing}"


# --- Plan 31: declared extent vs. the real bytes ---------------------------


def test_declared_extent_matching_the_data_passes(tmp_path):
    """A correct extent is silent, like every other satisfied declaration."""
    pytest.importorskip("geopandas")
    from geocase.catalog.content import check_case_content

    _write_geojson(tmp_path / "v.geojson", [_point(10.0, 50.0), _point(11.0, 51.0)])
    meta = _vector_metadata("in_place", "v.geojson")
    meta.extent = SpatialExtent(west=10.0, south=50.0, east=11.0, north=51.0)

    assert check_case_content(tmp_path, meta) == []


def test_declared_extent_in_the_wrong_place_is_an_error(tmp_path):
    """The failure this gate exists for: a box that is not where the data is.

    An extent is generated, so a stale one means a fixture moved and the page
    -- and the world map -- now point at the wrong continent.
    """
    pytest.importorskip("geopandas")
    from geocase.catalog.content import check_case_content

    _write_geojson(tmp_path / "v.geojson", [_point(10.0, 50.0), _point(11.0, 51.0)])
    meta = _vector_metadata("moved", "v.geojson")
    meta.extent = SpatialExtent(west=-120.0, south=30.0, east=-119.0, north=31.0)

    errors = check_case_content(tmp_path, meta)
    assert any("extent" in e for e in errors), errors


def test_no_declared_extent_is_not_checked(tmp_path):
    """The field is optional -- netcdf and the malformed cases carry none."""
    pytest.importorskip("geopandas")
    from geocase.catalog.content import check_case_content

    _write_geojson(tmp_path / "v.geojson", [_point(10.0, 50.0)])
    meta = _vector_metadata("no_extent", "v.geojson")

    assert meta.extent is None
    assert check_case_content(tmp_path, meta) == []


def test_assert_bounds_tolerates_small_drift():
    """Rounding to six decimals must not make a correct extent fail."""
    from geocase.assertions import assert_bounds

    assert_bounds(
        (10.0000001, 50.0, 11.0, 51.0),
        SpatialExtent(west=10.0, south=50.0, east=11.0, north=51.0),
    )


def test_assert_bounds_rejects_a_real_displacement():
    from geocase.assertions import assert_bounds

    with pytest.raises(AssertionError):
        assert_bounds(
            (10.0, 50.0, 11.0, 51.0),
            SpatialExtent(west=-120.0, south=30.0, east=-119.0, north=31.0),
        )


def test_assert_bounds_understands_the_antimeridian_wrap():
    """170..190 and the wrapped 170..-170 are the same box, not a 340 error."""
    from geocase.assertions import assert_bounds

    assert_bounds(
        (170.0, 40.0, 190.0, 50.0),
        SpatialExtent(west=170.0, south=40.0, east=-170.0, north=50.0),
    )

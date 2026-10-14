"""Geometry-operation comparison for the GEOS differential round (#48).

The readers (shapely, osgeo.ogr) need no stubbing: the compare function takes
the plain dicts they return, so these tests run without `osgeo`.
"""

from __future__ import annotations

from geocase.differential import compare_geometry_ops


def _ops(**overrides):
    ops = {
        "is_valid": True,
        "is_empty": False,
        "area": 12.0,
        "length": 14.0,
        "buffer0_area": 12.0,
        "centroid": [1.0, 2.0],
        "envelope": [0.0, 0.0, 4.0, 3.0],
        "make_valid_is_valid": True,
        "make_valid_type": "Polygon",
        "make_valid_area": 12.0,
        "simplify_area": 11.5,
        "union_area": 12.0,
        "union_type": "Polygon",
    }
    ops.update(overrides)
    return ops


def test_identical_ops_agree():
    assert compare_geometry_ops(_ops(), _ops()) is None


def test_exact_field_names_both_values():
    detail = compare_geometry_ops(_ops(), _ops(is_valid=False))
    assert detail is not None
    assert "is_valid" in detail and "True" in detail and "False" in detail


def test_area_within_relative_tolerance_agrees():
    assert compare_geometry_ops(_ops(area=1e6), _ops(area=1e6 * (1 + 1e-12))) is None


def test_area_outside_relative_tolerance_differs():
    detail = compare_geometry_ops(_ops(area=1e6), _ops(area=1e6 * (1 + 1e-6)))
    assert detail is not None and "area" in detail


def test_all_differences_are_reported():
    detail = compare_geometry_ops(
        _ops(), _ops(make_valid_type="MultiPolygon", length=15.0)
    )
    assert detail is not None
    assert "make_valid_type" in detail and "length" in detail


def test_centroid_compared_within_tolerance():
    assert compare_geometry_ops(_ops(), _ops(centroid=[1.0 + 1e-12, 2.0])) is None
    assert compare_geometry_ops(_ops(), _ops(centroid=[1.5, 2.0])) is not None


def test_nan_agrees_with_nan_and_not_with_a_number():
    nan = float("nan")
    assert compare_geometry_ops(_ops(area=nan), _ops(area=nan)) is None
    assert compare_geometry_ops(_ops(area=nan), _ops(area=1.0)) is not None


def test_none_centroid_on_both_sides_agrees():
    assert compare_geometry_ops(_ops(centroid=None), _ops(centroid=None)) is None
    assert compare_geometry_ops(_ops(), _ops(centroid=None)) is not None


def test_no_geometry_on_one_side_only_is_a_difference():
    assert compare_geometry_ops(None, None) is None
    detail = compare_geometry_ops(_ops(), None)
    assert detail is not None and "right" in detail


def test_a_side_that_could_not_run_an_op_is_a_difference():
    detail = compare_geometry_ops(_ops(), _ops(simplify_area=None))
    assert detail is not None and "simplify_area" in detail

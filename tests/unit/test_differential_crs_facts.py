"""CRS-facts comparison for the PROJ differential round (#47).

The readers (pyproj, osr) need no stubbing here: the compare function takes the
plain dicts they return, so these tests run without `osgeo`.
"""

from __future__ import annotations

from geocase.differential import compare_crs_facts


def _facts(**overrides):
    facts = {
        "authority": "EPSG:32633",
        "axis_order": ["E", "N"],
        "units": "metre",
        "is_geographic": False,
        "is_projected": True,
        "to_4326": [[15.0, 50.0], [16.0, 51.0]],
        "roundtrip": [[500000.0, 5538630.0], [570000.0, 5650000.0]],
    }
    facts.update(overrides)
    return facts


def test_identical_facts_agree():
    assert compare_crs_facts(_facts(), _facts()) is None


def test_scalar_difference_names_the_field_and_both_values():
    detail = compare_crs_facts(_facts(), _facts(axis_order=["N", "E"]))
    assert detail is not None
    assert "axis_order" in detail
    assert "['E', 'N']" in detail and "['N', 'E']" in detail


def test_authority_none_vs_code_is_a_difference():
    detail = compare_crs_facts(_facts(), _facts(authority=None))
    assert detail is not None
    assert "authority" in detail


def test_degree_difference_inside_tolerance_agrees():
    right = _facts(to_4326=[[15.0 + 1e-10, 50.0], [16.0, 51.0]])
    assert compare_crs_facts(_facts(), right) is None


def test_degree_difference_outside_tolerance_is_reported():
    right = _facts(to_4326=[[15.0 + 1e-7, 50.0], [16.0, 51.0]])
    detail = compare_crs_facts(_facts(), right)
    assert detail is not None
    assert "to_4326" in detail


def test_metre_difference_uses_the_metre_tolerance():
    inside = _facts(roundtrip=[[500000.0 + 1e-7, 5538630.0], [570000.0, 5650000.0]])
    outside = _facts(roundtrip=[[500000.0 + 1e-3, 5538630.0], [570000.0, 5650000.0]])
    assert compare_crs_facts(_facts(), inside) is None
    detail = compare_crs_facts(_facts(), outside)
    assert detail is not None
    assert "roundtrip" in detail


def test_geographic_roundtrip_uses_the_degree_tolerance():
    left = _facts(is_geographic=True, is_projected=False, units="degree")
    right = _facts(
        is_geographic=True,
        is_projected=False,
        units="degree",
        roundtrip=[[500000.0 + 1e-7, 5538630.0], [570000.0, 5650000.0]],
    )
    assert compare_crs_facts(left, right) is not None


def test_point_count_mismatch_is_reported():
    detail = compare_crs_facts(_facts(), _facts(to_4326=[[15.0, 50.0]]))
    assert detail is not None
    assert "to_4326" in detail


def test_nan_matches_nan_but_not_a_number():
    nan = float("nan")
    both = _facts(to_4326=[[nan, 50.0], [16.0, 51.0]])
    assert compare_crs_facts(both, both) is None
    assert compare_crs_facts(_facts(), both) is not None


def test_both_sides_without_a_crs_agree():
    assert compare_crs_facts(None, None) is None


def test_one_side_without_a_crs_is_a_difference():
    detail = compare_crs_facts(_facts(), None)
    assert detail is not None
    assert "no CRS" in detail


def test_several_differences_are_all_listed():
    detail = compare_crs_facts(_facts(), _facts(units="foot", is_projected=False))
    assert detail is not None
    assert "units" in detail and "is_projected" in detail

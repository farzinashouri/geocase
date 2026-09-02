"""Tests for the option-pair matrix and the smarter predicate — Plan 38 Phase 3.

Round 2 is the evidence for what an option axis is worth: **odc-stac's HIGH
defect needed ``crs=``**, **stackstac's needed ``dtype=``**, and odc-stac's
scale/offset defect needed a scaled case *and* a second library. A sweep
varying only library-vs-library on a plain read — Plan 37's recorded failure —
finds none of the three.

Phase 3.2 is the direct remedy for the five **false** lonboard findings: a
comparator that thinks ``OGC:CRS84`` and ``EPSG:4326`` are different CRSs, and
that cannot tell NULL from EMPTY from a NaN coordinate. Round 2 produced three
separate defects living exactly in the gaps between those three.

Phase 3.3 is ``known_divergences`` for probes rather than cases: the pyproj
sweep fired four probes and all four were expected behaviour. Without a keyed,
machine-readable explanation every run re-investigates the same four and the
fifth, real one is buried.
"""

from __future__ import annotations

import pytest

from geocase.differential import (
    OPTION_PAIRS,
    OptionPair,
    ProbeExplanation,
    compare_geometries,
    crs_equal,
    explain_divergence,
    option_pairs,
)


class TestOptionPairMatrix:
    """Ship the matrix as data, not as prose."""

    def test_the_matrix_is_not_empty_and_is_ordered(self):
        """Test the shipped pairs are a stable, inspectable sequence."""
        assert isinstance(OPTION_PAIRS, tuple)
        assert len(OPTION_PAIRS) >= 8
        assert all(isinstance(pair, OptionPair) for pair in OPTION_PAIRS)

    def test_every_axis_the_run_used_is_present(self):
        """Test the eight axes Phase 3.1 enumerates all ship."""
        names = {pair.name for pair in OPTION_PAIRS}
        assert names >= {
            "default",
            "explicit_crs",
            "resolution",
            "bounds",
            "nodata",
            "dtype",
            "resampling",
            "chunking",
        }

    def test_the_three_defect_finding_axes_are_marked_with_their_evidence(self):
        """Test the axes that actually found defects carry the citation."""
        by_name = {pair.name: pair for pair in OPTION_PAIRS}
        assert by_name["explicit_crs"].found_defect
        assert by_name["dtype"].found_defect
        assert "odc-stac" in by_name["explicit_crs"].evidence
        assert "stackstac" in by_name["dtype"].evidence

    def test_each_pair_carries_two_distinct_option_dicts(self):
        """Test a "pair" is a pair: two option sets that differ."""
        for pair in OPTION_PAIRS:
            assert isinstance(pair.left, dict)
            assert isinstance(pair.right, dict)
            assert pair.left != pair.right, pair.name

    def test_explicit_crs_offers_two_targets_one_changing_units(self):
        """Test the unit-changing target ships.

        It is a single option value, it found a HIGH defect, and it is the one
        a consumer author is least likely to think of testing.
        """
        pairs = [pair for pair in option_pairs(axis="explicit_crs")]
        targets = {
            str(value)
            for pair in pairs
            for options in (pair.left, pair.right)
            for value in options.values()
        }
        assert any("4326" in target for target in targets), targets
        assert any("32633" in target or "3857" in target for target in targets)

    def test_resolution_varies_above_and_below_native(self):
        """Test the resolution axis brackets native rather than only coarsens."""
        pair = next(pair for pair in OPTION_PAIRS if pair.name == "resolution")
        left = pair.left["resolution"]
        right = pair.right["resolution"]
        assert left != right
        assert min(left, right) < 10.0 < max(left, right)

    def test_option_pairs_can_be_filtered_to_the_defect_finding_axes(self):
        """Test a short sweep is expressible without hand-copying the matrix."""
        selected = option_pairs(found_defect=True)
        assert selected
        assert all(pair.found_defect for pair in selected)

    def test_an_unknown_axis_is_refused(self):
        """Test a typo yields an error rather than an empty sweep."""
        with pytest.raises(ValueError, match="axis"):
            option_pairs(axis="no_such_axis")


class TestCrsEquality:
    """The direct remedy for the five false lonboard findings."""

    def test_crs84_equals_epsg_4326(self):
        """Test the exact false finding: CRS84 and 4326 are the same CRS."""
        assert crs_equal("OGC:CRS84", "EPSG:4326")

    def test_epsg_4326_equals_itself_spelled_differently(self):
        """Test int, string and prefixed spellings agree."""
        assert crs_equal(4326, "EPSG:4326")
        assert crs_equal("epsg:4326", "EPSG:4326")

    def test_different_crss_are_not_equal(self):
        """Test the tolerance does not swallow a real CRS difference."""
        assert not crs_equal("EPSG:4326", "EPSG:32633")

    def test_axis_order_is_ignored_only_when_asked(self):
        """Test the caller chooses; the default does not silently flatten it."""
        assert crs_equal("OGC:CRS84", "EPSG:4326", ignore_axis_order=True)
        assert not crs_equal("EPSG:4326", "EPSG:32633", ignore_axis_order=True)

    def test_none_equals_none_and_not_a_crs(self):
        """Test a missing CRS is not accidentally equal to every CRS."""
        assert crs_equal(None, None)
        assert not crs_equal(None, "EPSG:4326")

    def test_default_compare_uses_it_on_crs_shaped_values(self):
        """Test the predicate reaches the harness, not just the unit test."""
        from geocase.differential import default_compare

        assert default_compare({"crs": "OGC:CRS84"}, {"crs": "EPSG:4326"}) is None


class TestGeometryComparison:
    """NULL, EMPTY and NaN-coordinate are three states, not one."""

    def test_null_and_empty_are_distinguished(self):
        """Test the gap round 2 produced a defect in."""
        shapely = pytest.importorskip("shapely")
        empty = shapely.from_wkt("POINT EMPTY")
        assert compare_geometries(None, empty) is not None
        assert "NULL" in compare_geometries(None, empty)

    def test_empty_and_nan_coordinate_are_distinguished(self):
        """Test a NaN-coordinate geometry is not reported as EMPTY."""
        shapely = pytest.importorskip("shapely")
        empty = shapely.from_wkt("POINT EMPTY")
        nan_point = shapely.from_wkt("POINT (nan nan)")
        detail = compare_geometries(empty, nan_point)
        assert detail is not None
        assert "EMPTY" in detail and "NaN" in detail

    def test_null_and_nan_coordinate_are_distinguished(self):
        """Test the third pairing in the same three-way gap."""
        shapely = pytest.importorskip("shapely")
        nan_point = shapely.from_wkt("POINT (nan nan)")
        detail = compare_geometries(None, nan_point)
        assert detail is not None
        assert "NULL" in detail and "NaN" in detail

    def test_two_nulls_agree(self):
        """Test the distinctions do not make identical inputs diverge."""
        assert compare_geometries(None, None) is None

    def test_two_empties_agree(self):
        """Test EMPTY compares equal to EMPTY of the same type."""
        shapely = pytest.importorskip("shapely")
        empty = shapely.from_wkt("POINT EMPTY")
        assert compare_geometries(empty, shapely.from_wkt("POINT EMPTY")) is None

    def test_two_nan_geometries_agree(self):
        """Test NaN-vs-NaN is agreement, as it is for arrays."""
        shapely = pytest.importorskip("shapely")
        nan_point = shapely.from_wkt("POINT (nan nan)")
        assert (
            compare_geometries(nan_point, shapely.from_wkt("POINT (nan nan)")) is None
        )

    def test_ordinary_geometries_still_compare(self):
        """Test the common path is untouched."""
        shapely = pytest.importorskip("shapely")
        assert (
            compare_geometries(
                shapely.from_wkt("POINT (1 2)"), shapely.from_wkt("POINT (1 2)")
            )
            is None
        )
        assert (
            compare_geometries(
                shapely.from_wkt("POINT (1 2)"), shapely.from_wkt("POINT (1 3)")
            )
            is not None
        )


class TestProbeExplanations:
    """``known_divergences`` for probes: keyed, so a repeat run classifies."""

    def test_the_four_pyproj_explanations_ship_keyed(self):
        """Test the run's four expected-behaviour classes are recorded."""
        from geocase.differential import PROBE_EXPLANATIONS

        keys = {explanation.key for explanation in PROBE_EXPLANATIONS}
        assert keys >= {
            "longitude_wrap",
            "pole_undefined_longitude",
            "float_noise",
            "identity_transform",
        }

    def test_an_explanation_carries_prose_and_a_predicate(self):
        """Test each is machine-readable, not a paragraph in a report."""
        from geocase.differential import PROBE_EXPLANATIONS

        for explanation in PROBE_EXPLANATIONS:
            assert isinstance(explanation, ProbeExplanation)
            assert explanation.description
            assert callable(explanation.matches)

    def test_longitude_wrap_is_classified_automatically(self):
        """Test a 180/-180 pair is explained, not re-investigated."""
        explanation = explain_divergence(
            "longitude differs: 180.0 vs -180.0", left=180.0, right=-180.0
        )
        assert explanation is not None
        assert explanation.key == "longitude_wrap"

    def test_float_noise_below_a_micrometre_is_classified(self):
        """Test sub-micrometre disagreement is expected, not a finding."""
        explanation = explain_divergence(
            "x differs", left=500000.0, right=500000.0000001
        )
        assert explanation is not None
        assert explanation.key == "float_noise"

    def test_a_real_divergence_is_not_explained_away(self):
        """Test the fifth, real one is still visible."""
        assert explain_divergence("x differs", left=500000.0, right=500123.0) is None

    def test_compare_case_reports_an_explained_divergence_as_known(self):
        """Test the classification reaches the harness's outcome."""
        from geocase.differential import compare_cases

        results = compare_cases(
            left=lambda path: 180.0,
            right=lambda path: -180.0,
            explain=True,
            include_ids=["dem_small"],
        )
        assert results[0].outcome == "known"
        assert results[0].probe_explanation is not None
        assert results[0].probe_explanation.key == "longitude_wrap"

    def test_explanations_are_off_by_default(self):
        """Test a caller who did not ask still sees the raw divergence."""
        from geocase.differential import compare_cases

        results = compare_cases(
            left=lambda path: 180.0,
            right=lambda path: -180.0,
            include_ids=["dem_small"],
        )
        assert results[0].outcome == "diverged"

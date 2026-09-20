"""Tests for *whose* failure mode a case is -- plan 44 phase 4.

Round 6's central structural gap. A consumer sweeping the corpus against GDAL
spends a full run discovering that the convention cases pass; a consumer
sweeping a downstream library needs exactly those cases first. The catalog
could not express the difference.

The evidence is the round itself. ``bottom_up_dem_small``,
``rotated_two_islands``, the ``pixel_is_point``/``pixel_is_area`` pair,
``dem_nan_nodata_small``, ``geotiff_int8_small``,
``landcover_ambiguous_zero_small`` and ``water_mask_small`` **all passed**
against GDAL ``d6fd56f52d`` -- while round 1 found rio-tiler mis-handling
``bottom_up_dem_small`` and round 4 found a P1 from ``rotated_two_islands``.
Those cases are failure modes *for consumers of GDAL*, not for GDAL. Their
value is that they catch everyone downstream who assumes a normalisation GDAL
performs and they do not.

Built as a ``failure_mode/*`` risk family rather than a parallel field (plan 44
phase 4.2), so it is selectable through the machinery that already exists and
a query for the whole half is ``risk_types_any=["failure_mode"]``.
"""

from __future__ import annotations

import pytest

import geocase

#: The convention cases round 6 proved GDAL handles correctly.
#:
#: The ``single_variable/`` controls (``bottom_up_only_square``,
#: ``rotated_only_square``) are deliberately absent. Each declares exactly one
#: risk type -- that single declaration *is* the control, and
#: ``tests/unit/test_single_variable_cases.py`` gates it. They pair with the
#: bundled cases listed here, which carry the marker for both.
CONSUMER_FAILURE_MODES = {
    "bottom_up_dem_small",
    "rotated_two_islands",
    "pixel_is_point_dem_small",
    "pixel_is_area_dem_small",
    "dem_nan_nodata_small",
    "geotiff_int8_small",
    "landcover_ambiguous_zero_small",
    "water_mask_small",
}

#: The cases that found a defect in the reference implementation itself.
REFERENCE_FAILURE_MODES = {
    "precision_loss_geojson_roundtrip",
    "optical_dateline_small",
    "optical_dateline_west_small",
    "numeric_boundary_15_significant_digits",
    "numeric_boundary_17_significant_digits",
    "numeric_boundary_trailing_zeros",
    "numeric_boundary_trailing_nines",
    "numeric_boundary_1e13",
    "numeric_boundary_1e14",
    "numeric_boundary_1e15",
}


class TestTheVocabularyExists:
    def test_both_terms_are_canonical(self):
        """Test the family is in the closed vocabulary, not free text."""
        from geocase.catalog.risk_types import RISK_TYPES

        assert "failure_mode/consumer" in RISK_TYPES
        assert "failure_mode/reference_implementation" in RISK_TYPES

    def test_the_family_has_more_than_one_member(self):
        """Plan 40: a family with one member is decoration."""
        from geocase.catalog.risk_types import families

        assert len(families()["failure_mode"]) >= 2


class TestTheConventionCasesAreMarked:
    @pytest.mark.parametrize("case_id", sorted(CONSUMER_FAILURE_MODES))
    def test_the_case_is_a_consumer_failure_mode(self, case_id: str):
        """Test each case GDAL handles correctly says so."""
        case = geocase.get_case(case_id)
        assert "failure_mode/consumer" in case.risk_types, (
            f"{case_id} passed against GDAL and found defects downstream -- "
            "it is a consumer failure mode and must say so"
        )

    @pytest.mark.parametrize("case_id", sorted(REFERENCE_FAILURE_MODES))
    def test_the_case_is_a_reference_implementation_failure_mode(self, case_id: str):
        """Test each case that reached GDAL itself says so."""
        case = geocase.get_case(case_id)
        assert "failure_mode/reference_implementation" in case.risk_types


class TestItIsSelectableBeforeTheRun:
    """Plan 44 phase 4.2 -- ask for the right half *before* sweeping, not after."""

    def test_the_consumer_half_selects_as_a_group(self):
        selected = {
            c.id for c in geocase.list_cases(risk_types_any=["failure_mode/consumer"])
        }
        assert CONSUMER_FAILURE_MODES <= selected

    def test_the_reference_half_selects_as_a_group(self):
        selected = {
            c.id
            for c in geocase.list_cases(
                risk_types_any=["failure_mode/reference_implementation"]
            )
        }
        assert REFERENCE_FAILURE_MODES <= selected

    def test_the_bare_family_prefix_selects_both_halves(self):
        """``failure_mode`` alone is the browsable form (plan 40 §3)."""
        selected = {c.id for c in geocase.list_cases(risk_types_any=["failure_mode"])}
        assert CONSUMER_FAILURE_MODES <= selected
        assert REFERENCE_FAILURE_MODES <= selected

    def test_the_two_halves_do_not_overlap(self):
        """A case is one kind or the other; both would make the split useless."""
        for case in geocase.list_cases():
            assert not (
                "failure_mode/consumer" in case.risk_types
                and "failure_mode/reference_implementation" in case.risk_types
            ), f"{case.id} claims to be both kinds of failure mode"

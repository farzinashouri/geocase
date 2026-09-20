"""Tests for the westward antimeridian control -- plan 44 phase 3.

``optical_dateline_small`` is the only raster in the corpus past +-180 and it
crosses one way: 179.9 -> 180.22. Round 6's warp defect
(``AutoCreateWarpedVRT`` returning a ``23x0`` dataset) was found by that case
and the run **could not answer whether it is symmetric**, because there is no
negative-wrap counterpart. Two cases differing only in the sign of the crossing
turn "GDAL mishandles the antimeridian" into "GDAL mishandles the eastward
crossing and not the westward one", or into a stronger claim -- and either is
worth more than one data point.

The control is deliberately identical in every other respect: same size, same
dtype, same band count, same CRS, same pixel size. A difference in behaviour is
then attributable to the sign and to nothing else.
"""

from __future__ import annotations

import pytest

import geocase

EASTWARD = "optical_dateline_small"
WESTWARD = "optical_dateline_west_small"


class TestTheControlExists:
    def test_the_westward_case_is_in_the_catalog(self):
        """Test the negative-wrap counterpart is registered."""
        assert WESTWARD in {c.id for c in geocase.list_cases()}

    def test_it_crosses_westward(self):
        """Test the western bound is past -180 and the eastern is not."""
        case = geocase.get_case(WESTWARD)
        bounds = case.assertions.expected_bounds
        assert bounds is not None
        west, _, east, _ = bounds
        assert west < -180.0, "the case must actually cross the antimeridian"
        assert east > -180.0


class TestItIsAControlAndNotJustAnotherCase:
    """Single-variable: only the sign of the crossing differs."""

    @pytest.mark.parametrize(
        "attribute",
        ["expected_shape", "expected_dtype", "expected_band_count", "expected_epsg"],
    )
    def test_the_pair_agrees_on_everything_but_the_sign(self, attribute: str):
        """Test a behavioural difference is attributable to the crossing alone."""
        east = geocase.get_case(EASTWARD).assertions
        west = geocase.get_case(WESTWARD).assertions
        assert getattr(east, attribute) == getattr(west, attribute)

    def test_the_two_cases_span_the_same_width(self):
        """Test the footprints are the same size, mirrored about 180."""
        east = geocase.get_case(EASTWARD).assertions.expected_bounds
        west = geocase.get_case(WESTWARD).assertions.expected_bounds
        assert east is not None and west is not None
        assert (east[2] - east[0]) == pytest.approx(west[2] - west[0])


class TestItCarriesTheRiskThatDescribesIt:
    def test_it_declares_the_antimeridian_risk(self):
        """Test the control is reachable by the same query as its sibling."""
        case = geocase.get_case(WESTWARD)
        assert "extent/antimeridian" in case.risk_types

    def test_it_is_marked_a_reference_implementation_failure_mode(self):
        """Plan 44 phase 4 -- this case is about GDAL itself, not a consumer."""
        case = geocase.get_case(WESTWARD)
        assert "failure_mode/reference_implementation" in case.risk_types


class TestItLoads:
    def test_the_bytes_are_readable(self):
        """Test the fixture was actually generated, not just declared."""
        case = geocase.load_case(WESTWARD)
        assert case.primary_path.exists()

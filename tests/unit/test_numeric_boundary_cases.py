"""Tests for the numeric-boundary family -- plan 44 phase 2.

Round 6's first defect was found by ``precision_loss_geojson_roundtrip``
feature 3, and it was found **by luck**: that case carries three points and the
third happens to sit at ``1e-14``, the single magnitude where the significant
digit lands on the one string position GDAL's ``intelliround`` does not test. A
case chosen for "very small values near zero" is not the same as a case
designed against the *formatter*, and the difference is the whole finding.

These cases are the designed version: single-variable per plan 40's control
principle, one property per case, and each ships the value it must round-trip
to as a typed hint rather than leaving every consumer to re-derive what
"survived" means.
"""

from __future__ import annotations

import json

import pytest

import geocase

#: ``case id -> the coordinate property it isolates``.
FAMILY = {
    "numeric_boundary_15_significant_digits": "needs exactly 15 digits",
    "numeric_boundary_17_significant_digits": "needs 17 digits to round-trip",
    "numeric_boundary_trailing_zeros": "five 0s at 15 decimal places",
    "numeric_boundary_trailing_nines": "five 9s at 15 decimal places",
    "numeric_boundary_1e13": "above the affected class",
    "numeric_boundary_1e14": "inside the affected class",
    "numeric_boundary_1e15": "below the affected class",
}


@pytest.fixture(scope="module")
def case_ids() -> set[str]:
    return {c.id for c in geocase.list_cases()}


class TestTheFamilyExists:
    @pytest.mark.parametrize("case_id", sorted(FAMILY))
    def test_the_case_is_in_the_catalog(self, case_id: str, case_ids: set[str]):
        """Test each numeric-boundary case is registered."""
        assert case_id in case_ids

    @pytest.mark.parametrize("case_id", sorted(FAMILY))
    def test_the_case_loads(self, case_id: str):
        """Test the declared bytes are actually readable."""
        case = geocase.load_case(case_id)
        assert case.primary_path.exists()


class TestTheBoundaryIsBracketed:
    """``1e-14`` alone is a hit; ``1e-13``/``1e-14``/``1e-15`` is a bracket."""

    @pytest.mark.parametrize(
        ("case_id", "magnitude"),
        [
            ("numeric_boundary_1e13", 1e-13),
            ("numeric_boundary_1e14", 1e-14),
            ("numeric_boundary_1e15", 1e-15),
        ],
    )
    def test_the_case_carries_its_magnitude(self, case_id: str, magnitude: float):
        """Test the file really holds the magnitude the id claims."""
        case = geocase.load_case(case_id)
        raw = json.loads(case.primary_path.read_text())
        coords = raw["features"][0]["geometry"]["coordinates"]
        assert coords[0] == pytest.approx(magnitude, rel=1e-12)


class TestTheExpectedAnswerIsShipped:
    """Plan 44 phase 2.2 -- a typed hint, not ``params``.

    ``params`` is ``dict[str, Any]`` with no validator, so an unrecognised key
    there is silence. The whole point of the family is that a consumer can be
    *graded*, which needs the right answer in a field the content gate can
    reach.
    """

    @pytest.mark.parametrize("case_id", sorted(FAMILY))
    def test_the_case_declares_its_roundtrip_coordinates(self, case_id: str):
        """Test the value that must survive a write/read cycle is declared."""
        case = geocase.get_case(case_id)
        pairs = case.assertions.expected_roundtrip_coordinates
        assert pairs, f"{case_id} must ship the coordinates it must round-trip to"
        for pair in pairs:
            assert len(pair) == 2

    @pytest.mark.parametrize("case_id", sorted(FAMILY))
    def test_the_declared_coordinates_match_the_bytes(self, case_id: str):
        """A hint that disagrees with the file is worse than no hint."""
        meta = geocase.get_case(case_id)
        case = geocase.load_case(case_id)
        raw = json.loads(case.primary_path.read_text())
        actual = [f["geometry"]["coordinates"] for f in raw["features"]]
        assert meta.assertions.expected_roundtrip_coordinates == actual


class TestTheVocabulary:
    """Plan 44 phase 2.3 -- the corpus had one such case and called it
    ``precision_loss``, a singleton among the 78 plan 40 measured."""

    @pytest.mark.parametrize("case_id", sorted(FAMILY))
    def test_the_case_declares_a_numeric_boundary_risk(self, case_id: str):
        """Test each case is reachable by the risk that describes it."""
        case = geocase.get_case(case_id)
        assert any(
            t.startswith("precision/") for t in case.risk_types
        ), f"{case_id} declares no precision risk"
        assert "precision/formatter_boundary" in case.risk_types

    def test_the_family_is_selectable_as_a_group(self):
        """A harness must be able to ask for the boundary set before it runs."""
        selected = {
            c.id
            for c in geocase.list_cases(
                risk_types_any=["precision/formatter_boundary"]
            )
        }
        assert set(FAMILY) <= selected


class TestSingleVariable:
    """Plan 40's control principle: one property per case, so a failure names
    the property."""

    @pytest.mark.parametrize("case_id", sorted(FAMILY))
    def test_each_case_carries_one_feature(self, case_id: str):
        """Test the stimulus is not diluted by unrelated coordinates."""
        case = geocase.load_case(case_id)
        raw = json.loads(case.primary_path.read_text())
        assert len(raw["features"]) == 1

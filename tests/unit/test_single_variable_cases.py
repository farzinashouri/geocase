"""The single-variable controls -- plan 40 phase 4.

Round 3's fifth observation: ``rotated_two_islands`` was the round's one
genuine discovery, but it bundles rotation *with* sparse islands *with*
footprint generation. The reporter wanted rotation **alone**, with a
known-correct answer, so ``_get_bounds`` could be proved wrong without
arguing about the islands.

> A failure with one possible cause is a better bug-finder than a case
> combining three risks.

These three isolate one variable each and ship plan 40 phase 2's ground truth,
so a defect that reproduces on the isolated case and not on the bundled one
localises itself. That is the entire argument for them: they are **controls**,
not coverage. No new ``from_origin`` baselines -- plans 37 and 38 both record
that the corpus is thick there and thin on convention divergence.
"""

from __future__ import annotations

import pytest

import geocase

ROTATED_ONLY = "rotated_only_square"
NODATA_ONLY = "nodata_only_dem_small"
BOTTOM_UP_ONLY = "bottom_up_only_square"
ALL_THREE = [ROTATED_ONLY, NODATA_ONLY, BOTTOM_UP_ONLY]


@pytest.mark.parametrize("case_id", ALL_THREE)
def test_the_case_is_registered(case_id: str) -> None:
    assert geocase.get_case(case_id).id == case_id


@pytest.mark.parametrize("case_id", ALL_THREE)
def test_every_control_declares_its_bounds(case_id: str) -> None:
    """The reporter's explicit ask: a known-correct bounding box."""
    bounds = geocase.get_case(case_id).assertions.expected_bounds
    assert bounds is not None and len(bounds) == 4


@pytest.mark.parametrize("case_id", ALL_THREE)
def test_the_declared_bounds_match_the_real_bytes(case_id: str) -> None:
    """Declared, generated and gated -- never hand-authored."""
    rasterio = pytest.importorskip("rasterio")
    del rasterio

    case = geocase.load_case(case_id)
    with case.open() as src:
        actual = [float(v) for v in src.bounds]
    assert actual == pytest.approx(case.metadata.assertions.expected_bounds)


class TestRotatedOnly:
    """Rotation with nothing else: no nodata, no islands, no sparse footprint."""

    def test_the_transform_is_actually_rotated(self) -> None:
        pytest.importorskip("rasterio")
        with geocase.load_case(ROTATED_ONLY).open() as src:
            assert src.transform.b != 0 or src.transform.d != 0

    def test_it_carries_no_nodata_at_all(self) -> None:
        """A nodata pixel would be a second variable, which is the point."""
        pytest.importorskip("rasterio")
        assert geocase.get_case(ROTATED_ONLY).assertions.nodata_pixel_count == 0
        with geocase.load_case(ROTATED_ONLY).open() as src:
            assert src.nodata is None

    def test_it_ships_the_pixel_world_round_trip(self) -> None:
        """The oracle the reporter had to hand-roll on rotated_two_islands."""
        pairs = geocase.get_case(ROTATED_ONLY).assertions.expected_pixel_world_pairs
        assert pairs and all(len(p) == 4 for p in pairs)

    def test_it_declares_only_the_rotation_risk(self) -> None:
        """One possible cause, so a failure localises without argument."""
        assert geocase.get_case(ROTATED_ONLY).risk_types == ["transform/rotated"]


class TestNodataOnly:
    """One sentinel nodata value, north-up, unrotated."""

    def test_the_transform_is_plain_north_up(self) -> None:
        pytest.importorskip("rasterio")
        with geocase.load_case(NODATA_ONLY).open() as src:
            assert src.transform.b == 0 and src.transform.d == 0
            assert src.transform.e < 0

    def test_it_ships_both_means_and_they_differ(self) -> None:
        """The gap between them *is* the defect a consumer is graded on."""
        hints = geocase.get_case(NODATA_ONLY).assertions
        assert hints.expected_mean_masked is not None
        assert hints.expected_mean_naive is not None
        assert hints.expected_mean_masked != hints.expected_mean_naive
        assert hints.nodata_pixel_count and hints.nodata_pixel_count > 0

    def test_it_declares_only_the_nodata_risk(self) -> None:
        assert geocase.get_case(NODATA_ONLY).risk_types == ["nodata/ignored"]


class TestBottomUpOnly:
    """A positive-e affine alone -- no rotation, no nodata."""

    def test_the_transform_is_bottom_up_and_unrotated(self) -> None:
        pytest.importorskip("rasterio")
        with geocase.load_case(BOTTOM_UP_ONLY).open() as src:
            assert src.transform.e > 0
            assert src.transform.b == 0 and src.transform.d == 0

    def test_it_declares_only_the_bottom_up_risk(self) -> None:
        assert geocase.get_case(BOTTOM_UP_ONLY).risk_types == ["transform/bottom_up"]


def test_the_controls_pair_with_the_bundled_cases_they_isolate() -> None:
    """A control is only useful if its bundled counterpart is still there.

    ``rotated_only_square`` localises a defect *against* ``rotated_two_islands``;
    delete either half and the comparison that makes them controls is gone.
    """
    for bundled in ("rotated_two_islands", "bottom_up_dem_small"):
        assert geocase.get_case(bundled)

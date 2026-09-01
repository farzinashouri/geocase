"""Tests for ``CaseMetadata.known_divergences`` — Plan 28 phase 2.5.

A divergence that is catalogued once stays catalogued: the next person to run a
differential harness over the corpus can tell "the bug we already filed" from
"something new appeared". Without it, ``empty_geometry_gpkg`` costs every user
the same investigation, and — worse — a *newly introduced* consumer bug on the
same case is indistinguishable from the one already understood.

The field is a record, not an assertion. Nothing in the content gate can verify
it: whether pyogrio 0.12 still returns the extra row depends on the pyogrio the
reader has installed, not on geocase's bytes. What *is* gated here is that the
record is well-formed and attached to the case it describes.
"""

from __future__ import annotations

import pytest

import geocase


@pytest.fixture(scope="module")
def cases() -> list[geocase.CaseMetadata]:
    return geocase.list_cases()


class TestTheSeededRecord:
    """The finding the external pyogrio run asked to be made cumulative."""

    def test_empty_geometry_gpkg_carries_the_pyogrio_arrow_divergence(self):
        """Test the GPKG spatial-filter finding is recorded on its own case."""
        case = geocase.get_case("empty_geometry_gpkg")
        assert case.known_divergences

        pyogrio = [d for d in case.known_divergences if d.consumer == "pyogrio"]
        assert pyogrio, "the case that found the GDAL bug must name pyogrio"

    def test_the_record_links_the_upstream_issue(self):
        """Test a reader can get from the case to the filed bug in one hop."""
        case = geocase.get_case("empty_geometry_gpkg")
        divergence = case.known_divergences[0]

        assert divergence.upstream_url is not None
        assert divergence.upstream_url.startswith("https://")

    def test_the_record_names_the_versions_it_was_observed_in(self):
        """Test "is this still open?" is answerable without re-running anything."""
        case = geocase.get_case("empty_geometry_gpkg")
        divergence = case.known_divergences[0]

        assert divergence.version_range


class TestTheRestOfTheCorpus:
    """An empty default outside the recorded runs, so ``[]`` keeps meaning
    "not seen"."""

    def test_only_the_cases_with_real_findings_declare_records(
        self, cases: list[geocase.CaseMetadata]
    ):
        """Test the metadata pass touched only cases with a real finding."""
        declared = {c.id for c in cases if c.known_divergences}
        assert declared == {
            "empty_geometry_gpkg",
            "rotated_two_islands",
            "bottom_up_dem_small",
            "ndvi_scaled_int16_small",
            "landcover_small",
            "optical_dateline_small",
            "empty_polygon",
            "geometrycollection_mixed_valid",
        }

    def test_every_declared_record_is_attributed_and_described(
        self, cases: list[geocase.CaseMetadata]
    ):
        """Test no case ships a record a reader cannot act on."""
        for case in cases:
            for divergence in case.known_divergences:
                assert divergence.consumer.strip()
                assert divergence.description.strip()


class TestRoundTwoConsumerDivergences:
    """Plan 38 phase 1.1 -- the 2026-08-31 six-consumer differential run.

    Ten records over eight cases. Each is a *consumer* defect found by a
    specific case, so the record belongs on that case: a repeat run reports
    ``known`` instead of re-deriving the same investigation, and a genuinely
    new defect on the same case stays distinguishable.

    The two stackstac defects the same run found are deliberately absent. One
    fires on any STAC Item and the other on all 34 rasters identically, so
    neither is attributable to a case; recording them here would be a false
    claim about which case found what.
    """

    EXPECTED = {
        ("rotated_two_islands", "titiler"),
        ("bottom_up_dem_small", "titiler"),
        ("bottom_up_dem_small", "rio-stac"),
        ("ndvi_scaled_int16_small", "odc-stac"),
        ("landcover_small", "titiler"),
        ("optical_dateline_small", "titiler"),
        ("empty_geometry_gpkg", "lonboard"),
        ("empty_polygon", "lonboard"),
        ("empty_polygon", "geoarrow-pyarrow"),
        ("geometrycollection_mixed_valid", "geoarrow-pyarrow"),
    }

    @pytest.mark.parametrize(("case_id", "consumer"), sorted(EXPECTED))
    def test_the_case_records_the_consumer_that_diverged(
        self, case_id: str, consumer: str
    ):
        """Test each round-2 finding is attributed to the case that found it."""
        case = geocase.get_case(case_id)
        matches = [d for d in case.known_divergences if d.consumer == consumer]
        assert matches, f"{case_id} must record a divergence for {consumer}"

    def test_no_stackstac_record_is_attributed_to_any_case(
        self, cases: list[geocase.CaseMetadata]
    ):
        """Test the two non-case-attributable defects are not claimed by a case."""
        for case in cases:
            for divergence in case.known_divergences:
                assert divergence.consumer != "stackstac", (
                    f"{case.id} claims a stackstac defect that fires on every "
                    "input -- not a case-attributable finding"
                )

    def test_every_round_two_record_names_the_versions_observed(self):
        """Test each record answers "is this still open?" without a re-run."""
        for case_id, consumer in self.EXPECTED:
            case = geocase.get_case(case_id)
            for divergence in case.known_divergences:
                if divergence.consumer == consumer:
                    assert divergence.version_range


class TestRoundOneConsumerDivergences:
    """Plan 37 phase 1.1 -- the 2026-08-31 four-consumer differential run.

    The run that produced Plan 37: rio-tiler 9.4.3 returns geographically wrong
    pixels for a rotated affine, and inverted bounds for a bottom-up one. Both
    are silent, and both were found by the corpus's only case carrying the
    convention.

    Recorded separately from the round-2 titiler records even though titiler
    republishes the same two rio-tiler defects over HTTP. ``_match_known``
    matches on consumer name alone, so a titiler record does not excuse a
    rio-tiler run: without its own record, a differential run passing
    ``consumer="rio-tiler"`` reports both as new findings and re-derives an
    investigation that is already closed.
    """

    EXPECTED = {
        ("rotated_two_islands", "rio-tiler"),
        ("bottom_up_dem_small", "rio-tiler"),
    }

    @pytest.mark.parametrize(("case_id", "consumer"), sorted(EXPECTED))
    def test_the_case_records_the_consumer_that_diverged(
        self, case_id: str, consumer: str
    ):
        """Test each round-1 finding is attributed to the case that found it."""
        case = geocase.get_case(case_id)
        matches = [d for d in case.known_divergences if d.consumer == consumer]
        assert matches, f"{case_id} must record a divergence for {consumer}"

    def test_every_round_one_record_names_the_version_observed(self):
        """Test each record answers "is this still open?" without a re-run."""
        for case_id, consumer in self.EXPECTED:
            case = geocase.get_case(case_id)
            for divergence in case.known_divergences:
                if divergence.consumer == consumer:
                    assert "9.4.3" in divergence.version_range

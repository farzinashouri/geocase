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
    """An empty default everywhere else, so ``[]`` keeps meaning "not seen"."""

    def test_every_other_case_declares_none(self, cases: list[geocase.CaseMetadata]):
        """Test the metadata pass touched only the case with a real finding."""
        declared = {c.id for c in cases if c.known_divergences}
        assert declared == {"empty_geometry_gpkg"}

    def test_every_declared_record_is_attributed_and_described(
        self, cases: list[geocase.CaseMetadata]
    ):
        """Test no case ships a record a reader cannot act on."""
        for case in cases:
            for divergence in case.known_divergences:
                assert divergence.consumer.strip()
                assert divergence.description.strip()

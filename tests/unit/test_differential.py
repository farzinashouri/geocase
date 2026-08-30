"""Tests for ``geocase.differential`` — Plan 28 phase 2.6.

The external pyogrio run's own conclusion: *"the most productive thing built
here was ~100 lines: read every case two ways, compare, report divergences"*.
Both bugs that run found came from comparing a consumer against **itself**, not
against geocase's declared assertions — so this is the mode the evidence backs,
and shipping it means the next user finds bugs on day one instead of writing
the harness first.

What these tests pin:

* the four outcomes, and that they are distinguishable — ``agree``, ``diverged``,
  ``known`` (a divergence already catalogued in ``known_divergences``), and
  ``errored`` (one or both paths raised);
* that a curated-failure case raising in *both* paths is agreement, not a
  divergence — the two paths agree that it fails;
* that the default comparison understands GeoDataFrames, which is the shape
  the evidenced use actually produces.
"""

from __future__ import annotations

import json

import pytest

from geocase.catalog.models import (
    AssertionHints,
    CaseMetadata,
    FileMap,
    KnownDivergence,
)


def _case(case_id: str, primary: str, **overrides) -> CaseMetadata:
    base = {
        "id": case_id,
        "title": case_id,
        "category": "vector",
        "format": "GeoJSON",
        "test_tier": "unit",
        "size_class": "tiny",
        "storage_class": "bundled",
        "redistributable": True,
        "schema_version": "1.0",
        "loader_hint": "geopandas",
        "files": FileMap(primary=primary),
        "assertions": AssertionHints(),
    }
    base.update(overrides)
    return CaseMetadata(**base)


def _write_points(path, count: int) -> None:
    features = [
        {
            "type": "Feature",
            "properties": {"v": i},
            "geometry": {"type": "Point", "coordinates": [float(i), 0.0]},
        }
        for i in range(count)
    ]
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))


# --- the four outcomes ----------------------------------------------------


class TestOutcomes:
    def test_two_paths_returning_the_same_thing_agree(self, tmp_path):
        """Test the ordinary case: both readers see the same data."""
        from geocase.differential import compare_case

        _write_points(tmp_path / "p.geojson", 3)
        meta = _case("agreeing", "p.geojson")

        result = compare_case(
            tmp_path, meta, left=lambda p: p.read_text(), right=lambda p: p.read_text()
        )

        assert result.outcome == "agree"
        assert result.case_id == "agreeing"
        assert result.detail is None

    def test_two_paths_returning_different_things_diverge(self, tmp_path):
        """Test the finding this module exists to surface."""
        from geocase.differential import compare_case

        _write_points(tmp_path / "p.geojson", 3)
        meta = _case("diverging", "p.geojson")

        result = compare_case(
            tmp_path,
            meta,
            left=lambda p: 2,
            right=lambda p: 3,
        )

        assert result.outcome == "diverged"
        assert result.detail

    def test_a_catalogued_divergence_is_reported_as_known(self, tmp_path):
        """Test the 2.5 record turns a repeat finding into a non-finding."""
        from geocase.differential import compare_case

        _write_points(tmp_path / "p.geojson", 3)
        meta = _case(
            "catalogued",
            "p.geojson",
            known_divergences=[
                KnownDivergence(
                    consumer="pyogrio",
                    description="Arrow path keeps NULL geometries under a filter",
                )
            ],
        )

        result = compare_case(
            tmp_path, meta, left=lambda p: 2, right=lambda p: 3, consumer="pyogrio"
        )

        assert result.outcome == "known"
        assert result.known_divergence is not None
        assert result.known_divergence.consumer == "pyogrio"

    def test_a_divergence_catalogued_for_another_consumer_is_still_a_finding(
        self, tmp_path
    ):
        """Test a record only excuses the consumer it was recorded against.

        Otherwise one catalogued fiona quirk would silence every future pyogrio
        divergence on the same case -- exactly the "cannot tell a new bug from
        the known one" problem 2.5 exists to fix.
        """
        from geocase.differential import compare_case

        _write_points(tmp_path / "p.geojson", 3)
        meta = _case(
            "other_consumer",
            "p.geojson",
            known_divergences=[
                KnownDivergence(consumer="fiona", description="something else")
            ],
        )

        result = compare_case(
            tmp_path, meta, left=lambda p: 2, right=lambda p: 3, consumer="pyogrio"
        )

        assert result.outcome == "diverged"

    def test_one_path_raising_is_an_error_not_a_divergence(self, tmp_path):
        """Test a crash is reported as its own outcome, with the exception."""
        from geocase.differential import compare_case

        _write_points(tmp_path / "p.geojson", 3)
        meta = _case("half_broken", "p.geojson")

        def boom(path):
            raise ValueError("Index data must be 1-dimensional")

        result = compare_case(tmp_path, meta, left=lambda p: 2, right=boom)

        assert result.outcome == "errored"
        assert "1-dimensional" in result.detail

    def test_both_paths_raising_the_same_way_agree(self, tmp_path):
        """Test a curated-failure case is agreement: both paths reject it.

        ``unclosed_ring_polygon`` is meant to fail. A harness that called that
        a divergence would report a finding on every expected failure in the
        corpus, which is noise that hides the real ones.
        """
        from geocase.differential import compare_case

        _write_points(tmp_path / "p.geojson", 3)
        meta = _case("expected_failure", "p.geojson")

        def boom(path):
            raise ValueError("unclosed ring")

        result = compare_case(tmp_path, meta, left=boom, right=boom)

        assert result.outcome == "agree"

    def test_both_paths_raising_differently_is_a_divergence(self, tmp_path):
        """Test failing for two different reasons is itself the finding."""
        from geocase.differential import compare_case

        _write_points(tmp_path / "p.geojson", 3)
        meta = _case("two_failures", "p.geojson")

        def left(path):
            raise ValueError("unclosed ring")

        def right(path):
            raise TypeError("something else entirely")

        result = compare_case(tmp_path, meta, left=left, right=right)

        assert result.outcome == "diverged"


# --- the default comparison -----------------------------------------------


class TestDefaultComparison:
    """The shape the evidenced use produces is a GeoDataFrame."""

    def test_identical_geodataframes_compare_equal(self, tmp_path):
        """Test two reads of the same file agree, despite `==` being elementwise."""
        gpd = pytest.importorskip("geopandas")
        from geocase.differential import compare_case

        _write_points(tmp_path / "p.geojson", 3)
        meta = _case("gdf_agree", "p.geojson")

        reader = lambda p: gpd.read_file(p)  # noqa: E731
        result = compare_case(tmp_path, meta, left=reader, right=reader)

        assert result.outcome == "agree"

    def test_a_differing_row_count_is_the_divergence(self, tmp_path):
        """Test the exact shape of the GPKG finding: 2 rows against 3."""
        gpd = pytest.importorskip("geopandas")
        from geocase.differential import compare_case

        _write_points(tmp_path / "p.geojson", 3)
        meta = _case("gdf_rows", "p.geojson")

        result = compare_case(
            tmp_path,
            meta,
            left=lambda p: gpd.read_file(p).iloc[:2],
            right=lambda p: gpd.read_file(p),
        )

        assert result.outcome == "diverged"
        assert "2" in result.detail and "3" in result.detail

    def test_none_and_nan_are_the_same_missing_value(self, tmp_path):
        """Test the noise the external run predicted is not reported as a finding.

        Seven KML cases in the shipped corpus return ``None`` on pyogrio's
        numpy path and ``nan`` on its Arrow path for the same absent field.
        Both mean absent; reporting them buries the one real divergence.
        """
        pytest.importorskip("geopandas")
        from geocase.differential import default_compare

        assert default_compare(None, float("nan")) is None
        assert default_compare(float("nan"), None) is None

    def test_an_empty_string_is_not_a_missing_value(self, tmp_path):
        """Test the tolerance stops at absence: "" is a value a reader returned."""
        from geocase.differential import default_compare

        assert default_compare(None, "") is not None
        assert default_compare("", 0) is not None

    def test_a_differing_column_set_is_a_divergence(self, tmp_path):
        """Test the dtype/column noise a real run has to see, not swallow."""
        gpd = pytest.importorskip("geopandas")
        from geocase.differential import compare_case

        _write_points(tmp_path / "p.geojson", 3)
        meta = _case("gdf_cols", "p.geojson")

        result = compare_case(
            tmp_path,
            meta,
            left=lambda p: gpd.read_file(p),
            right=lambda p: gpd.read_file(p).drop(columns=["v"]),
        )

        assert result.outcome == "diverged"
        assert "v" in result.detail


# --- running over the corpus ----------------------------------------------


class TestRunOverTheCorpus:
    def test_compares_every_selected_case(self):
        """Test the batch entry point walks the real catalog."""
        from geocase.differential import compare_cases

        results = compare_cases(
            left=lambda p: p.stat().st_size,
            right=lambda p: p.stat().st_size,
            category="vector",
        )

        assert len(results) > 50
        assert all(r.outcome == "agree" for r in results)

    def test_a_report_separates_known_from_new(self):
        """Test the summary a repeat run actually reads."""
        from geocase.differential import compare_cases, summarize

        results = compare_cases(
            left=lambda p: p.stat().st_size,
            right=lambda p: p.stat().st_size,
            category="vector",
        )
        summary = summarize(results)

        assert summary["agree"] == len(results)
        assert summary["diverged"] == 0
        assert summary["known"] == 0
        assert summary["errored"] == 0

    def test_selection_is_forwarded_to_list_cases(self):
        """Test the harness reuses the catalog's own selectors, not a new one."""
        from geocase.differential import compare_cases

        results = compare_cases(
            left=lambda p: 1,
            right=lambda p: 1,
            include_ids=["empty_geometry_gpkg"],
        )

        assert [r.case_id for r in results] == ["empty_geometry_gpkg"]

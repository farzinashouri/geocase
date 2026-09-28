"""Tests for ``geocase.differential``'s round instrument -- Plan 51.

Every differential round to date (pyogrio, GDAL) hand-rolled the same three
steps around the library call: run ``compare_cases``, ``summarize`` the
result, then hand-format the non-``agree`` outcomes into prose. These tests
pin the one call that replaces the third step -- ``run_round`` to gather the
results, ``render_report`` to write them up -- so PROJ (#47) and GEOS (#48)
do not redo it a third and fourth time.
"""

from __future__ import annotations

from pathlib import Path

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


def _run_round(monkeypatch, tmp_path: Path, cases: list[CaseMetadata], **kwargs):
    """Call ``run_round`` against synthetic cases, bypassing the real catalog.

    ``compare_cases`` resolves each case's directory through
    ``case_roots_by_id()``, which only knows about the bundled corpus. These
    tests exercise the round instrument's own logic, not catalog resolution
    -- that is already covered for real cases in
    ``TestRunOverTheCorpus.test_selection_is_forwarded_to_list_cases`` (and
    below, in ``test_selection_kwargs_reach_compare_cases``) -- so the roots
    lookup is patched to point every synthetic case at ``tmp_path``.
    """
    from geocase.differential import run_round

    monkeypatch.setattr(
        "geocase.catalog.roots.case_roots_by_id",
        lambda: {case.id: tmp_path for case in cases},
    )
    return run_round(cases=cases, **kwargs)


def _write(path: Path, text: str = "x") -> None:
    path.write_text(text)


class TestRunRound:
    def test_gathers_results_and_summary(self, tmp_path, monkeypatch):
        _write(tmp_path / "a.geojson", "1")
        cases = [_case("agreeing_a", "a.geojson"), _case("agreeing_b", "a.geojson")]

        report = _run_round(
            monkeypatch,
            tmp_path,
            cases,
            title="stdlib read vs itself",
            left=lambda p: p.read_text(),
            right=lambda p: p.read_text(),
        )

        assert report.title == "stdlib read vs itself"
        assert [r.case_id for r in report.results] == ["agreeing_a", "agreeing_b"]
        assert report.summary == {"agree": 2, "diverged": 0, "known": 0, "errored": 0}

    def test_forwards_consumer_for_known_divergences(self, tmp_path, monkeypatch):
        _write(tmp_path / "p.geojson", "1")
        case = _case(
            "catalogued",
            "p.geojson",
            known_divergences=[
                KnownDivergence(consumer="proj", description="axis order")
            ],
        )

        report = _run_round(
            monkeypatch,
            tmp_path,
            [case],
            title="proj round",
            left=lambda p: 2,
            right=lambda p: 3,
            consumer="proj",
        )

        assert report.consumer == "proj"
        assert report.results[0].outcome == "known"
        assert report.summary["known"] == 1

    def test_selection_kwargs_reach_compare_cases(self):
        from geocase.differential import run_round

        report = run_round(
            title="whole vector corpus",
            left=lambda p: 1,
            right=lambda p: 1,
            include_ids=["empty_geometry_gpkg"],
        )

        assert [r.case_id for r in report.results] == ["empty_geometry_gpkg"]
        assert report.summary["agree"] == 1


class TestRenderReport:
    def test_lists_diverged_cases_with_detail(self, tmp_path, monkeypatch):
        from geocase.differential import render_report

        _write(tmp_path / "p.geojson", "1")
        report = _run_round(
            monkeypatch,
            tmp_path,
            [_case("mismatch", "p.geojson")],
            title="a round",
            left=lambda p: "left value",
            right=lambda p: "right value",
        )

        text = render_report(report)

        assert "# a round" in text
        assert "mismatch" in text
        assert "left value" in text
        assert "right value" in text

    def test_omits_agreeing_cases_from_the_body(self, tmp_path, monkeypatch):
        from geocase.differential import render_report

        _write(tmp_path / "p.geojson", "1")
        report = _run_round(
            monkeypatch,
            tmp_path,
            [_case("boring", "p.geojson")],
            title="clean round",
            left=lambda p: 1,
            right=lambda p: 1,
        )

        text = render_report(report)

        assert "boring" not in text

    def test_a_clean_round_says_so_rather_than_rendering_empty(
        self, tmp_path, monkeypatch
    ):
        from geocase.differential import render_report

        _write(tmp_path / "p.geojson", "1")
        report = _run_round(
            monkeypatch,
            tmp_path,
            [_case("boring", "p.geojson")],
            title="clean round",
            left=lambda p: 1,
            right=lambda p: 1,
        )

        text = render_report(report)

        assert "no divergences" in text.lower() or "all agreed" in text.lower()

    def test_known_divergence_shows_the_upstream_url(self, tmp_path, monkeypatch):
        from geocase.differential import render_report

        _write(tmp_path / "p.geojson", "1")
        case = _case(
            "catalogued",
            "p.geojson",
            known_divergences=[
                KnownDivergence(
                    consumer="proj",
                    description="axis order",
                    upstream_url="https://example.org/issue/1",
                )
            ],
        )

        report = _run_round(
            monkeypatch,
            tmp_path,
            [case],
            title="proj round",
            left=lambda p: 2,
            right=lambda p: 3,
            consumer="proj",
        )
        text = render_report(report)

        assert "https://example.org/issue/1" in text

    def test_environment_table_only_when_given(self, tmp_path, monkeypatch):
        from geocase.differential import render_report

        _write(tmp_path / "p.geojson", "1")
        case = _case("c", "p.geojson")
        no_env = _run_round(
            monkeypatch,
            tmp_path,
            [case],
            title="no env",
            left=lambda p: 1,
            right=lambda p: 1,
        )
        with_env = _run_round(
            monkeypatch,
            tmp_path,
            [case],
            title="with env",
            left=lambda p: 1,
            right=lambda p: 1,
            environment={"proj": "9.4.1"},
        )

        assert "9.4.1" not in render_report(no_env)
        assert "9.4.1" in render_report(with_env)
        assert "proj" in render_report(with_env)

    def test_errored_cases_are_listed_separately_from_diverged(
        self, tmp_path, monkeypatch
    ):
        from geocase.differential import render_report

        _write(tmp_path / "p.geojson", "1")

        def boom(path):
            raise ValueError("boom detail")

        report = _run_round(
            monkeypatch,
            tmp_path,
            [_case("crashes", "p.geojson")],
            title="a round",
            left=lambda p: 1,
            right=boom,
        )
        text = render_report(report)

        assert "crashes" in text
        assert "boom detail" in text

    def test_notes_are_included(self, tmp_path, monkeypatch):
        from geocase.differential import render_report

        _write(tmp_path / "p.geojson", "1")
        report = _run_round(
            monkeypatch,
            tmp_path,
            [_case("c", "p.geojson")],
            title="a round",
            left=lambda p: 1,
            right=lambda p: 1,
            notes="Filtered to cases PROJ 9.4 can open.",
        )

        assert "Filtered to cases PROJ 9.4 can open." in render_report(report)

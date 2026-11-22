from __future__ import annotations

from pathlib import Path

import pytest

from geocase import ci

pytest_plugins = ["pytester"]

FIX = Path(__file__).parent.parent / "fixtures" / "ci"


def test_case_id_format_matches_plugin(pytester: pytest.Pytester) -> None:
    """The test id carries the bare case id; ci.py parses what the plugin emits."""
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.geocase_case("all_valid_rectangular")
        def test_x(geocase):
            pass
        """
    )
    result = pytester.runpytest("--collect-only", "-q")
    result.stdout.fnmatch_lines(["*test_x[[]all_valid_rectangular[]]*"])
    assert (
        ci.case_id_from_test_name("test_x[all_valid_rectangular]")
        == "all_valid_rectangular"
    )


def test_non_geocase_names_yield_none() -> None:
    assert ci.case_id_from_test_name("test_math") is None
    assert ci.case_id_from_test_name("test_param[1]") is None


def test_all_pass() -> None:
    md = ci.build_report(FIX / "all_pass.xml")
    assert "2 of 2 GeoCase cases pass" in md
    assert "| Case |" not in md


def test_failures_listed_with_metadata() -> None:
    md = ci.build_report(FIX / "some_fail.xml")
    assert "1 of 3 GeoCase cases pass" in md
    assert "ambiguous_engine_dependent_polygon" in md
    assert "Ambiguous Engine-dependent Polygon" in md
    assert "geometry/topology_error" in md
    assert "test_zonal" in md
    assert "AssertionError: mean is nan" in md
    assert "second line" not in md
    assert "test_math" not in md


def test_no_geocase_tests() -> None:
    md = ci.build_report(FIX / "no_geocase.xml")
    assert "No GeoCase cases" in md


def test_cli_writes_file_and_exits_zero(tmp_path: Path) -> None:
    out = tmp_path / "s.md"
    assert ci.main(["report", str(FIX / "some_fail.xml"), "--out", str(out)]) == 0
    assert "GeoCase cases pass" in out.read_text()


def test_cli_prints_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    assert ci.main(["report", str(FIX / "all_pass.xml")]) == 0
    assert "2 of 2" in capsys.readouterr().out

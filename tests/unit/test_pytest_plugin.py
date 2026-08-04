"""Focused error-path tests for the GeoCase pytest plugin."""

from __future__ import annotations

from pathlib import Path

import pytest

from geocase.cases.base import BaseCase
from geocase.catalog.registry import get_registry
from geocase.pytest_plugin import marks_for_case

pytest_plugins = ("pytester",)

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"


def _make_plugin_conftest(pytester: pytest.Pytester) -> None:
    pytester.makeconftest(
        f"""
from __future__ import annotations

import sys

if {str(_SRC)!r} not in sys.path:
    sys.path.insert(0, {str(_SRC)!r})
"""
    )


def test_geocase_fixture_without_markers_shows_helpful_usage_error(
    pytester: pytest.Pytester,
) -> None:
    """Test geocase fixture without markers shows helpful usage error."""
    _make_plugin_conftest(pytester)
    pytester.makepyfile(
        """

def test_needs_marker(geocase):
    assert geocase is not None
"""
    )

    result = pytester.runpytest_subprocess("-q")

    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        [
            "*UsageError: Fixture 'geocase' requires at least one GeoCase marker*",
        ]
    )


def test_geocase_case_marker_without_args_raises_usage_error(
    pytester: pytest.Pytester,
) -> None:
    """Test geocase case marker without args raises usage error."""
    _make_plugin_conftest(pytester)
    pytester.makepyfile(
        """
import pytest


@pytest.mark.geocase_case()
def test_missing_case_args(geocase):
    assert geocase is not None
"""
    )

    result = pytester.runpytest_subprocess("-q")

    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        [
            "*@pytest.mark.geocase_case requires at least one case id*",
        ]
    )


def test_unknown_suite_key_raises_usage_error(pytester: pytest.Pytester) -> None:
    """Test unknown suite key raises usage error."""
    _make_plugin_conftest(pytester)
    pytester.makepyfile(
        """
import pytest


@pytest.mark.geocase_suite("no_such_suite")
def test_unknown_suite(geocase):
    assert geocase is not None
"""
    )

    result = pytester.runpytest_subprocess("-q")

    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        [
            "*UsageError: Unknown geocase suite 'no_such_suite'. Available:*",
        ]
    )


def test_geocase_case_fixture_requires_exactly_one_case(
    pytester: pytest.Pytester,
) -> None:
    """Test geocase case fixture requires exactly one case."""
    _make_plugin_conftest(pytester)
    pytester.makepyfile(
        """
import pytest


@pytest.mark.geocase_case("simple_valid_polygon", "polygon_with_hole")
def test_ambiguous_single_case_fixture(geocase_case):
    assert geocase_case is not None
"""
    )

    result = pytester.runpytest_subprocess("-q")

    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        [
            "*UsageError: Fixture 'geocase_case' requires exactly one resolved case.*",
        ]
    )


def test_geocase_select_with_no_matches_raises_helpful_usage_error(
    pytester: pytest.Pytester,
) -> None:
    """Test geocase select with no matches raises helpful usage error."""
    _make_plugin_conftest(pytester)
    pytester.makepyfile(
        """
import pytest


@pytest.mark.geocase_select(category="satellite")
def test_selection_with_no_matches(geocase):
    assert geocase is not None
"""
    )

    result = pytester.runpytest_subprocess("-q")

    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        [
            "*UsageError: Fixture 'geocase' resolved zero cases. Check your "
            "case ids, suite keys, or selector filters.*",
        ]
    )


class TestRemoteMarker:
    """Step 13.5: `remote` is attached from metadata, not by hand."""

    @staticmethod
    def _case(storage_class: str) -> BaseCase:
        registry = get_registry()
        meta = registry.list_cases()[0].model_copy(
            update={"storage_class": storage_class}
        )
        return BaseCase(meta, _ROOT)

    def test_bundled_case_gets_no_marks(self) -> None:
        """Leaves bundled cases unmarked, so `-m "not remote"` keeps them."""
        assert marks_for_case(self._case("bundled")) == []

    def test_remote_case_gets_the_remote_marker(self) -> None:
        """Attaches `pytest.mark.remote` to cases whose data is not bundled."""
        marks = marks_for_case(self._case("remote"))
        assert [mark.name for mark in marks] == ["remote"]

    def test_marker_is_registered_by_the_plugin(
        self, pytester: pytest.Pytester
    ) -> None:
        """Registers `remote` in a fresh install, so `-m` needs no user config."""
        _make_plugin_conftest(pytester)
        result = pytester.runpytest_subprocess("--markers")
        result.stdout.fnmatch_lines(["*@pytest.mark.remote:*not bundled*"])

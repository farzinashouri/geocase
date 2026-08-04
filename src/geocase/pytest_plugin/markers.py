"""Pytest marker registration for GeoCase plugin."""

from __future__ import annotations

import pytest


def register_markers(config: pytest.Config) -> None:
    """Register custom GeoCase markers in pytest help output."""
    config.addinivalue_line(
        "markers",
        "geocase_case(*case_ids): attach one or more explicit GeoCase case ids",
    )
    config.addinivalue_line(
        "markers",
        "geocase_suite(*suite_keys): attach one or more GeoCase suite keys",
    )
    config.addinivalue_line(
        "markers",
        "geocase_select(**filters): select cases using SuiteSelection-like filters",
    )
    # Attached automatically by ``pytest_generate_tests`` to cases whose
    # ``storage_class`` is ``remote``. Registered here rather than left to the
    # user's own config so ``pytest -m "not remote"`` works in a fresh install.
    config.addinivalue_line(
        "markers",
        "remote: a GeoCase case whose data is not bundled with the package "
        '(deselect with -m "not remote")',
    )

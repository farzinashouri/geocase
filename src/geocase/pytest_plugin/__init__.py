"""GeoCase pytest plugin entrypoint."""

from __future__ import annotations

import pytest

from geocase.pytest_plugin.fixtures import (
	geocase,
	geocase_case,
	geocase_cases,
	geocase_registry,
	resolve_cases_from_node,
)
from geocase.pytest_plugin.markers import register_markers


def pytest_configure(config: pytest.Config) -> None:
	"""Register custom markers for plugin users."""
	register_markers(config)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
	"""Auto-parametrize the ``geocase`` fixture from markers.

	If a test function requests fixture ``geocase`` and has one of the
	GeoCase markers, it is parametrized once per resolved case.
	"""
	if "geocase" not in metafunc.fixturenames:
		return

	cases = resolve_cases_from_node(metafunc.definition)
	if not cases:
		return

	metafunc.parametrize("geocase", cases, ids=[case.id for case in cases])


__all__ = [
	"geocase",
	"geocase_registry",
	"geocase_cases",
	"geocase_case",
]

"""Pytest fixtures and helpers for GeoCase integration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from geocase.catalog.loader import load_case_index, load_case_metadata
from geocase.catalog.models import CaseMetadata
from geocase.catalog.registry import CaseRegistry, get_registry
from geocase.catalog.selectors import select_cases
from geocase.catalog.suites import load_all_suites
from geocase.cases.base import BaseCase
from geocase.cases.factory import create_case

if TYPE_CHECKING:
	from _pytest.nodes import Node


def _package_root() -> Path:
	return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def _case_roots_by_id() -> dict[str, Path]:
	root = _package_root()
	case_index_path = root / "metadata" / "case-index.yaml"
	rel_case_yaml_paths = load_case_index(case_index_path)

	out: dict[str, Path] = {}
	for rel in rel_case_yaml_paths:
		case_yaml = root / rel
		meta = load_case_metadata(case_yaml)
		out[meta.id] = case_yaml.parent
	return out


def _materialize_case(meta: CaseMetadata) -> BaseCase:
	roots = _case_roots_by_id()
	try:
		root_dir = roots[meta.id]
	except KeyError as exc:
		raise KeyError(f"No case root found for case id '{meta.id}'") from exc
	return create_case(meta, root_dir)


def _dedupe_case_metadata(cases: list[CaseMetadata]) -> list[CaseMetadata]:
	seen: set[str] = set()
	ordered: list[CaseMetadata] = []
	for case in cases:
		if case.id not in seen:
			seen.add(case.id)
			ordered.append(case)
	return ordered


def resolve_case_metadata_from_node(
	node: Node,
	registry: CaseRegistry | None = None,
) -> list[CaseMetadata]:
	"""Resolve all GeoCase markers on a node into case metadata."""
	if registry is None:
		registry = get_registry()

	selected: list[CaseMetadata] = []

	for mark in node.iter_markers("geocase_case"):
		if not mark.args:
			raise pytest.UsageError(
				"@pytest.mark.geocase_case requires at least one case id"
			)
		for case_id in mark.args:
			selected.append(registry.get(str(case_id)))

	suite_marks = list(node.iter_markers("geocase_suite"))
	if suite_marks:
		suite_map = {suite.suite_key: suite for suite in load_all_suites(registry=registry)}
		for mark in suite_marks:
			if not mark.args:
				raise pytest.UsageError(
					"@pytest.mark.geocase_suite requires a suite key"
				)
			for suite_key in mark.args:
				key = str(suite_key)
				if key not in suite_map:
					available = sorted(suite_map)
					raise pytest.UsageError(
						f"Unknown geocase suite '{key}'. Available: {available}"
					)
				selected.extend(suite_map[key].cases)

	for mark in node.iter_markers("geocase_select"):
		kwargs = dict(mark.kwargs)
		selected.extend(select_cases(registry.list_cases(), **kwargs))

	return _dedupe_case_metadata(selected)


def resolve_cases_from_node(node: Node) -> list[BaseCase]:
	"""Resolve GeoCase markers on a node into materialized case objects."""
	metadata = resolve_case_metadata_from_node(node)
	return [_materialize_case(meta) for meta in metadata]


@pytest.fixture(scope="session")
def geocase_registry() -> CaseRegistry:
	"""Session-scoped case registry singleton."""
	return get_registry()


@pytest.fixture
def geocase_cases(request: pytest.FixtureRequest) -> list[BaseCase]:
	"""Resolve all GeoCase markers on the test node into case objects."""
	return resolve_cases_from_node(request.node)


@pytest.fixture
def geocase_case(geocase_cases: list[BaseCase]) -> BaseCase:
	"""Single-case convenience fixture.

	Requires exactly one resolved case from markers.
	"""
	if len(geocase_cases) != 1:
		raise pytest.UsageError(
			"Fixture 'geocase_case' requires exactly one resolved case. "
			"Use @pytest.mark.geocase_case('case_id')."
		)
	return geocase_cases[0]


@pytest.fixture
def geocase(request: pytest.FixtureRequest) -> BaseCase:
	"""Parametrized convenience fixture populated by ``pytest_generate_tests``.

	When used without any GeoCase marker, or when markers resolve to zero
	cases, raise a helpful UsageError instead of surfacing a generic
	``fixture 'geocase' not found`` failure.
	"""
	if hasattr(request, "param"):
		return request.param

	has_geocase_markers = any(
		any(request.node.iter_markers(marker_name))
		for marker_name in ("geocase_case", "geocase_suite", "geocase_select")
	)
	if has_geocase_markers:
		raise pytest.UsageError(
			"Fixture 'geocase' resolved zero cases. Check your case ids, "
			"suite keys, or selector filters."
		)

	raise pytest.UsageError(
		"Fixture 'geocase' requires at least one GeoCase marker such as "
		"@pytest.mark.geocase_case(...), @pytest.mark.geocase_suite(...), "
		"or @pytest.mark.geocase_select(...)."
	)

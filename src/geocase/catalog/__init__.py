"""Catalog module — registry, selectors, and suite resolution."""

from geocase.catalog.errors import RemoteCaseUnavailableError
from geocase.catalog.loader import (
    load_case_index,
    load_case_metadata,
    load_suite_index,
    load_suite_metadata,
)
from geocase.catalog.models import (
    CaseMetadata,
    SpatialExtent,
    SuiteMetadata,
    SuiteSelection,
)
from geocase.catalog.registry import CaseRegistry, get_registry, reset_registry
from geocase.catalog.selectors import matches_selection, select_cases
from geocase.catalog.suites import (
    ResolvedSuite,
    load_all_suites,
    load_and_resolve_suite,
    resolve_suite,
)

__all__ = [
    # Errors
    "RemoteCaseUnavailableError",
    # Models
    "CaseMetadata",
    "SpatialExtent",
    "SuiteMetadata",
    "SuiteSelection",
    # Loader
    "load_case_metadata",
    "load_suite_metadata",
    "load_case_index",
    "load_suite_index",
    # Registry
    "CaseRegistry",
    "get_registry",
    "reset_registry",
    # Selectors
    "matches_selection",
    "select_cases",
    # Suites
    "ResolvedSuite",
    "resolve_suite",
    "load_and_resolve_suite",
    "load_all_suites",
]

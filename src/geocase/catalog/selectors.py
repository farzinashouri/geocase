"""Case selectors — filter cases by metadata criteria.

Provides a functional API for narrowing the full case catalog down to
the subset matching a ``SuiteSelection`` (or ad-hoc keyword filters).
"""

from __future__ import annotations

from geocase.catalog.models import (
    CaseMetadata,
    Category,
    FormatType,
    LoaderHint,
    SizeClass,
    StorageClass,
    SuiteSelection,
    TestTier,
)
from geocase.catalog.risk_types import canonical_risk_type


def matches_selection(case: CaseMetadata, sel: SuiteSelection) -> bool:
    """Return True if *case* satisfies every constraint in *sel*.

    Filter logic:
      * ``include_case_ids`` — if non-empty, case.id must be listed.
      * ``exclude_case_ids`` — case.id must *not* be listed.
            * ``category``, ``geometry_type``, ``test_tier``, ``storage_class``,
                ``format``, ``loader_hint``, ``size_class`` — exact match when
                the field is set.
      * ``tags_any`` — case must have **at least one** of the listed tags.
      * ``tags_all`` — case must have **all** of the listed tags.
      * ``risk_types_any`` — case must have at least one matching risk type.
      * ``risk_types_all`` — case must match **every** listed risk type.

    Risk-type terms are matched by :func:`_risk_matches`, so a deprecated
    spelling and a bare family prefix both select.
    """
    # Explicit include list takes priority
    if sel.include_case_ids and case.id not in sel.include_case_ids:
        return False

    # Explicit exclude list
    if case.id in sel.exclude_case_ids:
        return False

    # Exact-match scalar fields
    if sel.category is not None and case.category != sel.category:
        return False
    if sel.geometry_type is not None and case.geometry_type != sel.geometry_type:
        return False
    if sel.test_tier is not None and case.test_tier != sel.test_tier:
        return False
    if sel.storage_class is not None and case.storage_class != sel.storage_class:
        return False
    if sel.format is not None and case.format != sel.format:
        return False
    if sel.loader_hint is not None and case.loader_hint != sel.loader_hint:
        return False
    if sel.size_class is not None and case.size_class != sel.size_class:
        return False

    # Tag filters
    if sel.tags_any and not set(sel.tags_any) & set(case.tags):
        return False
    if sel.tags_all and not set(sel.tags_all) <= set(case.tags):
        return False

    # Risk type filters (plan 40 phase 3). Not plain set intersection: a query
    # term is resolved through the alias table, and a bare family prefix
    # matches every member of that family.
    if sel.risk_types_any and not any(
        _risk_matches(term, case.risk_types) for term in sel.risk_types_any
    ):
        return False
    if sel.risk_types_all and not all(
        _risk_matches(term, case.risk_types) for term in sel.risk_types_all
    ):
        return False

    return True


def _risk_matches(query: str, declared: list[str]) -> bool:
    """Return True if *query* selects a case declaring *declared*.

    Three ways to match, in the order a user is likely to try them:

    * the canonical term exactly -- ``crs/axis_order``;
    * a **deprecated spelling**, resolved through
      :data:`~geocase.catalog.risk_types.RISK_TYPE_ALIASES` -- ``coordinate_order``.
      ``risk_types`` is a pinned v1.0 selector surface, so a query written
      before the vocabulary was consolidated must keep selecting the same
      cases;
    * a bare **family prefix** -- ``crs`` selects every ``crs/*`` term. This is
      what makes a 102-term vocabulary browsable: the singletons stay in the
      index and become reachable through their family rather than only by
      exact spelling.
    """
    resolved = canonical_risk_type(query)
    if resolved in declared:
        return True
    return any(term.split("/")[0] == resolved for term in declared if "/" in term)


def select_cases(
    cases: list[CaseMetadata],
    selection: SuiteSelection | None = None,
    *,
    category: Category | None = None,
    geometry_type: str | None = None,
    test_tier: TestTier | None = None,
    storage_class: StorageClass | None = None,
    format: FormatType | None = None,
    loader_hint: LoaderHint | None = None,
    size_class: SizeClass | None = None,
    tags_any: list[str] | None = None,
    tags_all: list[str] | None = None,
    risk_types_any: list[str] | None = None,
    risk_types_all: list[str] | None = None,
    include_ids: list[str] | None = None,
    exclude_ids: list[str] | None = None,
) -> list[CaseMetadata]:
    """Return the subset of *cases* matching the given criteria.

    You can pass a pre-built ``SuiteSelection`` *or* use the keyword
    arguments (they are merged into a new ``SuiteSelection``).

    Args:
        cases: Full list of available cases.
        selection: Optional pre-built selection.
        category .. exclude_ids: Ad-hoc filter overrides.

    Returns:
        Filtered list of :class:`CaseMetadata` in the same order as
        *cases*.
    """
    if selection is None:
        selection = SuiteSelection(
            include_case_ids=include_ids or [],
            exclude_case_ids=exclude_ids or [],
            category=category,
            geometry_type=geometry_type,
            test_tier=test_tier,
            storage_class=storage_class,
            format=format,
            loader_hint=loader_hint,
            size_class=size_class,
            tags_any=tags_any or [],
            tags_all=tags_all or [],
            risk_types_any=risk_types_any or [],
            risk_types_all=risk_types_all or [],
        )

    return [c for c in cases if matches_selection(c, selection)]

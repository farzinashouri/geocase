"""The public GeoCase API.

Thin, stable functions over the registry, the selectors, and the case
factory. Everything here is re-exported from the top-level ``geocase``
package and covered by the v1.0 compatibility promise.

Note the deliberate asymmetry: :func:`list_cases` and :func:`get_case` return
:class:`~geocase.catalog.models.CaseMetadata` (cheap, no geospatial import),
while :func:`load_case` and the ``geocase`` pytest fixture yield a
:class:`~geocase.cases.base.BaseCase`, which can open the data.
"""

from __future__ import annotations

from typing import get_args

from geocase.cases.base import BaseCase
from geocase.catalog.manifests import build_manifest_uri
from geocase.catalog.models import (
    CaseMetadata,
    Category,
    FormatType,
    SizeClass,
    StorageClass,
    SuiteSelection,
    TestTier,
)
from geocase.catalog.registry import get_registry
from geocase.catalog.roots import materialize_case
from geocase.catalog.selectors import select_cases
from geocase.catalog.suites import ResolvedSuite, load_all_suites

__all__ = [
    "list_cases",
    "get_case",
    "load_case",
    "show_case",
    "list_suites",
    "get_suite",
]

#: The four :data:`~geocase.catalog.models.Category` values, as a set, so
#: :func:`_reject_category_as_format` can intercept them before pydantic does.
_CATEGORY_VALUES = frozenset(get_args(Category))


def _reject_category_as_format(format: str | None) -> None:
    """Redirect ``format="vector"`` to ``category="vector"``.

    ``format`` and ``category`` are both plausible names for "what kind of case
    is this", so passing a category to ``format`` is the single most common
    first-contact mistake (it is the "worst first impression" recorded in
    ``docs/geocase_validate/geocase-improvement-report.md``). Left to pydantic
    it raises a ``ValidationError`` reciting every ``FormatType`` literal and
    never mentioning ``category`` — the answer is not in the error.

    ``format`` deliberately keeps its name: renaming it would break the v1.0
    keyword surface to fix a message. See Plan 28 phase 2.3.

    Raises:
        ValueError: If *format* is one of the four ``Category`` literals.
    """
    if format in _CATEGORY_VALUES:
        raise ValueError(
            f"{format!r} is a case category, not a file format. "
            f"Use category={format!r} instead of format={format!r}. "
            f"The 'format' filter takes a file format such as 'GeoJSON', "
            f"'GPKG' or 'GeoTIFF'."
        )


def list_cases(
    selection: SuiteSelection | None = None,
    *,
    category: Category | None = None,
    geometry_type: str | None = None,
    test_tier: TestTier | None = None,
    storage_class: StorageClass | None = None,
    format: FormatType | None = None,
    size_class: SizeClass | None = None,
    tags_any: list[str] | None = None,
    tags_all: list[str] | None = None,
    risk_types_any: list[str] | None = None,
    include_ids: list[str] | None = None,
    exclude_ids: list[str] | None = None,
) -> list[CaseMetadata]:
    """Return the bundled cases matching the given filters, sorted by id.

    Called with no arguments, returns the whole bundled catalog. The keyword
    filters are the same ones a suite's ``selection`` block uses.

    Returns:
        Matching :class:`~geocase.catalog.models.CaseMetadata`, *not*
        loadable case objects — see :func:`load_case`.
    """
    return select_cases(
        get_registry().list_cases(),
        selection,
        category=category,
        geometry_type=geometry_type,
        test_tier=test_tier,
        storage_class=storage_class,
        format=format,
        size_class=size_class,
        tags_any=tags_any,
        tags_all=tags_all,
        risk_types_any=risk_types_any,
        include_ids=include_ids,
        exclude_ids=exclude_ids,
    )


def get_case(case_id: str) -> CaseMetadata:
    """Return the metadata for a single case id.

    Raises:
        KeyError: If no such case is registered.
    """
    return get_registry().get(case_id)


def load_case(case_id: str) -> BaseCase:
    """Return a loadable case object for *case_id*.

    The returned object is a :class:`~geocase.cases.vector.VectorCase`,
    :class:`~geocase.cases.raster.RasterCase`, or
    :class:`~geocase.cases.netcdf.NetCDFCase` — call ``.load()`` or
    ``.open()`` on it to read the data.

    Raises:
        KeyError: If no such case is registered.
    """
    return materialize_case(get_case(case_id))


def show_case(case_id: str) -> str:
    """Return a human-readable multi-line summary of a case.

    Includes where the data lives, so a case that is catalogued but not present
    on disk — a manifest-backed one, or a bundled one whose file is missing —
    says so here instead of failing later at load time. This is the one public
    function that *describes* a remote case rather than refusing it.

    Raises:
        KeyError: If no such case is registered.
    """
    registry = get_registry()
    if registry.is_remote(case_id):
        return _show_remote_case(case_id)

    meta = get_case(case_id)
    lines = [
        f"{meta.id} — {meta.title}",
        f"  category:      {meta.category}",
        f"  format:        {meta.format}",
        f"  loader:        {meta.loader_hint}",
        f"  test_tier:     {meta.test_tier}",
        f"  size_class:    {meta.size_class}",
        f"  status:        {meta.status}",
    ]
    if meta.geometry_type:
        lines.append(f"  geometry_type: {meta.geometry_type}")
    if meta.crs:
        lines.append(f"  crs:           {meta.crs}")
    if meta.tags:
        lines.append(f"  tags:          {', '.join(sorted(meta.tags))}")
    lines.append(f"  storage:       {_describe_storage(meta)}")
    if meta.description:
        lines.append(f"  description:   {meta.description}")
    return "\n".join(lines)


def _show_remote_case(case_id: str) -> str:
    """Summarize a manifest-backed case, which has no CaseMetadata to show."""
    registry = get_registry()
    manifest = registry.get_manifest(case_id)
    entry = registry.get_manifest_entry(case_id)

    lines = [
        f"{case_id} — remote case from manifest '{manifest.manifest_key}'",
        f"  storage:       {manifest.storage.storage_type}, not fetched",
        f"  uri:           {build_manifest_uri(manifest, entry)}",
        f"  version:       {entry.version}",
        f"  sha256:        {entry.sha256}",
    ]
    if entry.byte_size is not None:
        lines.append(f"  byte_size:     {entry.byte_size}")
    if entry.archive_format:
        lines.append(f"  archive:       {entry.archive_format}")
    if entry.bundled_analog:
        lines.append(f"  analog:        {entry.bundled_analog} (bundled)")
    lines.append(
        "  note:          this release does not fetch remote data; "
        "load_case() will refuse it"
    )
    return "\n".join(lines)


def _describe_storage(meta: CaseMetadata) -> str:
    """Describe where a case's data lives and whether it is there now."""
    if meta.storage_class != "bundled":
        uri = meta.remote.uri if meta.remote else None
        location = f" at {uri}" if uri else ""
        return f"{meta.storage_class}, not fetched{location}"

    case = materialize_case(meta)
    if not case.primary_exists():
        return f"bundled, but {case.primary_path} is missing"
    return f"bundled at {case.primary_path}"


def list_suites() -> list[ResolvedSuite]:
    """Return every bundled suite, resolved against the registry."""
    return load_all_suites()


def get_suite(suite_key: str) -> ResolvedSuite:
    """Return a single resolved suite by key.

    Raises:
        KeyError: If no suite with that key is bundled.
    """
    suites = {suite.suite_key: suite for suite in list_suites()}
    try:
        return suites[suite_key]
    except KeyError:
        raise KeyError(
            f"Suite '{suite_key}' not found. Available: {sorted(suites)}"
        ) from None

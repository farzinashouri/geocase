"""GeoCase — a curated catalog of geospatial test cases.

The supported import surface is everything in ``__all__`` below::

    import geocase

    for meta in geocase.list_cases(category="vector", test_tier="unit"):
        gdf = geocase.load_case(meta.id).load()

Note the asymmetry: :func:`list_cases` and :func:`get_case` return
:class:`CaseMetadata`, while :func:`load_case` returns a :class:`BaseCase` that
can open the data. The pytest fixtures below likewise yield ``BaseCase``.

The pytest plugin is part of the same promise even though it is not importable
from here. It provides the fixtures ``geocase``, ``geocase_case``,
``geocase_cases``, and ``geocase_registry``, and the markers
``@pytest.mark.geocase_case``, ``@pytest.mark.geocase_suite``, and
``@pytest.mark.geocase_select``.
"""

from importlib.metadata import PackageNotFoundError, version

from geocase.api.public import (
    get_case,
    get_suite,
    list_cases,
    list_suites,
    load_case,
    show_case,
)
from geocase.api.types import (
    AssertionHints,
    BaseCase,
    CaseMetadata,
    Category,
    FileMap,
    FormatType,
    LoaderHint,
    NetCDFCase,
    NodataConvention,
    RasterCase,
    ResolvedSuite,
    SizeClass,
    SourceInfo,
    Status,
    StorageClass,
    SuiteMetadata,
    SuiteSelection,
    TestTier,
    VectorCase,
)
from geocase.catalog.errors import RemoteCaseUnavailableError

try:
    # Read from the installed distribution metadata rather than a literal, so
    # `geocase.__version__` cannot drift from pyproject.toml.
    __version__ = version("geocase")
except PackageNotFoundError:  # pragma: no cover - source tree, not installed
    __version__ = "0.0.0+unknown"

__all__ = [
    "__version__",
    # Functions
    "list_cases",
    "get_case",
    "load_case",
    "show_case",
    "list_suites",
    "get_suite",
    # Errors
    "RemoteCaseUnavailableError",
    # Types
    "BaseCase",
    "VectorCase",
    "RasterCase",
    "NetCDFCase",
    "CaseMetadata",
    "SuiteMetadata",
    "SuiteSelection",
    "ResolvedSuite",
    "AssertionHints",
    "FileMap",
    "SourceInfo",
    "Category",
    "FormatType",
    "TestTier",
    "SizeClass",
    "StorageClass",
    "LoaderHint",
    "Status",
    "NodataConvention",
]

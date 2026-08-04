"""Public API package — see :mod:`geocase.api.public` and :mod:`geocase.api.types`.

Import from the top-level ``geocase`` package instead; this module exists so
the surface has one obvious home.
"""

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

__all__ = [
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

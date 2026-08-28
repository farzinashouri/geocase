"""Stable types re-exported for user code.

Importing these from ``geocase`` (or ``geocase.api.types``) is the supported
way to annotate code that consumes the catalog. Everything here is covered by
the v1.0 compatibility promise.

The manifest models (``ManifestMetadata``, ``ManifestCaseEntry``,
``ManifestStorage``) are **deliberately excluded**: the manifest schema is
revised in v1.1, and re-exporting it here would pin it a release early. They
remain importable from ``geocase.catalog``.
"""

from __future__ import annotations

from geocase.cases.base import BaseCase
from geocase.cases.netcdf import NetCDFCase
from geocase.cases.raster import RasterCase
from geocase.cases.vector import VectorCase
from geocase.catalog.models import (
    AssertionHints,
    CaseMetadata,
    Category,
    FileMap,
    FormatType,
    LoaderHint,
    NodataConvention,
    SizeClass,
    SourceInfo,
    SpatialExtent,
    Status,
    StorageClass,
    SuiteMetadata,
    SuiteSelection,
    TestTier,
)
from geocase.catalog.suites import ResolvedSuite

__all__ = [
    # Case objects
    "BaseCase",
    "VectorCase",
    "RasterCase",
    "NetCDFCase",
    # Metadata models
    "CaseMetadata",
    "SuiteMetadata",
    "SuiteSelection",
    "ResolvedSuite",
    "AssertionHints",
    "FileMap",
    "SourceInfo",
    "SpatialExtent",
    # Field vocabularies
    "Category",
    "FormatType",
    "TestTier",
    "SizeClass",
    "StorageClass",
    "LoaderHint",
    "Status",
    "NodataConvention",
]

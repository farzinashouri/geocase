"""Format & geometry-type compliance gate — universal validation.

Auto-discovers every vector case from case-index.yaml and validates:
1. The primary file truly matches the declared format (magic bytes / structure).
2. The loaded geometries match the declared geometry_type.

Any future case that lies about its format or geometry type fails CI
automatically — no one has to remember to write a specific test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from geocase.assertions.format_compliance import (
    assert_format_compliance,
    assert_geoparquet_metadata,
    registered_format_validators,
)
from geocase.catalog.loader import load_case_index, load_case_metadata
from geocase.catalog.models import CaseMetadata, FormatType

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_SRC = Path(__file__).resolve().parents[2] / "src" / "geocase"
_METADATA = _SRC / "metadata"
_CASE_INDEX = _METADATA / "case-index.yaml"


# ---------------------------------------------------------------------------
# Auto-discover every bundled vector case
# ---------------------------------------------------------------------------


def _discover_vector_cases() -> list[str]:
    """Return (case_id, relative_path) for every vector case in the index."""
    relative_paths = load_case_index(_CASE_INDEX)
    src_root = _METADATA.parent  # src/geocase/

    cases: list[str] = []
    for rel in relative_paths:
        case_path = src_root / rel
        meta = load_case_metadata(case_path)
        if meta.category == "vector":
            cases.append(rel)
    return cases


_VECTOR_CASE_PATHS: list[str] = _discover_vector_cases()


def _load_meta(rel_path: str) -> CaseMetadata:
    src_root = _METADATA.parent
    return load_case_metadata(src_root / rel_path)


def _case_id_from_path(rel_path: str) -> str:
    """Extract a short test id from a relative case.yaml path."""
    return _load_meta(rel_path).id


# ---------------------------------------------------------------------------
# Validator coverage: dispatch table must cover every vector FormatType
# ---------------------------------------------------------------------------

# Formats that are non-vector (raster / generic) — deliberately excluded
# from the vector compliance gate.  If a new FormatType is added to
# models.py and is NOT in this set, the test below will fail until
# either a validator is registered or the format is added here.
_NON_VECTOR_FORMATS: frozenset[str] = frozenset({"GeoTIFF", "NetCDF", "Other"})


class TestValidatorCoverage:
    """Ensure the validator dispatch table stays in sync with FormatType."""

    def test_every_vector_format_has_a_validator(self) -> None:
        """Every FormatType that is not explicitly excluded must have a
        registered validator.  Adding a new format to models.py without
        adding a validator will fail this test."""
        all_formats: frozenset[str] = frozenset(FormatType.__args__)  # type: ignore[attr-defined]
        vector_formats = all_formats - _NON_VECTOR_FORMATS
        registered = registered_format_validators()

        missing = vector_formats - registered
        assert not missing, (
            f"FormatType values with no registered validator: {sorted(missing)}. "
            f"Either add a validator in format_compliance.py or add the format "
            f"to _NON_VECTOR_FORMATS if it is not a vector format."
        )

    def test_no_stale_validators(self) -> None:
        """Every registered validator must correspond to a real FormatType."""
        all_formats: frozenset[str] = frozenset(FormatType.__args__)  # type: ignore[attr-defined]
        registered = registered_format_validators()

        stale = registered - all_formats
        assert not stale, (
            f"Validators registered for unknown FormatType values: {sorted(stale)}. "
            f"Remove them from format_compliance.py or add the format to models.py."
        )


# ---------------------------------------------------------------------------
# Format compliance: every vector file must truly be the declared format
# ---------------------------------------------------------------------------


class TestFormatCompliance:
    """Every vector case's primary file must truly be the declared format."""

    @pytest.mark.parametrize(
        "case_path",
        _VECTOR_CASE_PATHS,
        ids=[_case_id_from_path(p) for p in _VECTOR_CASE_PATHS],
    )
    def test_format_matches_declared(self, case_path: str) -> None:
        """Test format matches declared."""
        meta = _load_meta(case_path)
        case_dir = (_METADATA.parent / case_path).parent
        primary = case_dir / meta.files.primary

        assert primary.is_file(), (
            f"Case '{meta.id}': primary file not found at {primary}"
        )
        assert_format_compliance(primary, meta.format)

    @pytest.mark.parametrize(
        "case_path",
        [p for p in _VECTOR_CASE_PATHS if _load_meta(p).format == "Parquet"],
        ids=[
            _case_id_from_path(p)
            for p in _VECTOR_CASE_PATHS
            if _load_meta(p).format == "Parquet"
        ],
    )
    def test_geoparquet_metadata(self, case_path: str) -> None:
        """Parquet cases must contain valid GeoParquet metadata."""
        meta = _load_meta(case_path)
        case_dir = (_METADATA.parent / case_path).parent
        primary = case_dir / meta.files.primary
        assert_geoparquet_metadata(primary)


# ---------------------------------------------------------------------------
# Geometry-type truthfulness: loaded geometries must match declared type
# ---------------------------------------------------------------------------


class TestGeometryTypeTruthfulness:
    """Loaded geometries must match the declared geometry_type."""

    @pytest.mark.parametrize(
        "case_path",
        _VECTOR_CASE_PATHS,
        ids=[_case_id_from_path(p) for p in _VECTOR_CASE_PATHS],
    )
    def test_geometry_type_matches_declared(self, case_path: str) -> None:
        """Test geometry type matches declared."""
        meta = _load_meta(case_path)

        # Cases that declare themselves non-loadable cannot be geometry-checked.
        if meta.assertions.expect_loadable is False:
            pytest.skip(
                f"Case '{meta.id}' declares expect_loadable=false — "
                f"cannot verify geometry type on a non-loadable file"
            )

        # Determine expected types: prefer assertions.expected_geometry_types,
        # fall back to meta.geometry_type, skip if neither is declared.
        expected = meta.assertions.expected_geometry_types
        if not expected and meta.geometry_type:
            expected = [meta.geometry_type]

        if not expected:
            pytest.skip(
                f"Case '{meta.id}' declares no geometry type — nothing to check"
            )

        from geocase.assertions.geometry import assert_geometry_type
        from geocase.cases.vector import VectorCase

        case_dir = (_METADATA.parent / case_path).parent
        case = VectorCase(meta, case_dir)
        gdf = case.load()

        # Drop null/empty geometries before type-checking — cases like
        # empty_geometry_gpkg deliberately contain null geometry rows
        # whose geom_type is NaN, not a real type mismatch.
        gdf_valid = gdf.dropna(subset=[gdf.geometry.name])
        if gdf_valid.empty:
            pytest.skip(f"Case '{meta.id}' has no non-null geometries to type-check")

        assert_geometry_type(gdf_valid, expected)

"""Gates for the large curated vector cases (plan 28 phase 3).

Every vector case in the catalog held at most 4 features before this, and 74
held exactly one. That ceiling is not a size complaint -- it is a
*discriminating power* complaint. A probe for ``skip_features``,
``max_features``, Arrow batch chunking or a paged read still executes against a
one-feature fixture; it simply cannot fail, because with one feature every
boundary is the same boundary and every partial read is the full read.

So each case here is built around one failure mode that only becomes observable
*past a batch boundary*, which is the property the small cases cannot carry:

* ``invalid_geometry_at_scale_gpkg`` -- the only invalid geometry is the last
  of 10,000, so a validity sweep that stops at the first batch reports clean.
* ``null_after_batch_boundary_gpkg`` -- one NULL after 10,000 non-NULL
  integers, so type inference from a head sample disagrees with the full read.
* ``mixed_timezone_after_batch_gpkg`` -- the UTC offset changes only at the
  last row, so a schema inferred from the first batch carries the wrong tz.

The distributional lesson from the external validation runs is baked in: both
bugs pyogrio found came from ``vector/special/`` cases built around a *named*
failure mode, not from the 61 format-coverage baselines. These are scaled-up
members of the first population, not the second.

They are **generated**, not hand-committed -- the lesson of
``hole_center_nodata``, which drifted into the inverse of its own description
precisely because it sat outside the regeneration gate.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
VECTOR_ROOT = REPO_ROOT / "src" / "geocase" / "data" / "core" / "vector"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

pytest.importorskip("shapely")
pytest.importorskip("geopandas")

from geocase import load_case  # noqa: E402
from geocase.catalog.registry import get_registry  # noqa: E402

#: The three cases and the feature count each is built to carry.
#:
#: 10,000 is chosen against real batch sizes rather than as a round number:
#: pyogrio's Arrow path defaults to 65,536-row batches but GDAL's own
#: ``GetNextArrowArray`` and every paged reader in common use chunk far below
#: that, and the documented dtype-inference sampling window is smaller still.
#: A divergent row at index 10,000 is past every boundary a consumer is likely
#: to have, while keeping the payload inside the ``small`` size class.
LARGE_CASE_FEATURE_COUNTS = {
    "invalid_geometry_at_scale_gpkg": 10_000,
    "null_after_batch_boundary_gpkg": 10_001,
    "mixed_timezone_after_batch_gpkg": 10_001,
}

LARGE_CASE_IDS = sorted(LARGE_CASE_FEATURE_COUNTS)


def _metadata(case_id: str):  # type: ignore[no-untyped-def]
    return get_registry().get(case_id)


# --- the property that earns the size ---------------------------------------


@pytest.mark.parametrize("case_id", LARGE_CASE_IDS)
def test_large_case_has_enough_features_to_discriminate(case_id: str) -> None:
    """The point of the case: a boundary that is not the first boundary.

    Asserted against the loaded data rather than the declaration, so a fixture
    that shrank cannot pass by having its metadata shrink with it.
    """
    gdf = load_case(case_id).load()

    assert len(gdf) == LARGE_CASE_FEATURE_COUNTS[case_id]
    assert len(gdf) >= 10_000


@pytest.mark.parametrize("case_id", LARGE_CASE_IDS)
def test_large_case_declares_its_feature_count(case_id: str) -> None:
    """``expected_feature_count`` is what makes the size checkable by the gate.

    Without it ``check_vector_content`` has nothing to compare, and a fixture
    that silently regenerated with 100 features would stay green -- the
    declared-but-ungated shape phase 1 exists to close.
    """
    metadata = _metadata(case_id)

    assert (
        metadata.params.get("expected_feature_count")
        == LARGE_CASE_FEATURE_COUNTS[case_id]
    )


@pytest.mark.parametrize("case_id", LARGE_CASE_IDS)
def test_large_case_is_declared_small_not_tiny(case_id: str) -> None:
    """A megabyte-scale payload declaring ``tiny`` is exactly the lie phase 1 closed."""
    assert _metadata(case_id).size_class == "small"


# --- one failure mode each --------------------------------------------------


def test_invalid_geometry_sits_past_the_first_batch() -> None:
    """Feature 9,999 is invalid and every feature before it is valid.

    This is the whole discriminating claim. If the invalid feature were first,
    a consumer reading one batch would find it, and the case would prove
    nothing a 2-feature fixture does not already prove.
    """
    gdf = load_case("invalid_geometry_at_scale_gpkg").load()

    invalid = [i for i, valid in enumerate(gdf.geometry.is_valid) if not valid]

    assert invalid == [9_999]


def test_invalid_geometry_is_invisible_to_a_first_batch_read() -> None:
    """A head sample of any plausible batch size reports the data clean."""
    gdf = load_case("invalid_geometry_at_scale_gpkg").load()

    for batch in (1, 100, 1_000, 8_192):
        assert gdf.head(batch).geometry.is_valid.all(), (
            f"a {batch}-feature read must miss the defect; "
            "otherwise the case does not need 10,000 features"
        )


def test_null_column_is_non_null_for_the_first_ten_thousand_rows() -> None:
    """One NULL, and it is the last row -- so a head sample infers a non-null column."""
    gdf = load_case("null_after_batch_boundary_gpkg").load()

    nulls = [i for i, missing in enumerate(gdf["measure"].isna()) if missing]

    assert nulls == [10_000]
    assert gdf["measure"].head(10_000).notna().all()


def test_timezone_offset_changes_only_at_the_last_row() -> None:
    """The mixed offset is what a partial read cannot see.

    Compared on the UTC instant rather than on a dtype: what a reader returns a
    ``tz``-aware column *as* is the consumer's business (and is the thing the
    case exists to make disagree), while the instants themselves are the
    fixture's own content and must be stable.
    """
    import pandas as pd

    gdf = load_case("mixed_timezone_after_batch_gpkg").load()
    observed = pd.to_datetime(gdf["observed"], utc=True)

    head = observed.head(10_000)
    assert head.nunique() == 1

    # +01:00 for the first 10,000 rows, +05:30 for the last -- 4.5 hours apart
    # in wall-clock terms, so the two land on different UTC instants.
    assert observed.iloc[-1] != observed.iloc[0]
    assert (observed.iloc[0] - observed.iloc[-1]) == pd.Timedelta(hours=4, minutes=30)


def test_mixed_timezone_case_declares_its_gpkg_non_conformance() -> None:
    """The offsets violate GeoPackage requirement 15, and the case says so.

    Requirement 15 wants DATETIME in UTC with a literal ``Z``; numeric offsets
    are valid ISO 8601 but non-conformant, and GDAL warns on read. That
    non-conformance is the case's *subject* -- a conformant all-``Z`` file
    shows no dtype instability whatsoever -- so it has to be a declared
    property rather than something a user infers from a warning. A case whose
    interesting behaviour comes from an undeclared spec violation is the same
    defect class as a declared assertion nothing checks.
    """
    metadata = _metadata("mixed_timezone_after_batch_gpkg")

    assert metadata.params.get("gpkg_datetime_conformant") is False
    assert "format/spec_nonconformance" in metadata.risk_types


def test_mixed_timezone_offsets_are_stored_as_written() -> None:
    """The numeric offsets survive on disk -- which is what makes the case work.

    Read straight out of SQLite rather than through a reader: every reader
    normalises to UTC, so going through one would prove the conversion and not
    the storage. If a regeneration ever wrote these as ``Z``, the file would
    become conformant and the divergence would vanish -- with every
    consumer-level assertion still passing.
    """
    import sqlite3

    from geocase.catalog.roots import case_roots_by_id

    path = case_roots_by_id()["mixed_timezone_after_batch_gpkg"] / "mixed_timezone.gpkg"
    con = sqlite3.connect(path)
    try:
        rows = con.execute("SELECT observed FROM mixed_timezone ORDER BY id").fetchall()
    finally:
        con.close()

    assert rows[0][0].endswith("+01:00")
    assert rows[-1][0].endswith("+05:30")
    assert not any(value.endswith("Z") for (value,) in rows)


# --- generated, not hand-committed ------------------------------------------


def test_large_cases_are_under_the_regeneration_gate() -> None:
    """Built by the generator, so it cannot drift the way hole_center_nodata did."""
    from generate_vector_fixtures import (  # type: ignore[import-not-found]
        _large_specs,
    )

    assert sorted(spec.case_id for spec in _large_specs(VECTOR_ROOT)) == LARGE_CASE_IDS


def test_large_case_geometry_is_deterministic() -> None:
    """No PRNG, no clock: two builds of a spec agree coordinate for coordinate."""
    from generate_vector_fixtures import (  # type: ignore[import-not-found]
        _large_frame,
        _large_specs,
    )

    for spec in _large_specs(VECTOR_ROOT):
        first = _large_frame(spec)
        second = _large_frame(spec)
        assert first.geometry.to_wkb().tolist() == second.geometry.to_wkb().tolist()


# --- the corpus keeps its promises about them -------------------------------


@pytest.mark.parametrize("case_id", LARGE_CASE_IDS)
def test_large_case_passes_the_content_gate(case_id: str) -> None:
    """The declared assertions match the real bytes -- phase 1's gate, per case."""
    from geocase.catalog.content import check_vector_content
    from geocase.catalog.roots import case_roots_by_id

    metadata = _metadata(case_id)
    errors = check_vector_content(case_roots_by_id()[case_id], metadata)

    assert errors == []


@pytest.mark.parametrize("case_id", LARGE_CASE_IDS)
def test_large_case_needs_no_optional_ogr_driver(case_id: str) -> None:
    """GPKG on purpose: stock GDAL opens all three, so nobody is gated out.

    A large case behind ``libgdal-arrow-parquet`` would be unreachable for the
    consumers who most need it -- and phase 2.1 exists because 18% of the
    vector corpus already is.
    """
    assert _metadata(case_id).assertions.required_drivers == []

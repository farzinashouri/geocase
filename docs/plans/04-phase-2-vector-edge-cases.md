# Phase 2: Vector Edge Cases Plan

> Created: April 2026
> Status: **Complete** (April 2026)

This document breaks out Phase 2 from `docs/plans/03-consolidation-roadmap.md` into a dedicated implementation plan.

---

## Objective

Complete the remaining high-value vector edge-case work needed for GeoCase v1.0 without duplicating coverage that already exists in the live catalog.

The goal is not to add vector cases blindly. The goal is to:

1. verify what is already covered,
2. fill the real remaining gaps,
3. keep suites and tests aligned,
4. refresh the roadmap and matrix so they reflect reality.

---

## Current Status

The live vector catalog is already broad.

### Already covered at a high level

The current tree under `src/geocase/data/core/vector/` already includes:

- all major geometry families (`Point`, `MultiPoint`, `LineString`, `MultiLineString`, `Polygon`, `MultiPolygon`, `GeometryCollection`),
- multiple special-case folders (`crs`, `dateline`, `degenerate`, `empty`, `encoding`, `holes`, `invalid`, `precision`),
- many formats already represented (`GeoJSON`, `GPKG`, `Shapefile`, `Parquet`, `GML`, `KML`, `CSV_WKT`, `WKB`, `WKT`, `SQLite`, `FlatGeobuf`),
- several cases the roadmap still describes as “missing,” such as polar points, equator-crossing lines, Web Mercator baseline coverage, ambiguous validity, degenerate geometries, and precision cases.

### Real remaining gaps

The clearest unresolved gaps are narrower than the roadmap currently suggests:

- `parquet_mixed_schema_attributes`
- `format_limited_kml_case`
- `north_pole_polygon`
- `south_pole_polygon`
- `equator_polygon`
- `web_mercator_precision_case`
- a clearer decision on `null_geometry_row_gpkg` vs the existing `empty_geometry_gpkg`

### Structural gap

The bigger problem is not only missing cases. It is that the planning docs and coverage matrix are stale relative to the actual vector catalog.

That means Phase 2 must start by re-baselining scope.

---

## Implementation Sequence

### Step 1: Re-baseline Phase 2 scope

Before adding new data, compare these three sources and resolve contradictions:

- `docs/plans/03-consolidation-roadmap.md`
- `docs/contributing/vector-dataset-generation.md`
- `docs/_generated/vector-coverage-matrix.md`

Use the live tree under `src/geocase/data/core/vector/` as the source of truth.

**Output:** an updated understanding of what is truly missing.

#### Step 1 baseline findings

As of April 2026, the re-baseline shows that several items previously described as missing are already present in the live catalog, including:

- major geometry-family baseline coverage,
- multiple non-GeoJSON format baselines,
- `north_pole_point`, `south_pole_point`, `equator_crossing_line`, and `web_mercator_baseline`,
- `ambiguous_engine_dependent_polygon`, `degenerate_but_parseable_line`, `shapefile_field_truncation`, and existing precision cases.

The narrowed Phase 2 backlog after Step 1 is:

- `parquet_mixed_schema_attributes`
- `format_limited_kml_case`
- `north_pole_polygon`
- `south_pole_polygon`
- `equator_polygon`
- a decision on `web_mercator_precision_case`
- a decision on `null_geometry_row_gpkg` vs `empty_geometry_gpkg`
- an explicit v1.0 decision on whether sparse matrix-cell completeness is still in scope

### Step 2: Finish the clearest format-specific gaps

Prioritize the two most obvious outstanding format-focused cases:

- `parquet_mixed_schema_attributes`
- `format_limited_kml_case`

These are small, coherent additions and map cleanly to current format-specific coverage gaps.

**Output:** two new cases plus index, suite, and test updates.

### Step 3: Complete missing spatial complements

Add the most obvious missing CRS/spatial follow-ons:

- `north_pole_polygon`
- `south_pole_polygon`
- `equator_polygon`

Then decide whether `web_mercator_precision_case` is required as a true new gap or is better treated as a refinement of existing `EPSG:3857` coverage.

**Output:** stronger polar/equator polygon coverage with clear suite placement.

### Step 4: Clarify null-vs-empty semantics

Review whether `empty_geometry_gpkg` already covers the intended "null geometry row" behavior.

If yes, document that and avoid duplication.
If no, add a distinct `null_geometry_row_gpkg` case with clearly different metadata and behavior expectations.

**Output:** no ambiguity about GPKG null vs empty geometry coverage.

#### Step 4 decision (April 2026)

**No separate `null_geometry_row_gpkg` case is needed.**

The existing `empty_geometry_gpkg` case already contains both:

- a SQL-NULL geometry row (`null_row`), and
- a WKB-EMPTY geometry row (`empty_row`),

alongside two valid Point geometries.  Its `params` explicitly track
`null_geometry_rows: 1` and `empty_geometry_rows: 1`, and its tags include
`null_handling` and `empty`.  The notes document the NULL-vs-EMPTY distinction
across formats.

A regression test in `tests/unit/test_registry.py`
(`test_step4_empty_geometry_gpkg_covers_null_semantics`) codifies this decision.

### Step 5: Decide whether matrix completeness is still in scope

If v1.0 still requires stronger geometry × format completeness, prioritize sparse cells next, especially:

- `GeometryCollection` follow-up coverage,
- limited columnar/Arrow-family format coverage across more geometry families.

If not, explicitly defer that work instead of letting it remain as an implied promise.

**Output:** a clear release gate for Phase 2.

#### Step 5 decision (April 2026)

**Full geometry × format matrix completeness is deferred past v1.0.**

As of 103 vector cases the coverage picture is:

- The **10 core formats** (GeoJSON, GPKG, Shapefile, CSV_WKT, FlatGeobuf,
  GML, KML, SQLite, WKB, WKT) each cover at least 6 of 7 geometry types.
  The only systematic gap is GeometryCollection, which most formats support
  poorly or not at all.
- The **4 columnar/Arrow-family formats** (Arrow, Feather, GeoArrow, Parquet)
  have 12 sparse cells across Multi* and GeometryCollection families.
  These are low-value for v1.0 because the single-geometry baselines already
  exercise the same read/write paths.
- **30 sparse cells** remain out of 98 total (7 geom types × 14 vector formats).
  Filling them mechanically would add 30 near-identical cases with minimal
  additional risk coverage.

The v1.0 release gate is codified in `tests/unit/test_registry.py`
(`test_step5_matrix_completeness_baseline`): all 7 geometry families present,
core formats each covering ≥ 6 geometry types.

### Step 6: Refresh tests, suites, and docs together

For each batch of cases added, update all of the following in the same pass:

- `src/geocase/metadata/case-index.yaml`
- relevant files in `src/geocase/catalog/suites/`
- `tests/unit/test_registry.py`
- `tests/unit/test_selectors.py`
- `tests/unit/test_suites.py`
- `tests/unit/test_cases.py`
- `docs/_generated/vector-coverage-matrix.md`
- `scripts/generate_vector_coverage_matrix.py`
- `docs/plans/03-consolidation-roadmap.md`

**Output:** the code, tests, suites, and docs remain aligned.

#### Step 6 completion (April 2026)

Final housekeeping sweep performed:

- `test_selectors.py` and `test_cases.py` confirmed passing (146 tests).
- `scripts/generate_vector_coverage_matrix.py` updated: decision-needed items
  resolved to `deferred` or `resolved` status labels.
- `docs/_generated/vector-coverage-matrix.md` regenerated from live catalog.
- `docs/plans/03-consolidation-roadmap.md` Phase 2 section updated to reflect
  completion.
- `docs/contributing/vector-dataset-generation.md` already aligned from Step 1.
- All unit tests pass: 525+ passed, 1 skipped, 0 failed.

---

## Likely Files and Areas to Edit

### Data and metadata

- `src/geocase/data/core/vector/`
- `src/geocase/metadata/case-index.yaml`

### Suites

- `src/geocase/catalog/suites/core-vector.yaml`
- `src/geocase/catalog/suites/vector-crs-edge.yaml`
- `src/geocase/catalog/suites/vector-schema-encoding.yaml`
- any other suite affected by the new tags or case families

### Tests

- `tests/unit/test_registry.py`
- `tests/unit/test_selectors.py`
- `tests/unit/test_suites.py`
- `tests/unit/test_cases.py`
- selector-driven example tests that may widen automatically when new tags or formats are introduced

### Planning and matrix sources

- `scripts/generate_vector_coverage_matrix.py`
- `docs/_generated/vector-coverage-matrix.md`
- `docs/plans/03-consolidation-roadmap.md`
- `docs/contributing/vector-dataset-generation.md`

---

## Good First PR Batches

### Batch 1: Parquet + KML format behavior

Add:

- `parquet_mixed_schema_attributes`
- `format_limited_kml_case`

Why this batch works:

- small and coherent,
- clearly tied to format-specific behavior,
- likely to require limited suite/test updates.

### Batch 2: Polar polygon complements

Add:

- `north_pole_polygon`
- `south_pole_polygon`

Why this batch works:

- directly strengthens CRS/spatial coverage,
- complements already-existing polar point cases,
- easy to group under CRS-oriented suites.

### Batch 3: Equator + Web Mercator refinement

Add:

- `equator_polygon`
- `web_mercator_precision_case` (if still justified after scope review)

Why this batch works:

- keeps the focus on CRS and projection behavior,
- can share related selector and suite updates.

### Batch 4: Null vs empty GPKG semantics

Either:

- create `null_geometry_row_gpkg`, or
- document that `empty_geometry_gpkg` already covers the intended behavior and update metadata/tests accordingly.

Why this batch works:

- resolves a planning ambiguity,
- avoids duplicated fixtures.

### Batch 5: Sparse matrix-cell follow-ups

Only if still in scope for v1.0:

- add one or two `GeometryCollection` follow-ups,
- expand Arrow/columnar family coverage where still thin.

Why this batch works:

- addresses completeness without expanding Phase 2 too early.

---

## Risks and Caveats

### 1. Scope drift

The roadmap still implies broad missing coverage, but most of that work is already done. If implementation follows the old roadmap literally, it will duplicate existing cases.

### 2. Stale planning sources

The roadmap, the generated matrix, and the live catalog are not perfectly aligned. Phase 2 should not proceed until one source of truth is established.

### 3. Implicit test expansion

New vector cases can automatically enter selector-driven tests and examples if their metadata overlaps existing selectors. This may widen test coverage unexpectedly.

### 4. Suite asymmetry

Some suites are tightly curated and others are selector-driven. New cases will not land consistently unless suite intent is reviewed explicitly.

### 5. Null vs empty overlap

The existing `empty_geometry_gpkg` may already overlap the intended null-geometry coverage. Clarifying that first is cheaper than creating a duplicate case.

---

## Definition of Done

Phase 2 is complete when:

- all genuinely missing high-value vector gaps are filled or explicitly deferred,
- `case-index.yaml` is updated,
- affected suites are reviewed and updated,
- relevant registry/selector/suite/case tests pass,
- the vector coverage matrix reflects the real catalog,
- the roadmap and vector-planning docs no longer describe already-completed work as missing.

---

## Related Docs

- [`docs/plans/03-consolidation-roadmap.md`](03-consolidation-roadmap.md)
- [`docs/contributing/vector-dataset-generation.md`](../contributing/vector-dataset-generation.md)
- [`docs/_generated/vector-coverage-matrix.md`](../_generated/vector-coverage-matrix.md)

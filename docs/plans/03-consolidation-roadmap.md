# Consolidation Roadmap

> Created: April 2026
> Status: Active planning document (refreshed April 2026)

This document captures the consolidated plan for bringing GeoCase to a stable v1.0 release.

---

## Goals

1. **Consolidate existing functionality** — Ensure all implemented layers are stable and well-tested
2. **Expand raster test coverage** — Add raster edge cases and sample functions
3. **Resolve v1.0 surface area** — Decide which stubbed layers are in or deferred
4. **Clean up and align planning/docs** — Keep roadmap, generated docs, and package state synchronized
5. **Bug fixes and release polish** — Address issues discovered during consolidation

---

## Phase 1: Documentation Cleanup — ✅ Complete (April 2026)

See `02-documentation-consolidation.md` for detailed plan.

**Summary:**
- Create `docs/contributing/`, `docs/design/`, `docs/plans/` subfolders
- Move planning and design docs out of root
- Merge related testing/edge-case docs
- Update outdated content in `getting-started.md`, `adding-a-case.md`

**Outcome:** docs reorganized and contributor/design/plans structure established.

---

## Phase 2: Vector Edge Cases — ✅ Complete (April 2026)

See `04-phase-2-vector-edge-cases.md` for the full implementation log.

### Summary of outcomes

- **Re-baselined** the gap list against the live catalog (Step 1).
- **Added 5 new cases:** `parquet_mixed_schema_attributes`, `format_limited_kml_case`, `north_pole_polygon`, `south_pole_polygon`, `equator_polygon` (Steps 2–3).
- **Decided** `null_geometry_row_gpkg` is not needed — `empty_geometry_gpkg` already covers both NULL and EMPTY semantics (Step 4).
- **Decided** `web_mercator_precision_case` is not needed — existing `web_mercator_baseline` is sufficient.
- **Deferred** full geometry × format matrix completeness past v1.0 — the 10 core formats each cover ≥ 6 of 7 geometry types (Step 5).
- **Added** Plan 05 universal format & geometry compliance gate (`src/geocase/assertions/format_compliance.py`).
- All decisions are codified in regression tests in `tests/unit/test_registry.py`.

**Total vector cases:** 103.  
**Total indexed cases:** 115.

---

## Phase 3: Raster Test Coverage — Current Priority

This is now the next highest-value implementation track.

### Objectives

- strengthen raster fixture breadth the same way Phase 2 strengthened vector coverage,
- create reusable raster sample-function tests similar to the vector interview-question pattern,
- close the largest remaining catalog/testing gaps before v1.0.

### New raster cases needed
- Multi-band raster
- Rotated/skewed transforms
- Different dtypes (int8, int16, int32, float32, float64)
- Cloud-Optimized GeoTIFF (COG)
- Rasters with overviews
- Different compression methods
- Large nodata regions

> **Good to know:** see
> [`docs/contributing/raster-dtypes-and-radiometric-resolution.md`](../contributing/raster-dtypes-and-radiometric-resolution.md)
> for the full explanation of how dtype coverage relates to — but is broader
> than — radiometric resolution.

### Sample functions pattern
Mirror the interview-questions approach from `examples/_easy_geospatial_interview_test_support.py`:
- Simple implementation (common approach)
- Perfect implementation (handles edge cases)
- Parameterized tests across all raster cases

### Suggested sequencing

1. Start with **multi-band** and **rotated/skewed transform** fixtures.
2. Add parameterized sample-function tests that auto-discover raster cases.
3. Follow with dtype/compression/overview coverage once the test harness is in place.

**Estimated effort:** 2-3 sessions

---

## Phase 4: Stub Module Resolution

Decide fate of each stub module:

| Module | Options |
|---|---|
| `loaders/*.py` | Implement or delete (cases already load via geopandas/rasterio) |
| `storage/*.py` | Implement for remote cases or defer |
| `api/*.py` | Implement for stable surface or defer |
| `cli/*.py` | Implement basic commands or defer to post-v1.0 |
| `catalog/validators.py` | Keep logic in scripts or move to package |
| `catalog/manifests.py` | Implement for external catalogs or defer |

**Recommendation:**
- Delete `loaders/` (redundant with current case implementations)
- Keep validators in scripts for now
- Prioritize `catalog/manifests.py` if external catalogs are needed for v1.0
- Defer `storage/`, `api/`, and `cli/` unless Phase 3 or release work proves they are necessary

**Estimated effort:** 1 session for decisions, variable for implementation

---

## Phase 5: Final Polish

- Run full test suite, fix any failures
- Update `pyproject.toml` version
- Complete `CHANGELOG.md`
- Final docs review
- Tag v1.0.0 release

**Estimated effort:** 1-2 sessions

---

## Not in Scope for v1.0

- Docker/Kubernetes support (not needed for pytest plugin)
- Logging infrastructure (errors surface via pytest)
- Case recommendation web service (future feature)
- CLI tooling (maintainer convenience, not user-facing)

---

## Dependencies

```
Phase 1 (Docs) ──┐
                 ├──► Phase 5 (Polish) ──► v1.0 Release
Phase 2 (Vector) ┤
                 │
Phase 3 (Raster) ┤
                 │
Phase 4 (Stubs) ─┘
```

Phases 1-4 can proceed in parallel. Phase 5 depends on all others completing.

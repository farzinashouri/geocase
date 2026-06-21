# Raster Action Plan

> Created: June 2026
> Status: Active execution plan

This document turns the broader raster strategy in
[`docs/plans/07-raster-coverage-plan.md`](07-raster-coverage-plan.md)
into a concrete implementation sequence.

It is intentionally biased toward the **smallest end-to-end tranche** that
moves GeoCase's raster support forward in a measurable way.

---

## Purpose

Expand raster coverage without splitting it into a separate package or repo.
The goal is to keep raster work inside GeoCase while giving it a clearer,
more maintainable internal structure and a practical execution order.

This plan assumes:

- bundled raster fixtures stay small, synthetic, and redistributable,
- realistic larger scenes remain manifest-backed follow-on work,
- metadata should drive raster validation wherever possible,
- and the first implementation pass should optimize for practical coverage,
  not maximum completeness.

---

## Current reality

The repo already has a working raster baseline, but several of the intended
expansion points are still stubs or partial placeholders.

### Already real

- `src/geocase/cases/raster.py`
- `src/geocase/assertions/raster.py`
- `src/geocase/data/core/raster/`
- `src/geocase/catalog/models.py`
- `src/geocase/catalog/registry.py`
- `scripts/build_case_index.py`
- `scripts/validate_catalog.py`
- raster coverage already exercised in `tests/unit/test_case_models.py`

### Still stubbed or incomplete

- `tests/unit/test_raster_loaders.py`
- `tests/integration/test_core_raster_suite.py`
- `src/geocase/loaders/generic.py`
- `src/geocase/loaders/geopandas_loader.py`
- `src/geocase/loaders/rasterio_loader.py`
- `src/geocase/loaders/xarray_loader.py`
- `scripts/generate_checksums.py`
- `src/geocase/data/core/raster/affine_transform_quirk/case.yaml`

That means the next raster phase should not start by adding large amounts of
new fixture data. It should first make the raster path easier to scale.

---

## Execution goals

The raster expansion phase is successful when it delivers all of the following:

- typed raster expectations in metadata rather than ad hoc test logic,
- reproducible raster fixture generation,
- one canonical raster integration suite,
- a first EO-oriented bundled fixture tranche,
- CI validation for raster coverage shape, not just individual files,
- and a clean bridge to future manifest-backed raster scenes.

---

## Implementation sequence

### Step 1 — Re-baseline the live raster catalog

**Goal:** document what exists today before adding anything new.

**Actions**

- Audit `src/geocase/data/core/raster/` and record which cases are live,
  which are placeholder-only, and which already represent useful coverage.
- Confirm the actual raster metadata patterns used in current `case.yaml`
  files, especially fields now stored under `params`.
- Reconcile this reality with:
  - `docs/plans/07-raster-coverage-plan.md`
  - `docs/plans/03-consolidation-roadmap.md`
  - `docs/contributing/raster-dtypes-and-radiometric-resolution.md`
- Mark placeholder entries such as
  `src/geocase/data/core/raster/affine_transform_quirk/case.yaml` as either:
  - ready for completion now, or
  - explicitly deferred.

**Output**

- a confirmed list of live raster cases,
- a short list of placeholder/stub raster assets,
- and an accurate v1.0 raster starting point.

### Step 2 — Add typed raster metadata expectations

**Goal:** stop relying on loosely structured `params` for key raster checks.

**Primary file:** `src/geocase/catalog/models.py`

**Actions**

- Extend `AssertionHints` with raster-specific fields such as:
  - `expected_band_count`
  - `expected_dtype`
  - `expected_shape`
  - `expected_nodata_value`
  - `nodata_convention`
  - `expected_compression`
  - `expected_overviews`
  - `expected_band_names`
  - `expected_scale_factor`
  - `expected_colormap_present`
  - `is_cog`
- Decide which currently untyped `params` values should migrate into typed
  assertion metadata versus remain free-form fixture parameters.
- Standardize raster tag vocabulary for:
  - product family,
  - geography,
  - and delivery style.
- Update existing raster `case.yaml` files to use the new typed fields where
  possible.

**Output**

- a typed metadata surface for raster expectations,
- reduced ambiguity in raster `case.yaml` files,
- and better support for registry-driven raster assertions.

### Step 3 — Establish raster fixture-generation tooling

**Goal:** make raster fixtures reproducible instead of opaque committed blobs.

**Primary files:**

- `scripts/generate_checksums.py`
- new raster generator script(s) under `scripts/`

**Actions**

- Implement `scripts/generate_checksums.py` so checksums can be generated and
  refreshed consistently.
- Add one or more reproducible raster generator scripts using deterministic
  array creation and explicit metadata writing.
- Define a simple generator convention for:
  - CRS,
  - shape,
  - dtype,
  - nodata,
  - transform,
  - band names,
  - compression,
  - overview creation,
  - and checksum refresh.
- Ensure generated fixtures still pass:
  - `scripts/build_case_index.py --check`
  - `scripts/validate_catalog.py`

**Output**

- reproducible raster artifact generation,
- a consistent maintainer workflow for adding raster fixtures,
- and less long-term fixture drift.

### Step 4 — Ship the Priority 1 EO fixture tranche

**Goal:** add the smallest high-value EO-oriented raster set.

**Target cases**

- `optical_rgb_small`
- `multispectral_s2_like_small`
- `water_mask_small`
- `dem_small`
- `ndvi_small`

**Actions**

- Generate each case through the new raster fixture workflow.
- Add clear `case.yaml` metadata with typed expectations and standardized tags.
- Register the new cases through the normal index build path.
- Keep fixture size tiny enough for normal CI use.
- Prefer behaviorally meaningful arrays over visually realistic imagery.

**Output**

- the first practical EO-oriented raster bundle,
- coverage for masking, multispectral handling, DEM usage, and derived
  products,
- and a stable foundation for later radar/COG/geography work.

### Step 5 — Expand raster assertions

**Goal:** make raster validation metadata-driven and scalable.

**Primary file:** `src/geocase/assertions/raster.py`

**Actions**

- Add helpers for:
  - band-count checks,
  - dtype checks driven by typed metadata,
  - shape checks,
  - explicit nodata-value checks,
  - NaN nodata checks,
  - compression checks,
  - overview presence checks,
  - COG-style structural checks,
  - band-name checks,
  - optional colormap/category checks.
- Keep the assertion style consistent with existing helpers:
  lightweight functions that raise `AssertionError` with clear failure text.
- Add a metadata-dispatch layer comparable to the vector sanity path so raster
  expectations can be applied consistently from case metadata.

**Output**

- reusable raster assertion helpers,
- less case-specific assertion duplication,
- and a scalable validation model for future fixtures.

### Step 6 — Create the canonical raster integration suite

**Goal:** move from scattered raster checks to one registry-driven suite.

**Primary file:** `tests/integration/test_core_raster_suite.py`

**Actions**

- Replace the current stub with an active integration suite.
- Resolve raster cases from `CaseRegistry` rather than hard-coded file paths
  where practical.
- Parameterize across selected bundled raster cases and dispatch assertions from
  typed metadata.
- Use targeted unit tests for edge behaviors, while reserving the integration
  suite for catalog-wide consistency.
- Decide whether this suite should cover all bundled raster cases or a tagged
  subset for CI speed.

**Output**

- one meaningful raster integration entry point,
- stronger regression protection for the live raster catalog,
- and less fragmentation across examples and unit-only coverage.

### Step 7 — Hook raster validation into CI and reporting

**Goal:** make raster growth visible and enforceable.

**Primary files:**

- `ci/extended-tests.yml`
- `ci/catalog-validation.yml`
- new generated raster coverage doc under `docs/_generated/`

**Actions**

- Ensure the real raster integration suite runs in `ci/extended-tests.yml`.
- Add a raster coverage-matrix generator that mirrors the existing vector
  matrix workflow.
- Generate a raster coverage markdown artifact under `docs/_generated/`.
- Add a diff gate in `ci/catalog-validation.yml` so coverage-matrix drift is
  visible during CI.

**Output**

- CI awareness of raster coverage shape,
- an inspectable raster coverage matrix,
- and clearer maintainer visibility into what is still missing.

### Step 8 — Add raster example workflows

**Goal:** demonstrate algorithm testing, not only file opening.

**Candidate examples**

- water masking from a binary raster mask,
- NDVI-style band calculations,
- DEM preprocessing or terrain-derived logic,
- simple SAR summary statistics in a later tranche.

**Actions**

- Add small example functions under `examples/` that operate on raster cases
  through the public testing pattern already used elsewhere in the repo.
- Parameterize them over the new raster fixtures where useful.
- Keep examples focused on realistic algorithm behavior with small fixtures.

**Output**

- user-facing proof that GeoCase can test raster algorithms,
- clearer docs/examples for contributors,
- and stronger justification for the new fixture families.

**Limitations surfaced by the new fixtures**

- **Rotated geotransforms break `-projWin` clipping.** The
  `rotated_two_islands` fixture (`footprint_edge_cases/`) carries non-zero
  rotation/skew terms (`gt[2]`/`gt[4]`). The naive Question 8 helper
  `clip_raster` calls `gdal.Translate(..., projWin=...)`, which GDAL
  explicitly rejects on rotated grids, so it raises `RuntimeError`. This is
  the intended teaching contrast: `clip_raster_perfect` now detects the
  rotated geotransform and falls back to `gdal.Warp(..., outputBounds=...)`,
  resampling onto an axis-aligned grid clipped to the requested bounds.
  Regression tests:
  `test_clip_raster_fails_on_rotated_geotransform` (asserts the simple helper
  raises) and `test_clip_raster_perfect_handles_rotated_geotransform`
  (asserts the warp fallback succeeds and yields a north-up output). The
  parametrized all-cases clip tests continue to `skip` rotated rasters, since
  axis-aligned `projWin` clipping is their documented contract. The other
  raster Question helpers (9 pixel→world, 10 alignment, 14 sampling, 17
  rasterize) pass unchanged across every bundled raster fixture.

### Step 9 — Add Priority 2 through Priority 4 raster families

**Goal:** broaden coverage after the first vertical slice is stable.

**Priority 2**

- `cog_singleband_small`
- `cog_multispectral_small`
- `geotiff_external_overviews_small`
- compression variants

**Priority 3**

- `sar_vv_small`
- `sar_dualpol_small`
- `optical_polar_small`
- `optical_dateline_small`
- `optical_equator_small`

**Priority 4**

- `multispectral_mixed_resolution_small`
- `dem_nan_nodata_small`
- `ndvi_scaled_int16_small`
- `landcover_small`

**Actions**

- Add these only after Steps 2 through 8 are working.
- Reuse the typed metadata and generator path rather than adding hand-authored
  one-off fixtures.
- Keep each tranche small enough to review and validate independently.

**Output**

- broader product-family coverage,
- delivery-style realism,
- and higher-confidence raster support for v1.0.

### Step 10 — Define the manifest-backed raster follow-on

**Goal:** separate bundled structural coverage from larger realistic scenes.

**Related plans**

- `docs/plans/06-manifest-support.md`
- `docs/contributing/manifests-and-storage.md`

**Actions**

- Identify which future raster cases should remain remote-only.
- Pair bundled fixtures with realistic analogs where possible.
- Avoid shipping large real EO scenes inside the package.
- Defer transport, cache, and fetch mechanics to the manifest/storage work.

**Output**

- a clear boundary between bundled and remote raster coverage,
- less package bloat,
- and a path toward realistic larger-scene testing later.

---

## Recommended ordering for active implementation

If work starts immediately, the practical order should be:

1. Step 1 — Re-baseline the live raster catalog
2. Step 2 — Add typed raster metadata expectations
3. Step 3 — Establish raster fixture-generation tooling
4. Step 4 — Ship the Priority 1 EO fixture tranche
5. Step 5 — Expand raster assertions
6. Step 6 — Create the canonical raster integration suite
7. Step 7 — Hook raster validation into CI and reporting
8. Step 8 — Add raster example workflows
9. Step 9 — Add Priority 2 through Priority 4 raster families
10. Step 10 — Define the manifest-backed raster follow-on

This order keeps the first raster expansion tranche grounded in reusable
infrastructure instead of immediately creating a large maintenance backlog.

---

## Decisions captured in this plan

### Keep raster in the main repo

Raster should stay in the main GeoCase repository and package.
The immediate need is better internal structure, not a separate repository or
package split.

### Prefer internal separation over repository separation

As raster expands, the codebase should separate raster concerns more clearly
inside GeoCase, for example by:

- promoting `src/geocase/assertions/raster.py` into a raster assertion
  subpackage when it becomes large enough,
- grouping raster fixtures more clearly by product family or behavior,
- and keeping manifest-backed realistic scenes outside the bundled core.

### Use vector coverage tooling as the model

The vector side already has a coverage-matrix workflow and generated reporting.
Raster expansion should mirror that pattern rather than inventing a separate
process.

---

## Open questions

1. Should raster fixtures move immediately to a vector-style grouped directory
   hierarchy, or should the current flat structure remain until more cases land?
2. Should `numpy` become an explicit dependency for raster-support workflows,
   or remain transitive through optional raster tooling?
3. How deep should first-pass COG validation go before optional dependencies
   become necessary?
4. Should `tests/integration/test_core_raster_suite.py` cover all bundled
   raster cases or only a fast tagged subset in default CI?
5. Which existing raster placeholders should be completed now versus deferred?

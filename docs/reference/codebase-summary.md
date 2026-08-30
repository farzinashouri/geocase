# Codebase Summary

> Created: June 2026 — revised August 2026 for the v1.0 release.
> Audience: contributors and maintainers

This document is a concise map of the current GeoCase codebase.
It focuses on how the package is organized today, which parts are already
working, and which areas are deliberately deferred.

Nothing in `src/geocase/` is a stub. The empty-module pattern was retired in Batches 1–4:
every one-line docstring placeholder was implemented or deleted. Where something is
absent — the CLI, storage transport — it is absent by decision, and the decision is
recorded in the roadmap's decision log.

For roadmap-level sequencing, see [`development-plan.md`](https://github.com/farzinashouri/geocase/blob/main/docs/plans/development-plan.md) — the
single roadmap. The superseded planning documents it replaced are retained as an
implementation log in [`../plans/archive/`](https://github.com/farzinashouri/geocase/blob/main/docs/plans/archive/index.md).

---

## What GeoCase is

GeoCase is a geospatial testing toolkit built around a **catalog of cases**.
Each case is a small dataset plus metadata explaining:

- what it represents,
- what behavior it is meant to test,
- how it should be loaded,
- and what assertions or expectations should hold.

The core runtime flow is:

`case.yaml -> Pydantic metadata -> registry -> selectors or suites -> case object -> load/open -> test assertions`

That pattern is the main organizing idea across the package.

---

## High-level package layout

### `src/geocase/catalog/`

This is the metadata and discovery core.

Key responsibilities:

- define typed metadata models,
- load YAML into runtime objects,
- discover cases from the bundled index,
- resolve named suites,
- and filter cases by metadata.

Important files:

- `src/geocase/catalog/models.py`
- `src/geocase/catalog/loader.py`
- `src/geocase/catalog/registry.py`
- `src/geocase/catalog/selectors.py`
- `src/geocase/catalog/suites.py`

Current status:

- this is one of the most complete and central parts of the codebase,
- `models.py` uses Pydantic v2,
- raster expectations are only lightly typed today,
- and tag vocabulary is still mostly free-form rather than strongly normalized.

### `src/geocase/cases/`

This layer turns metadata into loadable runtime objects.

Important files:

- `src/geocase/cases/base.py`
- `src/geocase/cases/vector.py`
- `src/geocase/cases/raster.py`
- `src/geocase/cases/netcdf.py`
- `src/geocase/cases/factory.py`

Current behavior:

- `BaseCase` provides shared metadata/path behavior,
- `VectorCase` contains format-aware loading branches,
- `RasterCase` opens rasters lazily with Rasterio,
- `NetCDFCase` is the xarray-backed variant,
- and the factory dispatches by case category.

Current design note:

- some format-specific behavior still lives directly in the case classes,
  especially for vector.
- `loaders/` is implemented and is the single raster load path: `cases/raster.py`
  calls `loaders/rasterio_loader.open_raster`, which closed the last open item
  from plan 03's Phase 4.

### `src/geocase/assertions/`

This layer contains reusable test assertions.

Important files:

- `src/geocase/assertions/geometry.py`
- `src/geocase/assertions/crs.py`
- `src/geocase/assertions/raster.py`
- `src/geocase/assertions/topology.py`
- `src/geocase/assertions/footprint.py`
- `src/geocase/assertions/metadata.py`

Current behavior:

- assertion helpers are intentionally lightweight,
- they mostly raise `AssertionError` with direct failure messages,
- and the metadata-aware layer dispatches expectations from case metadata.

Raster note:

- raster assertions exist and work,
- but they are still relatively small compared with the planned raster
  coverage expansion.

### `src/geocase/pytest_plugin/`

This is the main user-facing execution surface for `pytest` workflows.

Important files:

- `src/geocase/pytest_plugin/__init__.py`
- `src/geocase/pytest_plugin/fixtures.py`
- `src/geocase/pytest_plugin/markers.py`
- `conftest.py`

Current behavior:

- provides fixtures and marker-driven selection,
- supports suite- and selector-based parameterization,
- and is already one of the stronger, more complete parts of the project.

### `src/geocase/data/`

This is the bundled catalog content.

Important areas:

- `src/geocase/data/core/`
- `src/geocase/data/core/vector/`
- `src/geocase/data/core/raster/`
- `src/geocase/data/core/suites/`

Current behavior:

- vector coverage is broader and more structured,
- raster coverage is useful but still much smaller,
- suites define named selections over the catalog,
- and the bundled core is intentionally compact and CI-friendly.

### `src/geocase/loaders/`

This package is intended to separate file-format I/O from case objects.

Important files:

- `src/geocase/loaders/generic.py`
- `src/geocase/loaders/geopandas_loader.py`
- `src/geocase/loaders/rasterio_loader.py`
- `src/geocase/loaders/xarray_loader.py`

Current status:

- `rasterio_loader.py` is the single raster load path — `cases/raster.py` calls it rather
  than opening rasters itself,
- the vector and xarray sides are thinner, and some format-specific branching still lives
  in `cases/vector.py`,
- so this is an active subsystem on the raster side and a partial refactor boundary on the
  vector side.

### `src/geocase/storage/`

This package is for artifact integrity checking.

Current status:

- `hashing.py` is implemented and is the single SHA-256 implementation —
  `scripts/generate_checksums.py` imports it,
- transport (`local.py`, `remote.py`, `cache.py`) is **deferred to v1.1** and the
  former stub files were deleted rather than left implying a commitment.

### `src/geocase/api/`

The stable import surface for v1.0, implemented in Step 15. `import geocase` exposes a
pinned **27-name** `__all__`, asserted against a literal in
`tests/unit/test_public_api.py` so the surface cannot widen or narrow by accident. The
compatibility promise for v1.0 covers this surface and the pytest workflow, and nothing
else.

One import constraint is load-bearing: `catalog/roots.py` **cannot** be re-exported from
`geocase.catalog`. It is the one catalog module that imports `geocase.cases`, while
`cases/base.py` imports `catalog/models.py`, so eager re-export makes `import geocase`
circular. Import it directly.

### `src/geocase/cli/` — removed

There is no CLI. The stubs and the broken `[project.scripts]` entry point were removed
for v1.0; see the Decision log in [`development-plan.md`](https://github.com/farzinashouri/geocase/blob/main/docs/plans/development-plan.md).

---

## Data model and metadata conventions

The metadata model in `src/geocase/catalog/models.py` is one of the main
stabilizing layers in the project.

It currently defines:

- `CaseMetadata`
- `SuiteMetadata`
- `SuiteSelection`
- `AssertionHints`
- supporting file/source/remote models
- and shared literal-type aliases for category, format, tier, size, storage,
  loader hint, and status.

Important current characteristics:

- metadata is intentionally strict enough to keep the catalog consistent,
- `case.yaml` is the source of truth for bundled cases,
- suites are separate metadata files that resolve into case lists,
- and raster still relies on a mix of typed hints plus loosely structured
  `params` values for some expectations.

That last point is one of the main reasons the raster action plan emphasizes
stronger typed raster expectations.

---

## How catalog discovery works

The bundled catalog is built around index files and registry loading.

Important flow:

1. metadata paths are listed in a catalog index,
2. loader functions parse YAML into typed models,
3. `CaseRegistry` resolves metadata into in-memory objects,
4. selectors and suites filter that catalog for tests,
5. `cases.factory` turns metadata into runtime case objects.

Important files:

- `src/geocase/catalog/loader.py`
- `src/geocase/catalog/registry.py`
- `src/geocase/catalog/selectors.py`
- `src/geocase/catalog/suites.py`
- `scripts/build_case_index.py`
- `scripts/validate_catalog.py`

Current design characteristic:

- the catalog path is relatively mature,
- while some downstream subsystems still need polishing.

---

## Vector coverage today

Vector support is currently the most mature modality in the repo.

Characteristics:

- broad bundled coverage across geometry types and formats,
- edge-case organization under `src/geocase/data/core/vector_edge/`,
- generated reporting via `scripts/generate_vector_coverage_matrix.py`,
- and CI gating around the generated vector coverage matrix.

This vector side provides the clearest template for how raster coverage should
scale:

- richer metadata,
- reproducible planning,
- coverage reporting,
- and clearer integration suites.

---

## Raster coverage today

Raster support is functional but not yet as broad or as structured as vector.

Current live raster assets include coverage for:

- baseline GeoTIFF loading,
- NoData handling,
- shifted alignment,
- multiband behavior,
- several dtype families,
- UTM boundary behavior,
- and footprint-oriented raster edge cases.

Important files:

- `src/geocase/cases/raster.py`
- `src/geocase/assertions/raster.py`
- `src/geocase/data/core/raster/`
- `examples/test_raster_nodata_suite.py`
- `examples/test_gdal_footprint.py`
- `docs/contributing/raster-dtypes-and-radiometric-resolution.md`

Current limitations:

- the dedicated raster integration suite is implemented
  (`tests/integration/test_core_raster_suite.py`), alongside four unit modules,
- the loader abstraction is implemented and is the single load path,
- fixture generation is reproducible and CI-gated:
  `scripts/generate_raster_fixtures.py --check` regenerates the 30 GeoTIFFs and fails on
  any byte difference, and `generate_checksums.py --check` covers the whole catalog,
- and the raster coverage matrix is generated and gated the same way the vector one is.

Two genuine gaps remain, both on the v1.1 list rather than pretended away: rotated or
skewed affine transforms and non-square pixels are not covered by any case, and no case
sits in a southern-hemisphere UTM zone. See the
[dataset catalog](../dataset-catalog.md#coverage-gaps).

---

## Tests and examples

GeoCase's tests are spread across:

- `tests/unit/`
- `tests/integration/`
- `tests/fixtures/`
- `examples/`

Current pattern:

- many important runtime behaviors are covered in unit tests,
- examples double as realistic usage demonstrations,
- and the empty stub test modules were deleted in Batch 3 rather than left standing.

`pytest tests -q` is green at **780 passed, 1 skipped**. Runs are directory-based rather
than an allowlist, so a new test file is picked up without being registered anywhere.
Line coverage was measured at **54%** and is reported without gating.

Notable current state:

- the pytest plugin is reasonably well covered,
- raster behavior is tested in real files today, but not yet consolidated into
  the intended canonical raster integration suite,
- and examples are an important part of the developer experience, not just
  optional demos.

---

## Scripts and maintainer tooling

The `scripts/` directory supports catalog maintenance and generated outputs.

Important scripts:

- `scripts/build_case_index.py`
- `scripts/validate_catalog.py`
- `scripts/generate_vector_coverage_matrix.py`
- `scripts/package_extended_cases.py`

Current status:

- index building and catalog validation are real maintainer workflows,
- generated vector coverage reporting is already part of CI expectations,
- but checksum automation and raster fixture generation are not yet implemented
  to the same level.

---

## Dependencies and packaging

`pyproject.toml` defines a relatively small core install and several optional
extras.

Current characteristics:

- core dependencies are intentionally light,
- raster support depends on optional tooling such as Rasterio,
- NetCDF support depends on `xarray`,
- development extras pull in test and lint tooling,
- and the project targets Python 3.9+.

This keeps the package lean, but it also means some modality-specific behavior
is intentionally optional.

---

## CI and generated artifacts

The `ci/` directory currently separates:

- core tests,
- extended tests,
- and catalog validation.

Current characteristics:

- vector coverage reporting is already wired into validation workflows,
- catalog consistency checks are part of CI,
- raster still needs a comparable generated coverage view,
- and some planned integration targets are present but not yet active.

---

## What is mature vs. what is still evolving

### Relatively mature

- metadata models and YAML loading,
- registry, selectors, and suites,
- case object basics,
- pytest plugin flow,
- vector coverage organization,
- bundled catalog validation,
- and documentation/planning structure.

### Still evolving

- raster breadth and metadata depth,
- loader abstraction separation,
- manifest and storage maturity,
- checksum and fixture-generation tooling,
- public API consolidation,
- CLI usefulness,
- and release automation.

---

## Practical mental model for contributors

When working in the repo, it helps to think in this order:

1. **metadata first** — define what the case or suite is,
2. **registry/selectors next** — make sure the catalog can discover it,
3. **runtime object after that** — ensure the case loads correctly,
4. **assertions and examples next** — show what behavior is expected,
5. **CI and generated docs last** — keep reporting and validation aligned.

That sequence matches how GeoCase is designed and usually leads to cleaner
changes than starting from ad hoc fixture files alone.

---

## Related documents

- [`structure-and-planning.md`](../contributing/structure-and-planning.md)
- [`workflow.md`](../contributing/workflow.md)
- [`manifests-and-storage.md`](../contributing/manifests-and-storage.md)
- [`raster-dtypes-and-radiometric-resolution.md`](../contributing/raster-dtypes-and-radiometric-resolution.md)
- [`development-plan.md`](https://github.com/farzinashouri/geocase/blob/main/docs/plans/development-plan.md) — the roadmap
- [`../plans/archive/`](https://github.com/farzinashouri/geocase/blob/main/docs/plans/archive/index.md) — superseded plans, retained as history

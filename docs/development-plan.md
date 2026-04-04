# Development Plan

This document is the high-level build plan for GeoCase. It summarizes what is already done, what is currently in progress, and what still needs to be implemented before the project is ready for a full public release.

---

## Current snapshot

- Core metadata, catalog, runtime case loading, and assertion layers are implemented.
- The pytest plugin is implemented and working for normal `pytest` usage.
- Practical examples and usage docs exist for real geospatial testing workflows.
- The main remaining work is polishing the pytest-first developer experience and filling in a few support layers.
- Packaging metadata exists, but there is not yet a dedicated release workflow for PyPI publishing.

---

## Completed work

### Step 1 — Metadata foundation ✅

Goal: define typed metadata models and load YAML safely.

Done:

- Pydantic models for case and suite metadata
- YAML loading helpers for cases, suites, and indexes
- Schema files for validation
- Case template for adding new entries
- Real metadata files for the bundled core dataset

Key files:

- `src/geocase/catalog/models.py`
- `src/geocase/catalog/loader.py`
- `src/geocase/metadata/schemas/`
- `src/geocase/templates/new_case.yaml`

### Step 2 — Catalog and selection layer ✅

Goal: discover cases and filter them by metadata.

Done:

- Registry lookup by case ID
- Selection/filtering by metadata fields
- Suite resolution from named suite definitions
- Public catalog exports
- Geometry-type filtering support added end-to-end

Key files:

- `src/geocase/catalog/registry.py`
- `src/geocase/catalog/selectors.py`
- `src/geocase/catalog/suites.py`
- `src/geocase/catalog/__init__.py`

### Step 3 — Runtime case objects ✅

Goal: turn metadata into loadable vector, raster, and NetCDF cases.

Done:

- Base case abstraction
- Vector case loading via GeoPandas
- Raster case access via Rasterio
- NetCDF case loading via xarray
- Metadata-to-case factory dispatch

Key files:

- `src/geocase/cases/base.py`
- `src/geocase/cases/vector.py`
- `src/geocase/cases/raster.py`
- `src/geocase/cases/netcdf.py`
- `src/geocase/cases/factory.py`

### Step 4 — Assertion helpers ✅

Goal: provide reusable geospatial assertions for tests.

Done:

- Geometry assertions
- CRS assertions
- Raster assertions
- Topology assertions
- Metadata-aware sanity assertions

Key files:

- `src/geocase/assertions/geometry.py`
- `src/geocase/assertions/crs.py`
- `src/geocase/assertions/raster.py`
- `src/geocase/assertions/topology.py`
- `src/geocase/assertions/metadata.py`

### Step 5 — Pytest plugin and examples ✅

Goal: make GeoCase feel native inside `pytest`.

Done:

- Pytest fixtures for registry and selected cases
- Marker registration for case, suite, and selector-driven tests
- Auto-parameterization hook
- Plugin entry point for installed usage
- Source-checkout fallback loading for local development
- Example tests for CRS, dateline, GDAL footprint, and real functions
- Marker typing cleanup to avoid static typing issues in strict checking

Key files:

- `src/geocase/pytest_plugin/__init__.py`
- `src/geocase/pytest_plugin/fixtures.py`
- `src/geocase/pytest_plugin/markers.py`
- `conftest.py`
- `examples/`

### Step 6 — Documentation expansion ✅

Goal: explain how to use GeoCase in practice.

Done:

- Testing guide for using GeoCase with real functions
- Parameterized usage examples
- Workflow/project status documentation
- Product-direction docs for the recommendation service idea
- README quick start refresh

Key files:

- `README.md`
- `docs/testing-your-function-with-geocase.md`
- `docs/using-parameterized-tests.md`
- `docs/workflow.md`
- `docs/case-recommendation-service.md`
- `docs/case-recommendation-api-spec.md`
- `docs/case-recommendation-user-flow.md`

---

## In progress

### Step 7 — Finish plugin hardening and case-driven examples 🚧

Goal: close the gap between a working plugin and a polished developer experience.

Why this step is needed:

- The plugin already works for happy-path usage, but a first public release needs confidence in failure paths too, such as missing markers, invalid selections, or ambiguous fixture usage.
- Because GeoCase is meant to feel native inside plain `pytest`, the plugin experience needs to be predictable and easy to debug when users make mistakes.
- The examples are part of the product, not just extras. They are the fastest way for users to understand how to write tests, so they should demonstrate the intended case-ID and metadata-driven workflow instead of relying on repository-relative file paths.
- As the catalog grows, older tests can accidentally depend on fixed case counts or path conventions. Hardening this layer prevents the plugin from becoming fragile as more cases are added.

Current focus:

- Add dedicated plugin integration/unit tests for error paths and edge cases
- Continue reducing direct file-path coupling in examples in favor of case IDs and metadata-driven parameters
- Finish harmonizing tests after adding more cataloged raster edge cases

Likely affected files:

- `examples/test_gdal_footprint.py`
- `tests/unit/test_registry.py`
- `tests/unit/test_selectors.py`
- `tests/unit/test_suites.py`
- `src/geocase/metadata/case-index.yaml`

Definition of done:

- Plugin behavior is covered by focused tests
- Example tests rely primarily on case IDs instead of repository-relative data paths
- Catalog growth does not break hard-coded test assumptions

### Step 8 — Implement validation and manifest support

Why this step is needed:

- GeoCase depends heavily on metadata quality. If case metadata, suite metadata, or extended manifests drift out of shape, users will see failures much later in the `pytest` workflow, where they are harder to diagnose.
- Validation provides an earlier and clearer failure point for maintainers and contributors adding new cases.
- Manifest support is important if the catalog grows beyond bundled core cases. It creates a structured way to describe external or extended datasets without overloading the core case index.
- Together, validation and manifest handling make the catalog safer to evolve and more trustworthy for users relying on selectors, suites, and packaged fixtures.

Needed:

- `src/geocase/catalog/validators.py`
- `src/geocase/catalog/manifests.py`
- Validation rules for case metadata, suite metadata, and extended manifests

Why it matters:

- Enables stronger catalog QA
- Supports safer external/extended catalog ingestion
- Helps keep pytest-facing fixtures and selectors trustworthy

---

## Remaining work

### Step 9 — Implement loader abstraction layer

Why this step is needed:

- Right now, the case classes carry some format-specific knowledge directly. That is fine for an early implementation, but it makes the runtime layer harder to extend cleanly.
- A dedicated loader layer separates “what a case is” from “how a file format is opened and interpreted”. That keeps the case model focused on metadata and lifecycle, while loaders own format details.
- This separation becomes more valuable as more formats, options, or edge behaviors are added. It reduces duplication and makes format-specific testing more precise.
- It also makes mocking or swapping I/O behavior easier in tests, which helps maintain reliability without requiring every test to touch real files.

Needed:

- `src/geocase/loaders/generic.py`
- `src/geocase/loaders/geopandas_loader.py`
- `src/geocase/loaders/rasterio_loader.py`
- `src/geocase/loaders/xarray_loader.py`

Why it matters:

- Keeps case classes thin
- Centralizes format-specific I/O behavior
- Makes future extension and mocking easier

### Step 10 — Implement storage and remote dataset support

Why this step is needed:

- Bundled tiny cases are enough for the current core workflow, but they are not enough for every realistic geospatial testing scenario.
- Some useful cases will be too large, too numerous, or too specialized to ship inside the package. Storage and remote support create a path for those cases without bloating the installed distribution.
- A dedicated storage layer also makes it possible to add caching, checksum verification, and download policies in one place instead of scattering them across case logic.
- This matters for both reliability and user trust: if GeoCase fetches remote artifacts, users need predictable path resolution, repeatable caching, and confidence that the downloaded data is the expected data.

Needed:

- `src/geocase/storage/local.py`
- `src/geocase/storage/remote.py`
- `src/geocase/storage/cache.py`
- `src/geocase/storage/hashing.py`

Why it matters:

- Supports downloadable cases and larger datasets
- Enables caching and checksum verification
- Makes manifests and remote catalogs practical

### Step 11 — Complete starter docs

Needed:

- Finish `docs/getting-started.md`
- Finish `docs/adding-a-case.md`

Why it matters:

- Reduces onboarding friction
- Makes contribution workflows clearer

### Step 12 — Add release workflow and PyPI publishing

Needed:

- Build step for source and wheel distributions
- Release checklist
- CI workflow for publishing
- Versioning and changelog process

Suggested release sequence:

1. Run unit and integration tests
2. Build distributions
3. Verify package contents
4. Publish to TestPyPI or PyPI
5. Tag release and update docs

### Step 13 — Implement public API helpers

Needed:

- `src/geocase/api/public.py`
- `src/geocase/api/types.py`

Why it matters:

- Gives users a stable, simple import surface
- Helps separate internal implementation from supported public API

### Step 14 — Optional maintainer tooling: CLI commands

Needed:

- `src/geocase/cli/main.py`
- `src/geocase/cli/list_cases.py`
- `src/geocase/cli/show_case.py`
- `src/geocase/cli/fetch_case.py`
- `src/geocase/cli/validate_catalog.py`

Why it matters:

- Useful for maintainers and power users
- Helpful for catalog inspection and validation outside `pytest`
- Not required for the core goal of running GeoCase through plain `pytest`

Suggested optional CLI milestone:

- `geocase list-cases`
- `geocase show-case <case-id>`
- `geocase fetch-case <case-id>`
- `geocase validate-catalog`

---

## Recommended execution order from here

If development continues from the current state, the most practical order is:

1. Finish plugin hardening and case-driven example cleanup
2. Complete validation and manifest support
3. Complete storage and remote dataset support
4. Finish starter docs
5. Add release automation and publish process
6. Implement public API layer if a simpler supported import surface is needed
7. Add CLI commands only if maintainer workflows need them

---

## Definition of “ready for first public release”

GeoCase is ready for a first public release when all of the following are true:

- Core packaged cases load correctly in installed usage
- Plugin-driven tests work with plain `pytest`
- Catalog validation is available
- Remote case fetching has at least one supported workflow
- Getting-started and adding-a-case docs are complete
- Release automation exists for publishing distributions

CLI tooling is optional for that first release. It can be added later if catalog maintenance or local inspection workflows need it.

At that point, PyPI publishing becomes a release operation instead of a manual future task.
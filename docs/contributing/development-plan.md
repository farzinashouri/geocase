# Development Plan

This document is the **single roadmap** for GeoCase. It summarizes what is already done,
what is in progress, and what still needs to land before v1.0.

> **This is the only roadmap.** Earlier planning documents (`docs/plans/01..10`) were
> collapsed into this one in July 2026 and moved to
> [`docs/plans/archive/`](../plans/archive/index.md), where they are retained as an
> implementation log. Do not add "what's next" content anywhere else — four competing
> roadmaps using five different sequencing vocabularies is what made this collapse
> necessary. The detailed rationale and measured evidence behind Steps 11-16 lives in
> [`docs/plans/archive/10-v1-release-strategy.md`](../plans/archive/10-v1-release-strategy.md).
>
> **This document defines *scope*: what each step contains.** For the *order* in which to
> execute them — the batching, the checkpoints, and the hard constraints — see
> [`execution-order.md`](execution-order.md). Where the two disagree, this one wins.

---

## Current snapshot

- Core metadata, catalog, runtime case loading, and assertion layers are implemented.
- The pytest plugin is implemented and working for normal `pytest` usage.
- The catalog holds **134 cases** (103 vector / 30 raster / 1 netcdf) and **715 tests**.
  Measured from `case-index.yaml`, not from a file count: the five
  `raster/footprint_edge_cases/case_*.yaml` entries share one directory, so counting
  files named `case.yaml` undercounts. Plan 10's "130 cases / 26 raster" was wrong on
  both figures.
- Validation, manifest parsing, loaders, and raster coverage are all implemented.
- Manifest support is implemented but **not yet reachable** at runtime (Step 14).
- The remaining work is release readiness: a public API surface, quality gates that
  actually run, and PyPI publishing.
- **v1.0 scope is deliberately narrow:** a compatibility promise about the pytest
  workflow and a small public API. Storage transport is deferred to v1.1.

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
- [`docs/testing-your-function-with-geocase.md`](../testing-your-function-with-geocase.md)
- [`docs/using-parameterized-tests.md`](../using-parameterized-tests.md)
- [`docs/contributing/workflow.md`](workflow.md)
- [`docs/design/case-recommendation-service.md`](../design/case-recommendation-service.md)

### Step 7 — Plugin hardening and case-driven examples ✅

Goal: close the gap between a working plugin and a polished developer experience.

Done:

- Focused plugin error-path tests for missing markers, unknown suites, ambiguous
  single-case fixture usage, and empty selections
- Example coverage that relies primarily on case IDs and metadata-driven parameters
  instead of repository-relative data paths
- Registry/selector/suite tests updated to avoid brittle hard-coded catalog counts
- Clearer `geocase` fixture error messages

Key files:

- `src/geocase/pytest_plugin/fixtures.py`
- `tests/unit/test_pytest_plugin.py`

### Step 8 — Validation and manifest support ✅

Goal: catch metadata drift at the catalog layer instead of deep inside a pytest run.

Done:

- `src/geocase/catalog/validators.py` — case, suite, and index validation rules
- `src/geocase/catalog/manifests.py` — manifest models and `load_manifest` / `from_sources`
- `scripts/validate_catalog.py`, CI-gated via `ci/catalog-validation.yml`
- `tests/unit/test_manifests.py`

Not done, and tracked separately as **Step 14**: nothing at runtime *calls*
`from_sources`, so manifest case ids are unreachable through the registry.

### Step 9 — Loader abstraction layer ✅

Goal: separate "what a case is" from "how a format is opened".

Done:

- `src/geocase/loaders/generic.py`
- `src/geocase/loaders/geopandas_loader.py`
- `src/geocase/loaders/rasterio_loader.py`
- `src/geocase/loaders/xarray_loader.py`

Note: `cases/vector.py`, `raster.py`, and `netcdf.py` still import geopandas/rasterio/
xarray directly, so there are currently two parallel load paths. Resolved in the
Decision log below — the loaders become the single path as part of Step 13.

### Step 10 — Raster coverage ✅

Goal: bring raster from a token presence to a usable baseline.

Done:

- 30 raster cases with generated, reproducible fixtures
- `scripts/generate_raster_fixtures.py` and its `--check` CI gate
- `scripts/generate_checksums.py` and its `--check` CI gate
- `scripts/generate_raster_coverage_matrix.py` plus a git-diff CI gate

### Step 11 — Make the advertised product actually work ✅

Closing the gap between what the package advertised and what a fresh install did.

Done:

- **11.1** Removed `[project.scripts]` from `pyproject.toml` and deleted
  `src/geocase/cli/`. The declared console script pointed at a one-line docstring, so
  every install got a `geocase` command that died with `ImportError`. Same reasoning
  applied to the `src/geocase/storage/{local,remote,cache}.py` stubs. `storage/hashing.py`
  is real and was kept.
- **11.2** Fixed bare `pytest`. Narrowed `testpaths` to `["tests"]`, and added
  `pytest.importorskip("osgeo")` in `examples/test_gdal_footprint.py` above its
  `from gdal_footprint import ...`. Both were needed: a guard inside
  `examples/gdal_footprint.py` would not work because it is not a test module, and the
  `sys.path` insert has to stay above the skip.
- **11.3** Rebuilt `.venv` on Python 3.11 (matching CI). The 16 failures were solely a
  missing `pyarrow` in a stale 3.14 venv. `pytest tests -q` → **714 passed, 1 skipped**.
- **11.4** Gave `storage/hashing.py` a consumer — `scripts/generate_checksums.py`
  duplicated `sha256_file` byte-for-byte and now imports it, so the only real storage
  code is reachable and covered by the existing `--check` CI gate.
- **11.5** Fixed `docs/remote-datasets.md`, whose unterminated fence rendered the whole
  published page as a code block, and added a status note that transport is v1.1.

Also, as a consequence of the roadmap collapse: archived-plan references in `scripts/`,
`src/`, and `tests/` were repointed at `docs/plans/archive/`, and the docs describing
`cli/` and the storage stubs were corrected.

---

## Remaining work for v1.0

Ordering and hard constraints are listed at the end of this section.

### Step 12 — Shrink the bundled catalog (the wheel *is* the product) ✅

The bundled data was 36 MB, and ~93% of that was accidental bloat. Five SQLite fixtures
(`point`, `multipoint`, `linestring`, `multilinestring`, `multipolygon`
`_sqlite_baseline/data.sqlite`) were 6.7 MB each while holding **one feature**, because
SpatiaLite's metadata initialization populates `spatial_ref_sys` with 6,559 EPSG rows
and `spatial_ref_sys_aux` with 6,508 more.

Done:

- Trimmed the unused SRS rows from **both** tables and `VACUUM`ed. Measured:
  6,844 KB → 240 KB per file (−96.5%). Bundled data **36 MB → 4.2 MB**.
  Verified the trimmed files keep all 27 tables, all four SpatiaLite signature tables,
  and the R-tree index, and that geometry and attributes are byte-identical to the
  originals.
- Regenerated all 129 `checksums.sha256`; only the five expected files changed.
- Added `scripts/generate_vector_fixtures.py` with a `--check` gate, covering all six
  bundled SQLite fixtures.
- Added `_SIZE_CLASS_MAX_BYTES` to `scripts/validate_catalog.py`. Confirmed it fails on
  the pre-shrink file with: *"declares size_class 'tiny' but its payload is 6844 KB,
  over the 512 KB limit"*.
- Widened the CI checksum gate from raster-only to the whole catalog, and moved the job
  to the `ubuntu-full` GDAL image (see below).

Two corrections to the original analysis, both found while verifying it:

- **`polygon_sqlite_baseline` does not prove the bloat was unintended.** It was cited as
  a 24 KB sibling holding the same payload, but it has **0 of 4 SpatiaLite signature
  tables and no R-tree** — it is plain SQLite, not SpatiaLite, and its case tags say so
  (`sqlite`, not `spatialite`). It is small because it is a *different kind of fixture*.
  The real cause is simply that SpatiaLite initialization was never trimmed, which makes
  the missing generator a stronger explanation, not a weaker one.
- **SpatiaLite fixtures are not byte-reproducible**, so the raster generator's
  byte-comparison `--check` model could not be reused. `spatialite_history` records
  wall-clock timestamps and the SQLite/SpatiaLite library versions, so two runs on one
  machine already differ. `generate_vector_fixtures.py --check` therefore compares
  *observable semantics* — layer, geometry column, fields, per-feature WKB and
  attributes, SRID, table signature, SRS row count, and a 512 KB size budget — with
  identifiers casefolded so a GDAL upgrade is not reported as drift.

Also note: `tiny` is capped at **512 KB**, not the 256 KB originally proposed. The
largest honest `tiny` case is a 240 KB SpatiaLite database, leaving only 6% headroom at
256 KB; 512 KB keeps ~2× headroom while staying 13× below the regression it guards.

**Open item for the first pipeline run:** the CI job image moved from
`gdal:ubuntu-small-3.10.0` to `ubuntu-full-3.10.0` because `ubuntu-small` does not ship
libspatialite. This could not be verified locally. If the job fails, the generator exits
**2** (cannot verify) rather than 1 (drift), with a message naming the fix.

### Step 13 — Quality gates you can trust

715 tests overstates the real coverage: CI runs a hand-kept allowlist that has drifted,
and ~300 tests never run.

- **13.1** Replace the allowlist with `pytest tests/ -q` (the whole suite is ~23s).
  Delete the three empty stub test files (`tests/unit/test_vector_loaders.py`,
  `tests/integration/test_core_vector_suite.py`, `tests/integration/test_remote_fetch.py`)
  — CI names the first and runs nothing. Update README's "Local equivalents".
- **13.2** Ruff: 1043 errors, 722 of them W191 tab-indentation. Sequence as three
  commits — (1) `ruff format`, whitespace only, verifying identical test output before
  and after so it never pollutes `git blame`; (2) `ruff check --fix` plus hand-fixes;
  (3) *then* add the CI job. Adding the gate first makes `ignore = ["W191","E501"]`
  tempting, which would entrench the mixed indentation permanently.
- **13.3** Mypy: fix the config before tightening it. The 18 current errors are all
  missing stubs, so `strict = true` has never checked a function body. Add
  `types-PyYAML` / `types-shapely`, add `ignore_missing_imports` overrides for
  rasterio/pyarrow/osgeo/netCDF4/geopandas, and fix `python_version`. Then gate
  `catalog/` + `api/` only under strict; ratchet outward in v1.1.
- **13.4** Python support matrix. **Partly done (Aug 2026):** `requires-python` is now
  `>=3.11` with classifiers 3.11–3.14, and `[tool.mypy] python_version` / `[tool.ruff]
  target-version` were moved off 3.9 to match. See the Decision log. Remaining: add a CI
  matrix over floor (3.11) and ceiling (3.14) — CI currently runs 3.11 only, so the
  ceiling is verified locally but not in the pipeline.
- **13.5** Markers. `slow` is declared and used zero times — drop it. Keep `remote` and
  wire it: attach `pytest.mark.remote` in `pytest_generate_tests` to cases whose
  `storage_class == "remote"`, giving users `pytest -m "not remote"`.
- **13.6** Measure coverage, don't gate it. ~300 tests are entering CI for the first
  time, so any floor picked now is arbitrary. Report it non-blocking, record it in the
  CHANGELOG, set the floor in v1.1.
- Also resolve the loaders duplication from Step 9: have `cases/raster.py` call
  `loaders/rasterio_loader.py` so there is one load path.

### Step 14 — Make manifests reachable and honest (no transport)

- **14.1** Wire `get_registry()` to `from_sources` with a `GEOCASE_MANIFESTS` env var.
  Read the env var **inside** `get_registry`, not at module import, or tests that
  monkeypatch it silently no-op.
- **14.2** Close the `CaseRegistry` asymmetry — manifest ids appear in
  `list_ids`/`__contains__`/`__len__` but not `list_cases`/`__iter__`/`get`. Do **not**
  force manifest entries into `list_cases()`; `ManifestCaseEntry` is not `CaseMetadata`
  and that would be a type lie. Add `is_remote()`, `list_remote_ids()`,
  `get_manifest()`, `get_manifest_entry()`, and have `get()` raise a
  `RemoteCaseUnavailableError` **subclassed from `KeyError`** so existing callers keep
  working, with `build_manifest_uri(...)` in the message.
- **14.3** `fixtures.py::_case_roots_by_id` is `@lru_cache`d and built only from
  `case-index.yaml`, so once manifest ids resolve, `_materialize_case` raises an
  internal-sounding `KeyError` that defeats 14.2's clear error. `_materialize_case` must
  check `is_remote()` first and `reset_registry()` must call `cache_clear()`.
  **14.2 and 14.3 must land in the same commit.**
- **14.4** Teach `scripts/validate_catalog.py` to validate `extended-manifests/`.
  Explicitly **allow** `sha256: "replace_me"` with a warning — gating on the
  placeholders would block the v1.1 work they exist for.
- **Out of scope:** no download, cache, unpack, or `materialize_case`.

### Step 15 — Public API surface

Mostly a facade; `src/geocase/catalog/__init__.py` already exports a clean `__all__`.

- `api/types.py` — re-export stable types from `catalog/models.py` and `cases/`.
  **Deliberately exclude the manifest models**: exporting a schema that will be revised
  in v1.1 pins the wrong thing. They stay importable from `geocase.catalog`.
- `api/public.py` — `list_cases()`, `get_case()`, `load_case()`, `show_case()`,
  `list_suites()`/`get_suite()`. **Move `_case_roots_by_id`/`_materialize_case` out of
  `pytest_plugin/fixtures.py`** into the API (or a shared `catalog/roots.py`) and have
  the plugin import them — duplicating it would create two `lru_cache`s to invalidate.
- `src/geocase/__init__.py` — the public surface plus `__version__` from
  `importlib.metadata.version("geocase")`, *not* a hardcoded literal.
- `tests/unit/test_public_api.py` — pin `sorted(__all__)` against a literal. This is the
  compatibility promise made executable.
- Document that `list_cases()` returns `CaseMetadata` while the `geocase` *fixture*
  yields a `BaseCase`.

### Step 16 — Docs truth pass and release

- **Stale facts to correct:** `contributing/workflow.md` says "216 unit tests" (715) and
  lists manifests and `loaders/` as stubs (both implemented);
  `structure-and-planning.md` and `codebase-summary.md` say raster has "2 cases + 1 stub"
  (30); `manifests-and-storage.md` says manifest parsing is stubbed — rewrite it rather
  than flip it, since storage is now *deliberately* deferred. Use **134 cases (103
  vector / 30 raster / 1 netcdf)** and **715 tests** as the canonical figures.
- **Orphaned case directory:** `data/core/raster/affine_transform_quirk/case.yaml` is an
  empty stub (a single comment line, no YAML), so `build_case_index.py` silently skips it
  and it appears in no index — yet the directory still ships in the wheel. Either author
  the case or delete the directory; a third empty-stub-implies-a-commitment instance
  after `cli/` and the storage modules.
- **mkdocs nav** omits `docs/_generated/raster-coverage-matrix.md` and
  `codebase-summary.md`. Both coverage matrices are CI-gated, so publishing only one is odd.
- **Release:** add `CHANGELOG.md`, noting the CLI entry-point removal as a **breaking
  change**; version `0.1.0` → `1.0.0`; classifier `3 - Alpha` →
  `5 - Production/Stable`; README status line → 1.0.
- **PyPI checklist:** verify the built wheel contains all 130 case directories (a 1.0
  wheel missing `data/core/` is the single highest-severity release risk); configure an
  sdist target; prefer trusted publishing via GitLab CI OIDC over a long-lived token;
  gate on `twine check dist/*`; TestPyPI dry run first; and **fix `project.urls`**, which
  point at GitHub while the project lives on GitLab.

### Ordering and hard constraints

Step 11 → 12 → 13 → 14 → 16, with Step 15 able to run in parallel with 13.

- 11.1 before 16 — cannot publish a broken entry point.
- 12 before the first upload — PyPI artifacts are immutable.
- 13.2's normalization commits before 13.2's CI gate.
- 13.4 before 16 — classifiers.
- 15 before 14.2 — `show_case` reports remote state.
- **14.2 and 14.3 must be atomic.**

If the priority is a fast first upload rather than a polished one, Steps 11 + 15 + 16
alone are sufficient to publish. Steps 13 and 14 make the release *trustworthy* rather
than merely *installable*, and 13 is what prevents the next round of drift.

---

## Decision log

Decisions that reversed or closed an earlier plan, recorded so the reversal is not
silently re-litigated.

| Date | Decision | Rationale |
|---|---|---|
| July 2026 | **v1.0 = the pytest workflow + a small public API.** The compatibility promise covers those two surfaces only. | They are the genuinely mature parts. Promising more would make the 1.0 label dishonest. |
| July 2026 | **`api/` is in scope for v1.0.** | `import geocase` currently exposes nothing, so there is no surface to make a 1.0 promise *about*. |
| July 2026 | **`cli/` is out of scope; the entry point and stubs are removed.** This withdraws plan 09's reversal of plan 03. | Plan 03 listed the CLI as explicitly not in scope and plan 09 reversed it without recording why. The declared console script was broken in every install. |
| July 2026 | **Storage transport deferred to v1.1.** Remote cases stay discoverable with clear errors; no download, cache, or unpack. | Both manifests are 100% placeholder — every `sha256` is `"replace_me"`, every `base_uri` is `example.org`, and nothing was ever published. Building transport for cargo that does not exist ships a layer whose only user is its own tests. **The v1.1 gate is: at least one real published archive with a real sha256.** |
| July 2026 | **`examples/` stays as-is** (repo-only, not in the wheel); cleanup revisited post-1.0. Lint and type gates are therefore **scoped to `src` and `tests`**. | Otherwise the 5,350-line demo corpus dominates every number and the gates mean nothing. |
| July 2026 | **Keep `src/geocase/loaders/` and make it the single load path** (have `cases/raster.py` call it). Closes the last open item from plan 03's Phase 4. | Plan 03 recommended deleting it, but four test modules import `rasterio_loader.open_raster`. Routing through it is a smaller diff than rewriting those tests, and it removes the duplication. |
| Aug 2026 | **Two dev environments, deliberately.** conda/3.14 (`environment.yml`) is primary; `.venv`/3.11 is the CI mirror. Documented in [`workflow.md`](workflow.md). | Only conda has the GDAL bindings, which are source-only on PyPI. Without them `pytest examples` collects 37 tests instead of 1238, because two support modules `importorskip("osgeo")`. Both interpreters pass `pytest tests` identically, so 3.14 is a supported ceiling, not a risk. |
| Aug 2026 | **`requires-python = ">=3.11"`**, not the `>=3.10` plan 10 proposed. Classifiers 3.11–3.14. | Promise only what is tested. CI runs 3.11 and development happens on 3.14, so both ends are real; 3.10 is installed nowhere and would have been the same untested claim as `>=3.9`, one version up. Also removes the `eval-type-backport` question entirely — `catalog/models.py` has 40 PEP 604 unions in pydantic model bodies under `from __future__ import annotations`, which needs ≥3.10 natively. Widen later once a matrix exists. |
| July 2026 | **One roadmap.** This document; `docs/plans/01..10` archived. | Four competing "what's next" documents using five sequencing vocabularies produced commit `6391e04 "stage 3 of plan 9 is done"`, which actually contained plan 08 Step 9 work. |

---

## Deferred to v1.1

- Storage transport (`remote`/`cache`/`local`/resolver) and end-to-end remote loading
- `tests/integration/test_remote_fetch.py`
- `scripts/package_extended_cases.py`
- Repo-wide mypy strict
- A coverage floor
- A CLI
- The `examples/` corpus cleanup

**The v1.1 storage gate is one real published archive with a real checksum.**

---

## Definition of "ready for v1.0"

- A clean `pip install` yields a working `import geocase` with a pinned public surface
- Plugin-driven tests work with plain `pytest`, with no collection errors
- Every test under `tests/` runs in CI; ruff and mypy pass at their scoped targets
- The built wheel contains the full case catalog
- Remote case ids are discoverable and fail with a documented, actionable error
- No installed `geocase` console script
- `CHANGELOG.md` exists and the docs contain no stale counts or "stubbed" claims

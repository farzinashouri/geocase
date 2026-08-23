# Workflow

This document describes the current state of the GeoCase project and the workflow being followed to bring it from skeleton to working product.

---

## Current status

GeoCase has a complete folder structure, 135 bundled cases, and fully implemented metadata, catalog, runtime, assertion, loader, and plugin layers, with 1701 passing tests.

### Recent updates (April 2026)

- Pytest plugin is now implemented (`pytest_plugin/__init__.py`, `pytest_plugin/fixtures.py`, `pytest_plugin/markers.py`).
- Plugin errors now call out common setup problems directly, including missing markers, unknown suites, empty selections, and ambiguous single-case usage.
- Plugin-driven examples were added/updated in `examples/` (CRS, dateline, GDAL footprint, real geospatial function).
- Selector model now supports first-class `geometry_type` filtering end-to-end.
- CI jobs are implemented for catalog validation, tests, lint, typecheck, and docs. (This entry originally described GitLab CI files under `ci/`; that layout was never adopted — CI is GitHub Actions in `.github/workflows/`.)
- Practical docs were added for usage and product direction:
	- [`docs/testing-your-function-with-geocase.md`](../testing-your-function-with-geocase.md)
	- [`docs/design/case-recommendation-service.md`](../design/case-recommendation-service.md)
	- [`docs/design/case-recommendation-api-spec.md`](../design/case-recommendation-api-spec.md)
	- [`docs/design/case-recommendation-user-flow.md`](../design/case-recommendation-user-flow.md)

### Development environments

Two environments are maintained deliberately, and they are not interchangeable.

| | Primary — conda `geocase` | CI mirror — `.venv` |
|---|---|---|
| Python | 3.14.3 (Miniforge) | 3.11.14 (pyenv) |
| Defined by | `environment.yml` | `pip install -e ".[dev]"` |
| GDAL / `osgeo` | ✅ 3.12.2 | ❌ not available |
| `pytest tests` | 780 passed, 1 skipped | 780 passed, 1 skipped |
| `pytest examples` | 1238 collected | **37 collected** |

**Use conda for day-to-day work**, and for anything touching `examples/` or fixture
generation. It is the only environment with the GDAL Python bindings, which are
source-only on PyPI.

**Use `.venv` to reproduce a CI failure** — CI runs `python:3.11`, and this is the
supported floor. Note that without `osgeo` the three interview-question example modules
skip at import (`pytest.importorskip("osgeo")` in
`examples/_easy_geospatial_interview_test_support.py` and
`_easy_raster_interview_test_support.py`), silently dropping 1193 tests. That is why
`.venv` is a floor check, not a substitute for the primary environment.

Both interpreters pass `pytest tests -q` identically, so 3.14 is a supported ceiling
rather than a risk. `testpaths` is `["tests"]`, so `examples/` only runs when named
explicitly.

```bash
# Primary
conda env create -f environment.yml    # first time
conda activate geocase

# CI mirror
python3.11 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"
```

### What is implemented

| Component | File(s) | Status | Tests |
|---|---|---|---|
| Pydantic models | `catalog/models.py` | ✅ Complete | 27 |
| YAML loader | `catalog/loader.py` | ✅ Complete | 18 |
| Registry | `catalog/registry.py` | ✅ Complete | 16 |
| Selectors | `catalog/selectors.py` | ✅ Complete | 21 |
| Suites | `catalog/suites.py` | ✅ Complete | 18 |  
| Catalog `__init__` | `catalog/__init__.py` | ✅ Complete | — |
| Base case | `cases/base.py` | ✅ Complete | 13 |
| Vector case | `cases/vector.py` | ✅ Complete | 10 |
| Raster case | `cases/raster.py` | ✅ Complete | 9 |
| NetCDF case | `cases/netcdf.py` | ✅ Complete | 9 |
| Case factory | `cases/factory.py` | ✅ Complete | 8 |
| Cases `__init__` | `cases/__init__.py` | ✅ Complete | — |
| Geometry assertions | `assertions/geometry.py` | ✅ Complete | 11 |
| CRS assertions | `assertions/crs.py` | ✅ Complete | 7 |
| Raster assertions | `assertions/raster.py` | ✅ Complete | 10 |
| Topology assertions | `assertions/topology.py` | ✅ Complete | 6 |
| Metadata assertions | `assertions/metadata.py` | ✅ Complete | 9 |
| Assertions `__init__` | `assertions/__init__.py` | ✅ Complete | — |
| Case metadata (8 of 8) | `data/core/*/case.yaml` | ✅ Complete | — |
| Real test data files | GeoJSON, GeoTIFF, NetCDF, GPKG | ✅ Complete | — |
| Suite definitions (3) | `catalog/suites/*.yaml` | ✅ Complete | — |
| Case index | `metadata/case-index.yaml` | ✅ Complete | — |
| Suite index | `metadata/suite-index.yaml` | ✅ Complete | — |
| YAML schemas (3) | `metadata/schemas/*.schema.yaml` | ✅ Complete | — |
| New-case template | `templates/new_case.yaml` | ✅ Complete | — |
| Extended manifest | `extended-manifests/public-extended.yaml` | ✅ Complete | — |
| Project config | `pyproject.toml` | ✅ Complete | — |
| Environment lock | `environment.yml` | ✅ Complete | — |
| Documentation | `docs/*.md` | ✅ Partial | — |

**Total: `pytest tests -q` is green at 780 passed, 1 skipped.**

The per-component counts above are indicative rather than exact — they predate the move to
directory-based test runs. The suite total is the number to trust, and it is the one CI
enforces.

### What is deliberately absent

Nothing in `src/geocase/` is a stub any more. The empty-module pattern was retired in
Batches 1–4: every one-line docstring placeholder was either implemented or deleted, on
the grounds that an empty module implies a commitment the project has not made.

- **`catalog/manifests.py` and `loaders/`** are implemented. `cases/raster.py` routes
  through `loaders/rasterio_loader.py`, which is the single raster load path.
- **`api/`** is implemented and is the v1.0 compatibility surface — 27 names, pinned by
  `tests/unit/test_public_api.py`.
- **`catalog/validators.py`** was deleted. Nothing imported it.
- **`cli/`** was deleted along with its broken `[project.scripts]` entry point. There is no
  CLI in v1.0; see the decision log in [the roadmap](../plans/development-plan.md).
- **`storage/`** transport is **deferred to v1.1**, deliberately rather than
  incidentally. Remote cases stay discoverable and raise clear errors, but nothing
  downloads, caches, or unpacks. See
  [Manifests and storage](manifests-and-storage.md) for why, and the gate that would
  reopen it.

---

## Architecture overview

The core data flow is:

```
case.yaml → Pydantic model → registry → selectors/suites → case object → load() → pytest
```

The package is organized into layers:

| Layer | Packages | Responsibility |
|---|---|---|
| **Metadata** | `catalog/models.py`, `catalog/loader.py` | Define and parse case/suite metadata |
| **Catalog** | `catalog/registry.py`, `catalog/selectors.py`, `catalog/suites.py` | Discover, filter, and group cases |
| **Runtime** | `cases/base.py`, `cases/factory.py`, `cases/vector.py`, `cases/raster.py`, `cases/netcdf.py` | Turn metadata into loadable objects |
| **Loaders** | `loaders/*` | Format-specific file reading |
| **Assertions** | `assertions/*` | Reusable geospatial test helpers |
| **Storage** | `storage/*` | SHA-256 integrity checking (transport deferred to v1.1) |
| **Plugin** | `pytest_plugin/*` | pytest fixtures and markers |
| **Public API** | `api/*` | The `import geocase` compatibility surface |

---

## Implementation sequence

Work proceeds in waves. Each wave adds one coherent slice of functionality and its tests before moving to the next.

### Wave 1 — Metadata layer ✅ (45 tests)

**Goal:** A `case.yaml` loads cleanly into a typed Python object.

- [x] `catalog/models.py` — Pydantic v2 models for `CaseMetadata`, `SuiteMetadata`, and supporting types
- [x] `catalog/loader.py` — `load_case_metadata()`, `load_suite_metadata()`, `load_case_index()`, `load_suite_index()`
- [x] All `case.yaml` files populated with real metadata
- [x] Suite YAML files created in `catalog/suites/`
- [x] Unit tests: `test_case_models.py` (27), `test_loader.py` (18)

### Wave 2 — Catalog layer ✅ (55 tests)

**Goal:** `get_case("dateline_crossing_polygon")` and `select_cases(category="vector")` work.

- [x] `catalog/registry.py` — load full catalog from `case-index.yaml`, in-memory lookup
- [x] `catalog/selectors.py` — filter cases by category, tier, tags, format, etc.
- [x] `catalog/suites.py` — resolve named suites into case lists
- [x] `catalog/__init__.py` — full public API exports
- [x] Unit tests: `test_registry.py` (16), `test_selectors.py` (21), `test_suites.py` (18)

### Wave 3 — Runtime layer ✅ (49 tests)

**Goal:** `case.load()` returns actual geospatial data.

- [x] Real test data created: 4 GeoJSON, 2 GeoTIFF, 1 NetCDF, 1 GPKG
- [x] `cases/base.py` — `BaseCase` with metadata, root dir, `primary_path`
- [x] `cases/vector.py` — `VectorCase.load()` via GeoPandas
- [x] `cases/raster.py` — `RasterCase.open()` context manager via Rasterio, `.read(band)`
- [x] `cases/netcdf.py` — `NetCDFCase.load()` via xarray
- [x] `cases/factory.py` — dispatch metadata → case subclass
- [x] `cases/__init__.py` — exports
- [x] Unit tests: `test_cases.py` (49)

### Wave 4 — Assertions ✅ (55 tests)

**Goal:** Provide reusable test helpers beyond just loading.

- [x] `assertions/geometry.py` — `assert_valid_geometry`, `assert_invalid_geometry`, `assert_geometry_type`, `assert_has_holes`, `assert_no_holes`, `assert_feature_count`
- [x] `assertions/crs.py` — `assert_has_crs`, `assert_epsg`, `assert_crs_units` (works with both GeoDataFrames and rasterio datasets)
- [x] `assertions/raster.py` — `assert_band_count`, `assert_nodata_value`, `assert_dtype`, `assert_shape`, `assert_nodata_masked`, `assert_no_nodata_pixels`
- [x] `assertions/topology.py` — `assert_no_self_intersections`, `assert_no_duplicates`, `assert_no_null_geometries`
- [x] `assertions/metadata.py` — `assert_case_loadable`, `assert_matches_vector_hints`, `assert_matches_raster_hints`
- [x] `assertions/__init__.py` — exports all 18 public assertion functions
- [x] Unit tests: `test_assertions.py` (55)

### Wave 5 — Plugin & integration ✅ / polishing continues

**Goal:** First-class pytest experience.

- [x] `pytest_plugin/fixtures.py` — `geocase_registry`, `geocase_case`, `geocase_cases` fixtures and marker resolution
- [x] `pytest_plugin/markers.py` — custom marker registration (`geocase_case`, `geocase_suite`, `geocase_select`)
- [x] Plugin entrypoint + auto-parametrize hook in `pytest_plugin/__init__.py`
- [x] End-to-end plugin-driven examples in `examples/`
- [ ] Add dedicated plugin unit/integration tests for error paths and edge behavior

### Wave 6 — Validation, storage, docs, release polish

**Goal:** Make the pytest-first package reliable, documented, and releasable.

- [ ] `catalog/validators.py`, `catalog/manifests.py`
- [ ] `storage/local.py`, `remote.py`, `cache.py`, `hashing.py`
- [ ] `docs/getting-started.md`, `docs/adding-a-case.md`
- [ ] Add release workflow for packaging and PyPI publishing
- [ ] `api/public.py`, `api/types.py`

### Wave 7 — Optional maintainer tooling

**Goal:** Add non-essential tooling for catalog inspection and maintenance outside `pytest`.

- [ ] `cli/main.py`, `list_cases.py`, `show_case.py`, `fetch_case.py`, `validate_catalog.py`

---

## First milestone

The minimum working product is when all of these succeed:

1. ~~One case loads from YAML into a Pydantic model~~ ✅
2. ~~Registry discovers all cases from `case-index.yaml`~~ ✅
3. ~~`get_case("simple_valid_polygon")` returns a case object~~ ✅
4. ~~`select_cases(category="vector", test_tier="unit")` returns matching cases~~ ✅
5. ~~`suite("core-vector")` resolves to its case list~~ ✅
6. ~~`VectorCase.load()` returns a GeoDataFrame~~ ✅
7. ~~One parameterized pytest example works end-to-end~~ ✅
8. Dedicated plugin tests cover key error paths and edge behavior
9. Starter docs explain install, selection, and authoring workflows

CLI support is optional for this milestone.

---

## Development workflow

### Branch strategy

Work happens on feature branches off `main`. The current branch changes over time; use a focused branch per milestone or stabilization task.

### How to add code

Follow the pytest-first priority order. For each module or doc area:

1. Implement the module
2. Add tests for that module
3. Verify manually
4. Move to the next module

Keep prompts small and focused — one module at a time produces better results than asking for everything at once.

Recommended order from the current state:

1. Harden the plugin and case-driven examples
2. Add validation and manifest support
3. Complete storage/remote support needed by packaged or remote cases
4. Finish onboarding docs
5. Add release automation and publishing workflow
6. Add a public API layer if users need a smaller supported surface
7. Add CLI tooling only if maintainer workflows need it

### Running tests

```bash
# all tests
pytest

# unit tests only
pytest tests/unit/

# specific file
pytest tests/unit/test_case_models.py
```

### CI job segmentation

CI runs on GitHub Actions. `.github/workflows/ci.yml` fires on push and pull
request and defines five jobs:

- `tests` — the suite on a Python 3.11/3.14 matrix
- `lint` — `ruff format --check` and `ruff check` over `src` and `tests`
- `typecheck` — `mypy src`
- `docs` — `mkdocs build --strict`
- `catalog` — catalog integrity: `scripts/build_case_index.py --check`,
  `scripts/validate_catalog.py`, the fixture and checksum generators, and the
  generated-page and coverage-matrix drift gates

`.github/workflows/release.yml` handles tagged builds and publishing; see
[Releasing](releasing.md).

### Building docs

```bash
mkdocs serve
```

---

## Key design decisions

| Decision | Rationale |
|---|---|
| Pydantic v2 for models | Strict validation, good error messages, fast |
| YAML for metadata | Human-readable, diff-friendly, familiar to geo community |
| Hatch for build | Modern, minimal config, supports src layout |
| Optional dependencies | Users install only what they need (`vector`, `raster`, `netcdf`) |
| Bundled tiny data | Core cases ship with the package — no network needed for CI |
| Separate loaders from cases | Cases stay small; loader code is reusable and testable |
| Literal types for enums | Enforced at validation time without extra enum classes |

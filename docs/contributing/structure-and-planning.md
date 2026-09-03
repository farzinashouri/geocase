# Structure and Planning

> **Status (August 2026):** Core implementation is complete; `pytest tests -q` is green at
> 780 passed, 1 skipped, and the public API is pinned for v1.0.
> See [workflow.md](workflow.md) for the detailed status tracker and
> [development-plan.md](https://github.com/farzinashouri/geocase/blob/main/docs/plans/development-plan.md) for the roadmap, which is authoritative on
> scope.

The core implementation is complete:

1. ~~implement the **metadata models**~~ ✅
2. ~~implement the **YAML loaders**~~ ✅
3. ~~implement the **registry**~~ ✅
4. ~~implement **selectors**~~ ✅
5. ~~implement **suites**~~ ✅
6. ~~implement **case factory + loaders**~~ ✅
7. ~~add a few **tests**~~ ✅ (781 collected)
8. ~~wire the **pytest plugin**~~ ✅

Remaining work focuses on documentation cleanup, additional test cases, and polish.
See [`development-plan.md`](https://github.com/farzinashouri/geocase/blob/main/docs/plans/development-plan.md) for the current roadmap.

---

# 1. What the project is becoming

GeoCase is now basically this:

* a **catalog of cases**
* each case has **metadata**
* metadata is loaded into Python objects
* those objects can be **filtered** and **grouped into suites**
* selected cases are then used in `pytest.mark.parametrize(...)`

So the core flow is:

`case.yaml -> Pydantic model -> registry -> selectors/suites -> case object -> load() -> pytest`

That is the mental model to keep in mind while coding.

---

# 2. Folder structure explained briefly

Below is the meaning of the main folders and why they exist.

## Root files

### `README.md`

Project entry point. Explains what GeoCase is, why it exists, and shows a minimal example.

### `pyproject.toml`

Package configuration. Declares dependencies, optional extras, build system, pytest plugin entry point, linting config, etc.

### `LICENSE`

Open-source license.

### `.gitignore`

Prevents committing generated files, caches, virtualenvs, downloads, and temp artifacts.

### `mkdocs.yml`

Documentation site configuration if you publish docs with MkDocs.

---

## `docs/`

Human documentation.

### [`docs/index.md`](../index.md)

Landing page for docs.

### [`docs/getting-started.md`](../getting-started.md)

Basic install and first use.

### [`docs/philosophy.md`](../philosophy.md)

Explains the design principles: cases over random files, metadata-driven parameterization, small bundled core, remote later.

### [`docs/using-parameterized-tests.md`](../using-parameterized-tests.md)

Shows the main developer workflow with pytest.

### [`docs/adding-a-case.md`](../adding-a-case.md)

Instructions for contributors to add new cases correctly.

### [`docs/remote-datasets.md`](../remote-datasets.md)

Explains bundled vs remote vs private storage.

### [`docs/design/database-design.md`](../design/database-design.md)

Explains the longer-term catalog backend idea.

Why this folder exists: because GeoCase is partly a toolkit and partly a convention. Good docs are part of the product.

---

## `src/geocase/`

Main Python package.

### `__init__.py`

Public API surface. Re-export the small number of things users should import directly, like:

* `get_case`
* `list_cases`
* `select_cases`
* `suite`

### `py.typed`

Tells type checkers that the package is typed.

---

## `src/geocase/api/`

Optional but useful if you want a clean public-facing layer.

### `api/public.py`

Thin stable wrapper around internal modules. This is where you define the functions you want users to call.

### `api/types.py`

Shared public-facing type aliases or protocols if you want to keep internals separate.

Why this folder exists: to stop users from importing deep internal modules directly.

For v0.1 this folder is optional, but it is a clean design choice.

---

## `src/geocase/catalog/`

This is the real core.

### `catalog/models.py` ✅

Defines Pydantic v2 models:

* `CaseMetadata` — full case description with strict validation
* `SuiteMetadata` — suite definition with selection criteria
* `SuiteSelection` — filter fields using Literal types (`Category`, `TestTier`, etc.)
* `FileMap`, `RemoteInfo`, `SourceInfo`, `AssertionHints` — supporting models

Type aliases (`Category`, `FormatType`, `TestTier`, `SizeClass`, `StorageClass`, `LoaderHint`, `Status`) are defined as `Literal` types and reused throughout.

Why it exists: all metadata needs one clear runtime representation.

### `catalog/loader.py` ✅

Reads YAML files and converts them into Pydantic models.

Implemented functions:

* `load_case_metadata(path) -> CaseMetadata`
* `load_suite_metadata(path) -> SuiteMetadata`
* `load_case_index(path) -> list[str]`
* `load_suite_index(path) -> list[str]`

Why it exists: separates file parsing from the rest of the logic.

### `catalog/registry.py`

Loads the full catalog from `case-index.yaml`, stores it in memory, and provides lookup functions.

Why it exists: this is the single source of truth for available cases.

### `catalog/selectors.py`

Filters cases by metadata, such as:

* category
* tag
* risk type
* test tier
* format
* storage class

Why it exists: selectors are what make parameterized testing elegant.

### `catalog/suites.py`

Loads suite definitions and resolves them into case lists.

Why it exists: named suites are more convenient than repeating selectors everywhere.

### `scripts/validate_catalog.py`

Extra validation logic beyond Pydantic, such as:

* referenced files exist
* remote info is present for remote cases
* duplicate case IDs do not exist
* suite references are valid
* declared `size_class` matches the payload's actual size

Why it exists: schema validation alone is not enough.

This lives in `scripts/`, not in the package. `catalog/validators.py` was reserved for it
and stayed a one-line docstring that nothing imported, so it was deleted in Batch 3;
plan 03 had already decided validation stays in `scripts/`.

### `catalog/manifests.py`

Handles remote manifest files for downloadable extended datasets.

Why it exists: keeps remote logic separate from core bundled metadata.

See also: [`manifests-and-storage.md`](manifests-and-storage.md) for the
distinction between manifest support, storage support, checksums, and why both
layers are needed.

---

## `src/geocase/cases/`

Case objects and category-specific behavior.

### `cases/base.py`

Defines the common base class, e.g. `BaseCase`.

Why it exists: every case shares metadata, root path, `id`, and file resolution logic.

### `cases/vector.py`

Defines `VectorCase` and `load()` using GeoPandas.

### `cases/raster.py`

Defines `RasterCase` and `open()` using Rasterio.

### `cases/netcdf.py`

Defines `NetCDFCase` and `load()` using Xarray.

### `cases/factory.py`

Takes metadata and returns the right case class.

Why it exists: users should not have to care which subclass to instantiate.

---

## `src/geocase/loaders/`

Actual file loading utilities.

### `loaders/geopandas_loader.py`

Reads vector files.

### `loaders/rasterio_loader.py`

Opens raster files.

### `loaders/xarray_loader.py`

Opens NetCDF-like cases.

### `loaders/generic.py`

Fallback logic for generic files or untyped loading.

Why this folder exists: keeps case objects small and prevents loader code from being duplicated.

For v0.1, you can inline loading inside `cases/` and move it here later. But long-term this separation is cleaner.

---

## `src/geocase/assertions/`

Reusable test helpers.

### `assertions/geometry.py`

Examples:

* `assert_not_empty_geodataframe`
* `assert_all_geometries_valid`
* `assert_geometry_types`

### `assertions/crs.py`

Examples:

* `assert_has_crs`
* `assert_epsg`

### `assertions/raster.py`

Examples:

* `assert_raster_has_crs`
* `assert_raster_has_nodata`

### `assertions/topology.py`

Topology-specific checks later.

### `assertions/metadata.py`

Checks on case metadata or expected properties.

Why this folder exists: GeoCase should provide not only data, but also reusable testing primitives.

---

## `src/geocase/storage/`

### `storage/hashing.py` ✅

SHA-256 and byte-size verification. `scripts/generate_checksums.py` imports
`sha256_file` from here, so bundled fixtures and remote artifacts are hashed by the
same code.

Why it exists: local and remote cases should still feel like one catalog.

**Transport is deferred to v1.1.** `local.py`, `remote.py`, and `cache.py` previously
existed here as one-line docstring stubs and were deleted — an empty module implies a
commitment the project has not made, and both extended manifests are still 100%
placeholder (`sha256: "replace_me"`, `base_uri: example.org`). They return in v1.1,
gated on at least one real published archive with a real checksum. See
[`development-plan.md`](https://github.com/farzinashouri/geocase/blob/main/docs/plans/development-plan.md).

---

## `src/geocase/pytest_plugin/`

Pytest integration.

### `fixtures.py`

Provides fixtures like:

* `geocase_registry`
* `geocase`

### `markers.py`

Custom pytest markers later, such as:

* `@pytest.mark.geocase_remote`
* `@pytest.mark.geocase_slow`

Why it exists: GeoCase is designed for pytest, so first-class integration matters.

---

## `src/geocase/cli/` — removed

There is no CLI. The directory held five one-line docstring stubs while
`pyproject.toml` declared `geocase = "geocase.cli.main:app"`, so every install got a
console script that died with `ImportError`. Both the entry point and the stubs were
removed for v1.0; a CLI is deferred to v1.1 and would be re-added only if maintainer
workflows need one. Catalog inspection and validation run through
`scripts/validate_catalog.py` in the meantime.

---

## `src/geocase/metadata/`

Static metadata indexes and schemas.

### `metadata/case-index.yaml` ✅

Master list of case metadata file paths (currently 8 cases).

Why it exists: gives one deterministic place to discover all cases.

### `metadata/suite-index.yaml` ✅

Master list of suite definition file paths (currently 7 suites: `core-vector`, `crs-edge-cases`, `raster-nodata`,
`vector-topology`, `vector-crs-edge`, `vector-schema-encoding`,
`georeferencing-conventions`).

Why it exists: same idea, but for suites.

### `metadata/schemas/case.schema.yaml`

Human-readable schema contract for case metadata.

### `metadata/schemas/suite.schema.yaml`

Human-readable schema contract for suites.

### `metadata/schemas/manifest.schema.yaml`

Contract for remote dataset manifests.

Why it exists: keeps structure explicit and reviewable.

---

## `src/geocase/data/core/` ✅

Bundled sample data. All 8 `case.yaml` files are populated with full metadata.

The catalog is **163 cases**. The lists that were once here enumerated eight of them and
went stale within one release; the enumeration is now generated from the registry and
CI-gated instead. See the [dataset catalog](../dataset-catalog.md) for the reasoning and
the [case catalog](../_generated/catalog/index.md) for the full list.

### `data/core/vector/` (103 cases)

A 66-case geometry × format baseline (6 geometry types across the formats that support
them), 36 `special/` edge cases in eight families — `crs`, `dateline`, `invalid`,
`encoding`, `precision`, `empty`, `degenerate`, `holes` — and one GeometryCollection.

### `data/core/raster/` (30 cases)

GeoTIFFs in four groups: product families (17), the dtype family (5), the
nodata/alignment/CRS family (3), and footprint edge cases (5).

Rotated and skewed affine transforms are **not** covered. `affine_transform_quirk` was an
empty stub claiming that coverage and was deleted in Batch 3; the gap is on the v1.1 list,
and `validate_catalog.py` now fails on any unindexed `*.yaml` under `data/core`.

### `data/core/netcdf/` (1 case)

* `latlon_small` — CF-compliant lat/lon NetCDF

Each case folder contains:

* `case.yaml`
* main file like `.geojson`, `.gpkg`, `.tif`, `.nc`
* optional `notes.md`
* optional preview

Why it exists: every case should be self-contained.

---

## `src/geocase/templates/` ✅

Starter templates for contributors.

### `templates/new_case.yaml` ✅

Fully commented template with all fields, inline guidance, and sensible defaults. Copy into a new case directory and fill in.

### `templates/notes.md`

Template notes file.

Why it exists: reduces drift and makes contributions consistent.

---

## `tests/`

Your own test suite for GeoCase itself.

### `tests/unit/`

Fast tests for models, loaders, selectors, suites, assertions.

### `tests/integration/`

Broader tests that exercise actual case loading across several cases.

### `tests/fixtures/`

Shared test data for GeoCase’s own internal tests.

Why it exists: GeoCase should test its own testing toolkit.

---

## `examples/`

Small realistic examples for users.

Why it exists: examples are often more useful than long prose docs.

---

## `scripts/`

Maintenance scripts.

### `build_case_index.py`

Rebuilds `case-index.yaml`.

### `validate_catalog.py`

Validates all cases and indexes.

### `package_extended_cases.py`

Packages remote/extended datasets.

### `generate_checksums.py`

Creates SHA256 hashes.

Why it exists: separates contributor tooling from package runtime code.

---

## `extended-manifests/`

Remote catalog metadata.

Why it exists: lets you describe large downloadable cases without shipping them inside the package.

---

# 3. What to code next, in order

This is the order I would follow in VS Code.

## Step 1 — make `catalog/models.py` work ✅

This is your foundation.

Implemented:

* `CaseMetadata` with strict `id` validation
* `SuiteMetadata` with `SuiteSelection` using Literal types
* Helper models: `FileMap`, `SourceInfo`, `RemoteInfo`, `AssertionHints`
* Type aliases: `Category`, `FormatType`, `TestTier`, `SizeClass`, `StorageClass`, `LoaderHint`, `Status`

Goal: a `case.yaml` should load cleanly into `CaseMetadata`. ✅

---

## Step 2 — add `catalog/loader.py` ✅

This module does one job well:

* read YAML
* instantiate model
* return typed object

Implemented:

```python
load_case_metadata(path) -> CaseMetadata
load_suite_metadata(path) -> SuiteMetadata
load_case_index(path) -> list[str]
load_suite_index(path) -> list[str]
```

Goal: make metadata loading deterministic and simple. ✅

---

## Step 3 — implement `catalog/registry.py` ⬅️ NEXT

This reads `case-index.yaml`, loads all cases, and keeps them in memory.

Functions/methods you want:

* `get_registry()`
* `list_cases()`
* `get_case_record(case_id)`
* maybe `filter(...)`

The registry should probably store records like:

* metadata
* case root directory
* resolved primary path

Goal: be able to say `get_case("dateline_crossing_polygon")`.

---

## Step 4 — implement `catalog/selectors.py`

This is very important because this is where your main value appears.

Functions to add:

* `select_cases(...)`
* maybe `select_case_ids(...)`

Typical filters:

* `category`
* `test_tier`
* `tag`
* `risk_type`
* `format_type`
* `storage_class`

Goal: make metadata-driven parameterization work.

Example target usage:

```python
select_cases(category="vector", test_tier="unit")
```

---

## Step 5 — implement `catalog/suites.py`

Load suite YAML and resolve it to actual case objects.

Functions to add:

* `list_suites()`
* `load_suite_definition(name)`
* `suite(name)`

Goal: let users write:

```python
@pytest.mark.parametrize("case", suite("core-vector"), ids=lambda c: c.id)
```

---

## Step 6 — implement `cases/base.py` and `cases/factory.py`

`BaseCase` should hold:

* metadata
* root dir
* `primary_path`

Factory should:

* inspect metadata category
* return `VectorCase`, `RasterCase`, or `NetCDFCase`

Goal: convert catalog metadata into real usable objects.

---

## Step 7 — implement category-specific case classes

You want at least:

* `VectorCase.load()`
* `RasterCase.open()`
* `NetCDFCase.load()`

At first keep them minimal.

Goal: a case object should actually open its data.

---

## Step 8 — add a few assertions

Start with a tiny set.

For vector:

* has CRS
* not empty
* geometry types

For raster:

* has CRS
* has nodata

Goal: make GeoCase more than a file catalog.

---

## Step 9 — add tests for GeoCase itself

Do not postpone this too much.

Start with:

* `test_registry_loads_cases`
* `test_get_case`
* `test_select_cases_by_category`
* `test_suite_resolves_cases`

Then loader tests.

Goal: lock in the architecture before it grows.

---

## Step 10 — add `pytest_plugin/fixtures.py`

Fixtures:

* `geocase_registry`
* `geocase`

Goal: give users a clean pytest experience.

---

# 4. A practical implementation sequence per file

This is the simplest coding order.

## First wave ✅ (models + loader done, registry is next)

* ~~`catalog/models.py`~~ ✅
* ~~`catalog/loader.py`~~ ✅
* `catalog/registry.py` ⬅️ next

## Second wave

* `cases/base.py`
* `cases/vector.py`
* `cases/raster.py`
* `cases/netcdf.py`
* `cases/factory.py`

## Third wave

* `catalog/selectors.py`
* `catalog/suites.py`

## Fourth wave

* `assertions/geometry.py`
* `assertions/crs.py`
* `assertions/raster.py`

## Fifth wave

* `pytest_plugin/fixtures.py`
* tests
* examples

That order minimizes confusion.

---

# 5. What each major file should roughly contain

Here is the brief coding intent for the most important files.

## `catalog/models.py` ✅

Contains only data models and type constraints.
No file I/O.
No registry logic.
No GeoPandas/Rasterio code.

## `catalog/loader.py` ✅

Contains YAML-reading functions.
No selection logic.
No pytest logic.

## `catalog/registry.py`

Contains in-memory catalog assembly and lookup logic.
No file-format loading.

## `catalog/selectors.py`

Contains filtering logic over registry results.

## `catalog/suites.py`

Contains named suite resolution logic.

## `cases/base.py`

Contains common case behavior and file path helpers.

## `cases/vector.py`, `raster.py`, `netcdf.py`

Contain data-format-specific loading.

## `cases/factory.py`

Contains the mapping from metadata category to case class.

## `assertions/*`

Contain reusable test helpers only.

## `pytest_plugin/fixtures.py`

Contains pytest fixtures, not business logic.

That separation will save you a lot of refactoring later.

---

# 6. How to work with the VS Code LLM effectively

Since you want to continue in an integrated LLM, the best approach is **small, specific prompts**, not one giant request.

A good pattern is:

1. ask it to implement one module
2. ask it to add tests for that module
3. review manually
4. move to next module

Good prompt style:

> Implement `src/geocase/catalog/models.py` for GeoCase.
> Use Pydantic v2.
> Add models for case metadata and suite metadata based on the existing YAML schemas in `src/geocase/metadata/schemas/`.
> Keep the file focused on models only.
> Include strict validation for case ID, enums for category/test tier/storage class, and default factories for list/dict fields.

Then:

> Now implement `src/geocase/catalog/loader.py`.
> Add `load_case_metadata(path: Path) -> CaseMetadata` and `load_suite_metadata(path: Path) -> SuiteMetadata`.
> Use `yaml.safe_load`.
> Keep the module small and typed.

Then:

> Add unit tests for `catalog/models.py` and `catalog/loader.py` using pytest.
> Include valid and invalid case metadata examples.

That workflow usually works much better than asking for the whole repo at once.

---

# 7. The minimum working milestone

Before doing remote manifests, CLI, or fancy assertions, aim for this milestone:

* one case can be loaded from YAML
* registry discovers all cases from `case-index.yaml`
* `get_case("simple_valid_polygon")` works
* `select_cases(category="vector", test_tier="unit")` works
* `suite("core-vector")` works
* vector case `.load()` works
* one example pytest parameterization works

That is the first real “product moment”.

---

# 8. What not to overbuild yet

At this stage, I would avoid spending much time on:

* hosted catalog API
* database backend
* advanced CLI
* plugin system for private registries
* too many assertion types
* automatic remote download logic
* too many file formats

Keep the center strong first:
**metadata -> registry -> selection -> case loading -> pytest**

---

# 9. A clean mental map of the architecture

You can think of the package like this:

## Metadata layer

Defines what exists.

Files:

* `case.yaml`
* `suite.yaml`
* `case-index.yaml`
* `suite-index.yaml`

Python:

* `catalog/models.py`
* `catalog/loader.py`

## Catalog layer

Finds and filters cases.

Python:

* `catalog/registry.py`
* `catalog/selectors.py`
* `catalog/suites.py`

## Runtime layer

Turns metadata into loadable objects.

Python:

* `cases/base.py`
* `cases/factory.py`
* `cases/vector.py`
* `cases/raster.py`
* `cases/netcdf.py`

## Testing helper layer

Improves test ergonomics.

Python:

* `assertions/*`
* `pytest_plugin/fixtures.py`

## Storage layer

Resolves where files live.

Python:

* `storage/*`

This is the cleanest way to reason about the repo.

---

# 10. Your next practical move in VS Code

**Wave 1 (metadata layer) is complete.** Models and loader are implemented, all case.yaml files are populated, suite definitions exist, and config files are restored.

The next target is **Wave 2 — the catalog layer**:

```text
Implement the catalog layer for GeoCase.

Scope:
1. src/geocase/catalog/registry.py
2. src/geocase/catalog/selectors.py
3. src/geocase/catalog/suites.py

Requirements:
- registry.py: read case-index.yaml, load all CaseMetadata, store in memory
  - get_registry() -> Registry
  - list_cases() -> list of case records
  - get_case_record(case_id) -> single record or KeyError
- selectors.py: filter cases by category, test_tier, tags, format, storage_class, etc.
  - select_cases(...) -> list of case records
- suites.py: load suite YAML, apply its SuiteSelection to the registry
  - list_suites() -> list of suite keys
  - suite(name) -> list of case records
- Add pytest unit tests for each module
- Keep concerns separated across the three files
```

After that, the prompt should target **Wave 3 — the runtime layer**:

```text
Implement the runtime case layer for GeoCase.

Scope:
1. src/geocase/cases/base.py
2. src/geocase/cases/vector.py
3. src/geocase/cases/raster.py
4. src/geocase/cases/netcdf.py
5. src/geocase/cases/factory.py

Requirements:
- BaseCase should expose metadata, id, root_dir, and primary_path
- VectorCase.load() should use geopandas
- RasterCase.open() should use rasterio
- NetCDFCase.load() should use xarray
- factory.get_case(case_id) should resolve metadata from the registry and return the correct case subclass
- include helpful ImportError messages for missing optional dependencies
- add tests where practical
```

That will move you forward cleanly.

---

# 11. Final summary

The skeleton is built and the **metadata layer is complete**.
Now the important part is to make the **catalog layer** real.

Completed:

1. ~~`catalog/models.py`~~ ✅
2. ~~`catalog/loader.py`~~ ✅
3. ~~All `case.yaml` files~~ ✅
4. ~~Suite definitions~~ ✅
5. ~~Config files (`pyproject.toml`, `.gitignore`, `LICENSE`, `mkdocs.yml`)~~ ✅
6. ~~`templates/new_case.yaml`~~ ✅

Next coding priorities:

1. `catalog/registry.py`
2. `catalog/selectors.py`
3. `catalog/suites.py`
4. `cases/*`
5. tests
6. pytest fixtures

And the reason each folder exists is simple:

* `docs/` explains the system
* `metadata/` defines the catalog contract
* `catalog/` discovers and filters cases
* `cases/` loads actual data
* `assertions/` provides reusable test helpers
* `pytest_plugin/` makes GeoCase natural in pytest
* `storage/` handles local/remote artifacts
* `data/core/` contains bundled, self-contained sample cases
* `tests/` ensures GeoCase itself behaves correctly

The best next step is to implement the **first working metadata/catalog slice** before doing anything else.

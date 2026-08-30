---
description: "A plain-language guide to GeoCase's purpose, architecture, and contributor workflow."
---

# Repository Guide

GeoCase is a Python testing library for geospatial software. It gives developers small,
realistic geospatial datasets designed to expose subtle bugs—such as ignored NoData values,
broken polygons, CRS mistakes, antimeridian crossings, encoding problems, or raster metadata
loss.

Instead of inventing test files in every project, users select a GeoCase dataset and test their
ordinary code with `pytest`.

```text
case.yaml → typed metadata → catalog lookup/filtering → case object → file loader → pytest test
```

For example, a test can request a GeoTIFF containing NoData pixels and verify that an elevation
calculation excludes them.

## Repository architecture

| Part | Main location | What it does | Why it exists |
|---|---|---|---|
| Public API | `src/geocase/__init__.py`, `api/` | Provides the stable `import geocase` functions: list, inspect, and load cases or suites. | Keeps user-facing imports small and compatible while internals can evolve. |
| Catalog metadata | `src/geocase/metadata/`, `case.yaml` files | Defines the catalog index, schemas, and metadata for every dataset. | Each dataset needs a machine-readable explanation of what it tests and how to use it. |
| Catalog runtime | `src/geocase/catalog/` | Parses YAML, validates it with Pydantic, creates the registry, resolves suites, and filters selections. | Separates “find the right test case” from “open its files.” |
| Case objects | `src/geocase/cases/` | Turns metadata plus a case directory into `VectorCase`, `RasterCase`, or `NetCDFCase`. | Gives all data types a consistent object interface while preserving type-specific behavior. |
| File loaders | `src/geocase/loaders/` | Reads GeoPandas/vector, Rasterio/raster, and xarray/NetCDF data. | Keeps optional heavy geospatial dependencies and I/O details out of the catalog layer. |
| Pytest plugin | `src/geocase/pytest_plugin/` | Adds `geocase_case`, `geocase_suite`, and `geocase_select` markers plus fixtures. | This is the main user workflow: cases become normal pytest parameters. |
| Assertions | `src/geocase/assertions/` | Reusable checks for geometry validity, CRS, topology, raster properties, and metadata hints. | Prevents contributors and users from rewriting common GIS assertions. |
| Bundled dataset corpus | `src/geocase/data/core/` | Contains the actual small vector, raster, and NetCDF fixtures, their notes, and SHA-256 checksums. | This is the product’s core value: curated inputs that represent real failure modes. |
| Suites | `src/geocase/catalog/suites/` | Named groups such as CRS edge cases, topology cases, and raster NoData cases. | Lets users ask for a meaningful family of scenarios without listing each ID. |
| Integrity/storage | `src/geocase/storage/`, `extended-manifests/` | Hashes artifacts and describes optional external datasets. | Ensures fixture bytes do not silently drift; remote download and cache support is intentionally deferred. |
| Raster fixture builder | `src/geocase/raster/` | Creates configurable raster fixture specifications and product-like presets. | Supports generating adversarial raster inputs without forcing Rasterio on every consumer. |
| Benchmark | `src/geocase/benchmark/` | Grades coding-agent or implementation behavior against geospatial tasks. | Uses the catalog as an evaluation corpus, beyond ordinary library testing. |
| Maintainer scripts | `scripts/` | Rebuild indexes, fixtures, checksums, coverage matrices, catalog documentation, and validations. | Makes generated data and documentation reproducible and prevents catalog drift. |
| Tests | `tests/` | Unit, integration, raster, and benchmark tests. | Protects the stable API and verifies fixtures, metadata, plugins, and generators. |
| Documentation | `docs/` | User guides, contributor workflow, reference material, roadmap, and generated catalog pages. | Explains how to consume GeoCase and how to safely maintain it. |
| Automation/configuration | `pyproject.toml`, `.github/workflows/`, `mkdocs.yml`, `environment.yml` | Packaging, dependencies, CI, documentation-site configuration, and the GDAL-capable contributor environment. | Defines how the project is installed, checked, released, and documented. |

## Guide for the next developer

### 1. Start with the public contract

The supported v1 surface is the top-level `geocase` API and the pytest workflow. Prefer
importing from `geocase`, not internal modules. The API’s deliberate split is:

- `list_cases()` and `get_case()` return cheap metadata.
- `load_case()` returns a runtime object that can open data.

### 2. Understand the case lifecycle

Each bundled case is a folder containing:

```text
case-folder/
├── case.yaml          # identity, purpose, format, assertions, paths
├── primary-data-file  # GeoJSON, GeoTIFF, GPKG, NetCDF, and similar
├── notes.md           # human explanation
└── checksums.sha256   # integrity record
```

The case must also appear in `src/geocase/metadata/case-index.yaml`, otherwise the registry will
not discover it.

### 3. Add datasets metadata-first

Follow [Adding a Case](../adding-a-case.md). Choose the scenario first, add a minimal
reproducible file, write a clear `case.yaml`, then add tests and regenerate derived artifacts.
Do not add generic sample data; every case should represent a named behavior or failure risk.

### 4. Change the correct layer

| If you need to… | Change here |
|---|---|
| Add a field or validation rule to case metadata | `catalog/models.py`, schemas, loaders, and tests |
| Change case discovery or filtering | `catalog/registry.py`, `selectors.py`, and `suites.py` |
| Support a new data category | `cases/`, factory dispatch, loader, metadata literals, and tests |
| Support another representation of an existing type | Usually `cases/vector.py` or `loaders/` |
| Improve pytest usage | `pytest_plugin/` and plugin tests |
| Add a reusable test check | `assertions/` |
| Generate or verify corpus files | The relevant command in `scripts/` |
| Change stable consumer behavior | `api/public.py`, `__init__.py`, and public-API tests |

### 5. Use the right development environment

`environment.yml` is the fuller contributor environment and includes GDAL tooling required for
fixture generation and some examples. `pip install -e ".[dev]"` is the closer CI-style
development install.

```bash
pip install -e ".[dev]"
python -m pytest tests -q
```

### 6. Run the relevant guards after changes

```bash
python scripts/build_case_index.py --check
python scripts/validate_catalog.py
python scripts/generate_checksums.py --check
python -m pytest tests -q
ruff format --check src tests
ruff check src tests
mypy src
```

For corpus or generated-document changes, also run the relevant fixture, coverage-matrix, or
catalog-page generator. CI enforces these freshness checks.

### 7. Respect intentional boundaries

- There is no general GeoCase CLI in v1; the benchmark has its own module CLI.
- Remote cases can be declared through manifests but are not downloaded yet.
- Optional geospatial libraries are imported lazily so metadata discovery works without
  GeoPandas, Rasterio, or xarray.
- `catalog/roots.py` intentionally is not re-exported from `geocase.catalog`, because doing so
  creates a circular import.

## Maintenance note

Parts of the contributor documentation contain historical test counts and implementation-wave
status that no longer match the newer package structure. Treat the code, CI workflow, and current
tests as the source of truth, and update those historical statements when touching adjacent
documentation.

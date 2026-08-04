# Changelog

All notable changes to GeoCase are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-08-02

First stable release, and the first release published to PyPI. Version `0.1.0` was never
uploaded.

### The compatibility promise

v1.0 makes a stability commitment on **two surfaces only**:

1. **The pytest workflow** — the `geocase_case` / `geocase` fixtures and the
   `geocase_case`, `geocase_suite`, and `geocase_select` markers.
2. **The public API** — the 27 names exported from `import geocase`, pinned against a
   literal in `tests/unit/test_public_api.py`.

Everything else — module layout, internal helpers, the shape of `geocase.catalog` — is
internal and may change in a minor release. The promise is deliberately narrow because
those two surfaces are the genuinely mature ones; a wider claim would make the 1.0 label
dishonest.

### Breaking changes

- **The command-line interface and its `[project.scripts]` entry point have been
  removed.** The declared `geocase` console script was broken in every install — it
  pointed at a module that raised `ImportError` — so no working usage can depend on it.
  There is no CLI in v1.0. Use the Python API or the pytest plugin.

### Added

- **Public API** (`import geocase`): a pinned 27-name surface covering case discovery,
  loading, and inspection — `list_cases`, `get_case`, `load_case`, `show_case`,
  `list_suites`, `get_suite`, `__version__`, the case classes, the metadata models and
  enums, and `RemoteCaseUnavailableError`.
- **`docs/dataset-catalog.md`**: what the catalog contains, why each format was chosen,
  the geodetic rationale for every coordinate cluster, and an honest list of coverage
  gaps.
- **Generated catalog pages** under `docs/_generated/catalog/`: an index plus one page
  per case, per risk type, and per format, carrying `schema.org/Dataset` JSON-LD.
- **Manifest support**: `extended-manifests/*.yaml` parse and resolve, remote case ids are
  discoverable through the registry and `show_case`, and `GEOCASE_MANIFESTS` selects which
  manifests are loaded.
- **CI quality gates**: `ruff check` and `ruff format --check`, `mypy`, a Python
  3.11/3.14 test matrix, and non-blocking coverage reporting.
- **Catalog integrity gates**: orphaned case metadata, manifest validity (shadowed ids,
  cross-manifest duplicates, malformed digests, dangling `bundled_analog` references),
  `size_class` versus real on-disk payload, generated-page drift, and case ids named in
  hand-written docs.

### Changed

- **Bundled data shrank from 36 MB to 4.2 MB.** Five SpatiaLite fixtures declared
  `size_class: tiny` were 6.7 MB each; `size_class` now has enforced byte thresholds.
- `cases/raster.py` loads through `loaders/rasterio_loader.py`, making it the single
  raster load path.
- `requires-python` is `>=3.11`, with classifiers for 3.11 through 3.14 — the versions
  actually tested rather than the ones plausibly supported.
- Development status classifier: `3 - Alpha` → `5 - Production/Stable`.
- `project.urls` now point at GitLab, where the project actually lives.
- The case schema's `format` enum went from 7 values to 17, and its `assertions` block
  from 6 documented fields to all 16. Both are now pinned to the models by a test.

### Fixed

- The raster coverage matrix reported 25 of 30 cases: the generator's glob missed the five
  `footprint_edge_cases` files. Because the artifact was gated by `git diff --exit-code`,
  CI was actively enforcing the wrong number.
- Case pages linked risk hubs at `../../risk/`, one level too high, producing 187 broken
  links. `mkdocs build --strict` now passes.
- `materialize_case` raised an internal `No case root found` for manifest cases instead of
  an actionable error; both error paths are now asserted in tests.
- The registry singleton ignored `GEOCASE_MANIFESTS` changes after first use; resolved
  manifest paths are part of the cache key.

### Removed

- The `cli/` package and its entry point (see Breaking changes).
- `catalog/validators.py` — an empty stub nothing imported.
- `raster/affine_transform_quirk/` — an empty case directory that shipped in the wheel
  while appearing in no index. The rotated/skewed-transform coverage it implied is a
  genuine gap, now tracked on the v1.1 list rather than implied by a placeholder.

### Deferred to v1.1

Stated as decisions, not omissions:

- **Remote dataset transport.** Declared remote cases are discoverable and raise clear
  errors, but nothing downloads, caches, or unpacks. Both manifests are entirely
  placeholder — every `sha256` is `replace_me`, every `base_uri` is `example.org`. The
  gate for reopening this is concrete: at least one real published archive with a real
  sha256.
- **Rotated/skewed affine transforms and non-square pixels**, and **southern-hemisphere
  UTM coverage** — see the coverage gaps in the dataset catalog.

### Known numbers

134 bundled cases (103 vector, 30 raster, 1 NetCDF) across 16 formats, 4.2 MB of bundled
data, 780 passing tests, 54% line coverage.

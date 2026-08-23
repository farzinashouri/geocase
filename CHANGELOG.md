# Changelog

All notable changes to GeoCase are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **BREAKING (data): the `<geometry>_<format>_baseline` fixtures now hold the geometry
  they always claimed to.** 53 of the 60 shipped different coordinates from the GeoJSON
  canonical named in their own `params.canonical_source_case_id`. Nothing in `src/` or
  `tests/` ever dereferenced that link, so the divergence was structurally invisible —
  and anyone who trusted the naming and diffed, say, KML against Shapefile got a
  "cross-format difference" that was purely a fixture accident. Two independent
  evaluations hit exactly that.

  **Every baseline payload changed.** If you assert baseline coordinates downstream, use
  the table below to update them. Old values are shown normalized, so a row may differ
  from your file's literal ring order or vertex start.

  | Family | Formats | Old geometry | New (canonical) geometry |
  |---|---|---|---|
  | point | CSV_WKT, GPKG, SQLite, Shapefile, WKB, WKT | `POINT (10 52)` | `POINT (12.5 55.7)` |
  | point | GML | `POINT (10.5 50.5)` | `POINT (12.5 55.7)` |
  | point | Arrow, Feather, FlatGeobuf, KML | *(already correct)* | `POINT (12.5 55.7)` |
  | linestring | GML, GPKG, KML, SQLite, Shapefile, WKB, WKT | `LINESTRING (0 0, 1 1, 2 0)` | `LINESTRING (10 50, 10.5 50.3, 11 50.1)` |
  | linestring | FlatGeobuf, GeoArrow | `LINESTRING (12 55, 12.5 55.4, 13 55.8)` | `LINESTRING (10 50, 10.5 50.3, 11 50.1)` |
  | linestring | CSV_WKT | *(already correct)* | `LINESTRING (10 50, 10.5 50.3, 11 50.1)` |
  | polygon | FlatGeobuf, GML, KML, Parquet, WKB, WKT | `POLYGON ((12 55, 12 56, 13 56, 13 55, 12 55))` | `POLYGON ((10 50, 11 50, 11 51, 10 51, 10 50))` |
  | polygon | CSV_WKT, GPKG | `POLYGON ((0 0, 0 1, 1 1, 1 0, 0 0))` | `POLYGON ((10 50, 11 50, 11 51, 10 51, 10 50))` |
  | polygon | SQLite, Shapefile | *(already correct)* | `POLYGON ((10 50, 11 50, 11 51, 10 51, 10 50))` |
  | multipoint | all but Feather | `MULTIPOINT ((0 0), (1 1), (2 2))` | `MULTIPOINT ((10 50), (10.2 50.1), (10.4 50.2))` |
  | multipoint | Feather | `MULTIPOINT ((12 55), (12.2 55.1), (12.4 55.2))` | `MULTIPOINT ((10 50), (10.2 50.1), (10.4 50.2))` |
  | multilinestring | all but Parquet | `MULTILINESTRING ((0 0, 1 1), (2 2, 3 3))` | `MULTILINESTRING ((10 50, 10.5 50.2, 11 50.1), (10.2 49.8, 10.8 49.9, 11.1 50))` |
  | multilinestring | Parquet | `MULTILINESTRING ((12 55, 12.4 55.2, 12.8 55.4), (12.1 54.8, 12.6 55, 13 55.3))` | *(as above)* |
  | multipolygon | all | `MULTIPOLYGON (((0 0, 1 0, 1 1, 0 1, 0 0)), ((2 2, 3 2, 3 3, 2 3, 2 2)))` | `MULTIPOLYGON (((10 50, 10.5 50, 10.5 50.5, 10 50.5, 10 50)), ((11 50, 11.5 50, 11.5 50.5, 11 50.5, 11 50)))` |

  Note the multilinestring row in particular: the old fixtures had **two-vertex** parts
  where the canonical has three, so no coordinate tolerance would ever have hidden the
  difference.

  The six `simple_valid_*` GeoJSON canonicals are unchanged, including
  `simple_valid_polygon.params.expected_bounds`.

- **BREAKING (data): every baseline now carries exactly `id` (int64, always `1`) and
  `name` (str, always the case id).** Previously the schemas varied case by case —
  `polygon_geopackage_baseline` had `id, name, area_sqkm` while
  `polygon_shapefile_baseline` had only `name` — so a consumer diffing two members could
  not tell which column differences were *the format* and which were fixture accident.
  Columns removed: `value`, `area_sqkm`, `length_km`, `poly_count`, `segments`, and
  `segment_co` (itself a silent, undocumented DBF 10-character truncation of
  `segment_count`). Format-idiomatic schemas remain covered, deliberately and better, by
  the `special/encoding/*` cases.

  Three formats cannot honour the schema and are documented exceptions: KML reads `name`
  back as `Name` and synthesizes ~10 columns of its own, GML injects `gml_id`, and
  WKT/WKB have no attribute slot at all (`VectorCase.load()` synthesizes `name`).

- **`point_gml_baseline` now declares `params.canonical_source_case_id`.** It carried the
  `cross_format_canonical` tag while declaring an unrelated `canonical_location: {lon,
  lat}` literal that nothing read — the entire 59-declared vs 60-tagged gap. The literal
  is removed.

- **Regenerating the KML baselines drops the hand-added `<Style>` block** that
  `polygon_kml_baseline` carried. This is intentional, not an oversight: KML styling is
  `format_limited_kml_case`'s job, and a style element inside a family whose purpose is to
  hold everything but the format constant is one more uncontrolled variable.

- **CI: the `catalog` job installs `.[raster,vector]`** rather than `.[raster]`. The
  fixture generator now needs shapely, geopandas and pyarrow.

### Added

- **`shapefile_ring_orientation`** — a new `special/encoding/` case preserving the
  pre-convergence `polygon_shapefile_baseline` bytes: the same square as
  `simple_valid_polygon` but with a **clockwise** exterior ring. The Shapefile
  specification mandates CW exteriors where RFC 7946 mandates CCW, and OGR rewrites
  orientation on write, so a GeoJSON → Shapefile round trip silently reverses it. Code
  that reads `is_ccw` to tell an exterior from a hole breaks here.

  It exists as its own case because the cross-format comparison *must* be
  winding-insensitive — the Shapefile members of any family can never match a CCW
  canonical — which makes this artifact unassertable inside a baseline family.

- **Three gates, so this class of defect cannot return silently.**
  - `scripts/validate_catalog.py` now checks that the `cross_format_canonical` tag and
    `params.canonical_source_case_id` are biconditional, that the id resolves, that the
    target is GeoJSON, that geometry types match, and that a canonical is not itself
    tagged. No geospatial dependencies, so it runs in the GDAL-only `catalog` job.
  - `tests/unit/test_cross_format_canonical.py` loads every tagged case through
    `VectorCase.load()` and asserts geometry (via `shapely.normalize`, tolerance `1e-9`),
    geometry type, CRS (via `pyproj.CRS`, since the columnar formats return PROJJSON
    rather than the string `"EPSG:4326"`), the `name` value, and the column schema. Cases
    are auto-discovered, so future baselines are gated automatically.
  - `scripts/generate_vector_fixtures.py` now generates **all 60** baselines rather than
    only the five SpatiaLite ones, deriving each geometry from its declared canonical, and
    `--check` verifies every one.

### Fixed

- **`geometry.xsd` is now declared in `files.sidecars` for the six GML cases.** It was
  hashed by `generate_checksums.py` but undeclared, and `validate_catalog.py` only checks
  declared files — so a missing GML schema would have shipped unnoticed.

- **`docs/dataset-catalog.md` geography was wrong.** Thirty-six baselines sat at or beside
  `(0, 0)` — colliding with the `null_island_point` sentinel's entire reason for existing —
  while the page claimed they were in Central Europe. Convergence makes the claim true and
  leaves only seven deliberate cases near the origin. The bundled-payload figure is also
  corrected from 4.2 MB to its actual 2.1 MB.

- **The bundled case count is 135, not 134.** The 1.0.0 entry's "134 bundled cases" was
  correct at that release; the catalog has grown by one since. `README.md`, `docs/index.md`
  and `recipe/meta.yaml`'s build-time assertion said 134 and now say 135, and
  `scripts/validate_catalog.py` gates all three against `len(get_registry())` so the number
  cannot drift again.

## [1.0.0] — 2026-08-02

First stable release. Version `0.1.0` was never uploaded.

> **Correction (2026-08-23):** this entry originally claimed 1.0.0 was "the first release
> published to PyPI". It was not — no GeoCase version has ever been uploaded to PyPI or
> TestPyPI. The release process in
> [Releasing](contributing/releasing.md) is written and gated but has not yet been run;
> see [Plan 25](plans/25-ship-geocase-as-a-package.md).

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
- `project.urls` now point at the canonical repository host. (This entry originally said
  "GitLab"; the project has always lived on GitHub at
  <https://github.com/farzinashouri/geocase>, and the URLs point there.)
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

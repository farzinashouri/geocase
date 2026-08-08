# Plan 13 — Converge the `*_baseline` vector families onto their declared canonical

> **Status: proposed.** Scope is this document; order is owned by
> [`execution-order.md`](execution-order.md) and scope disputes by
> [`development-plan.md`](development-plan.md).

## Context

Three independent evaluation pilots reported the same blocking corpus defect against
1.0.0rc1, and it is still present. Case families named `<geomtype>_<format>_baseline`
promise **one geometry expressed across many file formats** — that is the single
comparison GeoCase exists to support. The promise is not kept.

Each such `case.yaml` declares `params.canonical_source_case_id` pointing at
`simple_valid_<geomtype>` (a GeoJSON case), and carries the tag
`cross_format_canonical`. **Nothing in `src/` or `tests/` ever dereferences that link**,
so the divergence is structurally invisible to the test suite.

Why this is worse than a missing fixture: it silently produces *fabricated results*.
Anyone who trusts the naming and diffs KML-vs-Shapefile output reports a cross-format
differential that is purely a corpus artifact. One pilot nearly filed exactly that before
checking coordinates; another lost its central question to it.

**Verified scope — roughly 4× what the pilots reported.** Loading all 60 tagged cases plus
the 6 canonicals shows only **6 of 60** fixtures currently carry their canonical geometry
(`point_flatgeobuf/kml/feather/arrow_baseline`, `linestring_csv_wkt_baseline`,
`polygon_sqlite_baseline`); 2 more match under a winding-insensitive comparison. The
pilots' "10 genuine twin groups" claim is wrong: `multipoint`, `multilinestring` and
`multipolygon` are internally consistent but *every member diverges from its canonical* —
and the `multilinestring` baselines have 2-vertex parts where the canonical has 3, so no
coordinate tolerance would ever have hidden it.

Canonical geometries, all EPSG:4326:

| family | canonical geometry |
|---|---|
| point | `POINT (12.5 55.7)` |
| linestring | `LINESTRING (10 50, 10.5 50.3, 11 50.1)` |
| polygon | `POLYGON ((10 50, 11 50, 11 51, 10 51, 10 50))` |
| multipoint | `MULTIPOINT ((10 50), (10.2 50.1), (10.4 50.2))` |
| multilinestring | `MULTILINESTRING ((10 50, 10.5 50.2, 11 50.1), (10.2 49.8, 10.8 49.9, 11.1 50))` |
| multipolygon | `MULTIPOLYGON (((10 50, 10.5 50, 10.5 50.5, 10 50.5, 10 50)), ((11 50, 11.5 50, 11.5 50.5, 11 50.5, 11 50)))` |

Intended outcome: `all_equal_geometry([...])` across a family becomes a meaningful
assertion, enforced mechanically at generation time and gated in CI.

**Scope discipline.** This plan is the corpus fix only. The pilots' other
recommendations — a `geocase.literals` / `geocase.cases` namespace split, per-stack-version
expected values, a `geocase doctor` command, repositioning — are deliberately out of
scope and are queued as a follow-on decision (see the last section).

## Decisions

### Winding

Author to RFC 7946 / OGC right-hand rule (exterior CCW, interior CW) via
`shapely.geometry.polygon.orient(geom, sign=1.0)` before any write — the canonicals are
already CCW.

But **compare winding-insensitively**: the Shapefile specification mandates the opposite,
and OGR rewrites orientation on write regardless of input. Comparison is

```python
shapely.equals_exact(shapely.normalize(actual), shapely.normalize(expected), tolerance=1e-9)
```

plus a separate `geom_type` assertion — `normalize` alone will not catch a
`Polygon` → `MultiPolygon` promotion. `normalize` canonicalizes ring orientation, ring
start vertex, component ordering and LineString direction, so it absorbs every legitimate
driver rewrite while still failing on any coordinate, vertex-count or component-count
change. The `1e-9` tolerance covers GML/KML text serialization; everything else is float64
end to end.

### Attribute schema — unify

Every `_baseline` fixture gets exactly `id: int64 = 1` and `name: str = <case_id>`, in that
order.

Today a consumer diffing `polygon_geopackage_baseline` (`id, name, area_sqkm`) against
`polygon_shapefile_baseline` (`name`) cannot tell which differences are *the format* and
which are fixture accident. After unification every surviving column difference is
attributable to the driver — which is the family's entire pedagogical payload.
Format-idiomatic schemas are already covered, deliberately and better, by
`special/encoding/{shapefile_field_truncation, shapefile_encoding_legacy,
mixed_encoding_attributes, parquet_mixed_schema_attributes}`. Duplicating that concern
inside `_baseline` is what let `multilinestring_shapefile_baseline` ship a column named
`segment_co` — a silent DBF 10-char truncation of `segment_count` — undocumented, inside a
family whose whole job is to hold everything but the format constant.

Both chosen names are ≤10 chars, so the write path needs no per-format field-name
special-casing.

Documented, **unfixable** exceptions — assert a *subset* relation, not equality:

- **KML** — OGR synthesizes `Name, description, timestamp, begin, end, altitudeMode,
  tessellate, extrude, visibility, drawOrder, icon` regardless of file content.
- **GML** — OGR injects `gml_id`.
- **WKT / WKB** — no attribute slot in the format; `VectorCase.load()` synthesizes
  `[{"name": self.id}]`, which setting `name = <case_id>` makes a strict subset of the
  real frames rather than a separate vocabulary.

**Do not touch the six `simple_valid_*` GeoJSON canonicals.** They are the reference, and
`simple_valid_polygon.params.expected_bounds` is consumed by
`examples/_easy_geospatial_interview_test_support.py` and its sibling.

### Gate placement — three layers, split by dependency

The CI `catalog` job runs in `ghcr.io/osgeo/gdal` with `-e .[raster] "numpy<2"` — **no
geopandas, shapely or pyarrow**. That constraint drives the split:

| Layer | Home | Checks |
|---|---|---|
| Metadata | `scripts/validate_catalog.py` | tag ⇄ param biconditional, id resolves, target is GeoJSON, `geometry_type` matches |
| Semantics | **new** `tests/unit/test_cross_format_canonical.py` | load → normalize → assert geometry, type, CRS, `name` |
| Fingerprint | `scripts/generate_vector_fixtures.py --check` | semantic fingerprint; byte-compare WKT/WKB/CSV_WKT only |

The semantic gate must go through `VectorCase.load()`, not `geopandas.read_file` — only
that exercises the hand-rolled CSV_WKT/WKT/WKB/Parquet/Feather/Arrow branches consumers
actually hit. Putting geometry comparison in `validate_catalog.py` instead would mean
adding geopandas and pyarrow to the catalog job under the `numpy<2` pin for no coverage
gain.

## Steps

### 1. Metadata first (no binary churn, lands independently)

- Add the missing `params.canonical_source_case_id: simple_valid_point` to
  `src/geocase/data/core/vector/point/gml/point_gml_baseline/case.yaml`. This one case is
  the entire 59-declared vs 60-tagged gap.
- Add `_validate_cross_format_canonical(registry)` to `scripts/validate_catalog.py`, called
  from `main()` alongside the existing validators and raising `CatalogValidationError` in
  the same message style. Checks: tag ⇄ param biconditional; the param resolves in the
  registry; target `format == "GeoJSON"`; `geometry_type` matches between case and
  canonical; the canonical is not itself tagged.
- No schema change is needed — `case.schema.yaml`'s `params` is `type: object` with
  `additionalProperties: true`, and `CaseMetadata.params` is `dict[str, Any]`.

### 2. Derive the generator's specs from canonical

In `scripts/generate_vector_fixtures.py`, replace the literal `VectorSpec.wkt` / `fields`
declarations with derivation:

- `_canonical_geometry(case_id)` reads
  `<geomtype>/geojson/simple_valid_<geomtype>/geometry.geojson` via `json` +
  `shapely.geometry.shape` — **not** via `geocase.load_case`. The generator must not depend
  on the package whose data it generates; `verify_dist.py` was made independent for the
  same reason (commit `8cffc22`).
- `_specs()` walks `VECTOR_ROOT/**/case.yaml`, selects cases declaring
  `canonical_source_case_id`, and builds one spec per case from `id`, `format`,
  `files.primary` and the resolved canonical geometry, orienting polygons CCW.
- **Rewrite the `_specs()` docstring.** It currently documents this defect as a known,
  accepted deviation, on the grounds that deriving "would silently rewrite the fixtures and
  break the tests that assert against them." That was true when written and is **false
  now** — a grep for coordinate literals across `tests/` returns zero matches. Leaving it
  would leave the trap's own warning sign pointing the wrong way.

### 3. Add write backends, mirroring `VectorCase.load()`'s dispatch exactly

- `_write_ogr` — Shapefile, GPKG, SQLite (the existing path, generalized), GML, KML,
  FlatGeobuf. Keep `osgeo.ogr` rather than switching to pyogrio, so the SpatiaLite
  `SPATIALITE=YES` + trim + `VACUUM` path is untouched. Use `SPATIAL_INDEX=NO` for
  single-feature FlatGeobuf.
- `_write_text` — WKT; WKB via `to_wkb(byte_order=1, include_srid=False)` matching the
  committed little-endian no-SRID form; CSV_WKT via `csv.writer(lineterminator="\n")` with
  fixed columns `id,name,geometry`.
- `_write_geopandas` — Parquet (`to_parquet`), Feather (`to_feather`). Pin the GeoParquet
  `schema_version` explicitly and check it against
  `geocase.assertions.format_compliance.assert_geoparquet_metadata`.
- `_write_arrow_ipc` — Arrow, GeoArrow via `pyarrow.ipc.new_file` on `gdf.to_arrow()`.
  **IPC *file* format, not stream** — `VectorCase.load()` reads these with
  `pyarrow.ipc.open_file`.

### 4. Generalize `--check`

Split `_fingerprint` into `_fingerprint_ogr` (existing, with the SpatiaLite-only parts made
conditional), `_fingerprint_text` (raw bytes) and `_fingerprint_arrow`. Keep `_diff`, keep
the `_MAX_BYTES` budget for SQLite and add a smaller one for the rest, and keep the exit-2
"cannot verify" semantics — never degrade to a silent pass — extending it to missing
geopandas/pyarrow.

Determinism, per format:

| Format | Deterministic | Notes |
|---|---|---|
| WKT, WKB, CSV_WKT | **Yes** | Pure Python, no driver in the loop — these three can byte-compare |
| GML, KML | Yes | Text, no timestamp. GML writes a `.xsd` sidecar |
| FlatGeobuf | Yes, per GDAL version | No timestamps |
| Shapefile | **No** | `.dbf` header bytes 1–3 are the last-update date; checksums drift daily with identical content. Semantic fingerprint only |
| GPKG | **No by default** | `gpkg_contents.last_change` is wall-clock (verified present in the committed `point_geopackage_baseline/data.gpkg`). Set `OGR_CURRENT_DATE`, **verify empirically in the GDAL container**, and fall back to a post-write `sqlite3 UPDATE` if it does not take |
| SQLite/SpatiaLite | **No** | Already handled — `spatialite_history` carries wall-clock plus library versions |
| Parquet, Feather, Arrow | **No** | `created_by` footer plus geopandas creator metadata. Semantic only |

### 5. Regenerate

```bash
python scripts/generate_vector_fixtures.py
python scripts/generate_checksums.py
```

`generate_checksums.py` already discovers every `case.yaml` directory and hashes every
payload file, so it needs no change. While touching the GML cases, declare `geometry.xsd`
in `files.sidecars` — it is currently hashed but undeclared, and `validate_catalog.py` only
checks declared files.

### 6. Preserve the real artifact as a named case

Add `src/geocase/data/core/vector/special/encoding/shapefile_ring_orientation/`, modelled on
its sibling `shapefile_field_truncation` — the existing precedent for promoting a format
artifact to a named case. Same geometry as `simple_valid_polygon` but with the exterior ring
**CW**: today's `polygon_shapefile_baseline` bytes preserved rather than discarded.

- `format: Shapefile`, `geometry_type: Polygon`, `crs: EPSG:4326`, `test_tier: unit`,
  `size_class: tiny`.
- Tags `vector, polygon, shapefile, winding, ring_orientation, format_specific`;
  `risk_types: [ring_orientation, format_specific]`. The `format_specific` tag makes
  `vector-schema-encoding.yaml`'s `tags_any` selection pick it up — add it to that suite's
  `case_order` explicitly.
- **Deliberately omits `cross_format_canonical`**, and uses distinct param names
  (`reference_case_id`, `exterior_ring_orientation: cw`,
  `reference_ring_orientation: ccw`) so the Step 1 biconditional does not trip.
- `notes.md` states the mechanism: the Shapefile specification mandates CW exterior rings
  and OGR rewrites winding on write, so a GeoJSON → Shapefile round trip silently reverses
  orientation; code that reads `is_ccw` to infer interior from exterior breaks here.
- Register with `python scripts/build_case_index.py`.

This is correct independent of preservation. The invariant in the winding decision above is
necessarily winding-insensitive, so inside a `_baseline` family this artifact is not merely
undocumented — it is *unassertable*. Only as its own case can anything assert it.

### 7. Tests

- **New** `tests/unit/test_cross_format_canonical.py`, parametrized over cases discovered
  from `case-index.yaml` using the same auto-discovery pattern as
  `tests/unit/test_format_compliance.py` — so future baselines are gated without anyone
  remembering. Per case: exactly 1 feature; `geom_type` matches the canonical;
  `equals_exact(normalize(a), normalize(b), 1e-9)`;
  `pyproj.CRS.from_user_input(gdf.crs) == CRS.from_epsg(4326)` (**must** go through
  `pyproj.CRS` — Parquet/Feather/Arrow/GeoArrow return a full PROJJSON object, not the
  string `"EPSG:4326"`); `name` equals the case id; and `{"id", "name"} ⊆ columns` except
  for one explicit, commented allowlist covering the KML/GML/WKT/WKB exceptions.
- **New** test for `shapefile_ring_orientation`: topologically `equals` the canonical **and**
  `not is_ccw(exterior)` **and** the canonical *is* CCW. All three, or the test proves
  nothing.
- **New** unit test for the `validate_catalog.py` invariant, beside
  `tests/unit/test_validate_catalog_manifests.py`.
- **Existing tests need no edits.** `tests/unit/test_cases.py` asserts only feature count,
  `crs is not None` and `geom_type` across all ~60 baseline blocks; the only value
  assertions in the suite belong to encoding and dateline cases, and `examples/` reads
  `expected_bounds` from `simple_valid_polygon.params`, which this plan does not touch.
  Re-run the greps after the change rather than trusting this.
- Do **not** add a public `assert_geometry_equals` to `src/geocase/assertions/geometry.py`.
  `tests/unit/test_public_api.py` pins the exported surface against a literal and
  `CHANGELOG.md` makes an explicit stability promise about it; adding a name mid-rc widens
  that promise for a helper only one internal test needs. Keep it private to the test module
  and promote it in v1.1 if it earns a second caller.

### 8. Docs, generated artifacts, CI

- `.github/workflows/ci.yml`, `catalog` job: `-e .[raster] "numpy<2"` →
  `-e .[raster,vector] "numpy<2"`. No new step is needed — `generate_vector_fixtures.py
  --check` and `generate_checksums.py --check` already run there, and the new test rides the
  existing `pytest` job.
- `docs/dataset-catalog.md`, "Where in the world we test": the Central Europe and Copenhagen
  rows both change counts, since the ten point baselines move to Copenhagen and the
  unit-square families move into Central Europe. Worth stating in prose that ~20 baselines
  currently sit at or beside `(0, 0)`, colliding with the `null_island_point` sentinel's
  entire reason for existing; convergence removes that collision. This page is gated by
  `_validate_documented_case_ids`.
- Regenerate `docs/_generated/` via `generate_catalog_pages.py` and
  `generate_vector_coverage_matrix.py` — CI diffs these, so run them even where no change is
  expected.
- `docs/contributing/vector-dataset-generation.md`: add a short section stating that
  `_baseline` fixtures are generated, never hand-edited, and that their geometry comes from
  `params.canonical_source_case_id`.
- `CHANGELOG.md` — **required**. This changes shipped fixture bytes, which breaks any
  downstream test asserting baseline coordinates. `pyproject.toml` is at `1.0.0rc1` and
  1.0.0 final is not yet on real PyPI, so **land this before it** — an rc exists precisely so
  this is free. Add an `## [Unreleased]` → `### Changed` entry with the old→new coordinate
  table so consumers can diff their own assertions, plus the 59→60 tag fix, the unified
  `id`/`name` schema, and the new case. If 1.0.0 has shipped by then this becomes a `1.1.0`
  entry — never a patch release.

## Files

**Modified — code and gates**

- `scripts/generate_vector_fixtures.py` (the bulk; ~429 → ~700 lines)
- `scripts/validate_catalog.py`
- `.github/workflows/ci.yml`
- `src/geocase/catalog/suites/vector-schema-encoding.yaml`
- `src/geocase/metadata/case-index.yaml` (regenerated)

**New**

- `tests/unit/test_cross_format_canonical.py`
- `src/geocase/data/core/vector/special/encoding/shapefile_ring_orientation/`

**Modified — fixtures.** 60 case directories under
`src/geocase/data/core/vector/{point,linestring,polygon,multipoint,multilinestring,multipolygon}/<format>/`
— payload, `checksums.sha256`, `notes.md`, and `case.yaml` wherever the description claims
"the same coordinates as the GeoJSON baseline" while not being true.

**Modified — docs.** `docs/dataset-catalog.md`,
`docs/contributing/vector-dataset-generation.md`, `CHANGELOG.md`, regenerated
`docs/_generated/**`.

**Deliberately untouched.** The six `simple_valid_*` GeoJSON canonicals;
`src/geocase/cases/vector.py`; `src/geocase/metadata/schemas/case.schema.yaml`;
`src/geocase/assertions/*`.

## Traps

1. **The generator's own docstring is the trap's warning label — and it is now stale.**
   Re-verify the greps rather than trusting either it or this plan.
2. **~52 fixtures change geometry**, not a handful of outliers. Budget for it; do not
   discover it mid-implementation.
3. **Arrow/GeoArrow must be IPC file format**, not stream, or the fixture becomes unloadable
   and only the new test will say so.
4. **The catalog CI job has no geopandas** — the generator will `ImportError` there until the
   install line changes. Keep exit-2; never a silent pass.
5. **KML/GML column injection is not fixable.** Assert a subset, and keep the exception list
   in one commented constant rather than scattered `if` branches.
6. **Regenerating KML drops the hand-added `<Style>` block** in `polygon_kml_baseline`. That
   is intentional — styling is `format_limited_kml_case`'s job — but say so in the changelog
   so it does not look accidental.
7. **GML uses `urn:ogc:def:crs:EPSG::4326`**, which forces lat/lon axis order in `posList`
   (the committed file reads `55 12`, not `12 55`). It round-trips correctly through OGR but
   looks swapped to naive text diffing. Keep the URN form; it is real behaviour worth
   keeping.

## Verification

```bash
# 1. Metadata layer (no geospatial deps needed)
python scripts/validate_catalog.py
python scripts/build_case_index.py --check

# 2. Regenerate + checksums (GDAL env with osgeo + geopandas + pyarrow)
python scripts/generate_vector_fixtures.py && python scripts/generate_checksums.py
python scripts/generate_vector_fixtures.py --check   # must pass immediately after
python scripts/generate_checksums.py --check

# 3. Semantic gate
python -m pytest tests/unit/test_cross_format_canonical.py -q
python -m pytest tests -q

# 4. NEGATIVE CONTROLS — the gate must be observed failing
#    a) edit polygon_wkt_baseline/polygon.wkt back to (12 55 ...)  -> test must FAIL
#    b) delete params.canonical_source_case_id from a tagged case  -> validate_catalog must FAIL
#    c) git-revert one fixture                                     -> --check must FAIL
#    Restore all three afterwards.

# 5. Idempotence
python scripts/generate_vector_fixtures.py && git status --porcelain -- src/geocase/data
#    Expect: only Shapefile .dbf dirty (date byte). If GPKG appears,
#    OGR_CURRENT_DATE did not take -> use the sqlite3 UPDATE fallback.

# 6. Docs
python scripts/generate_catalog_pages.py --check
python scripts/generate_vector_coverage_matrix.py --output docs/_generated/vector-coverage-matrix.md
git status --porcelain -- docs/_generated && mkdocs build --strict

# 7. Re-confirm no coordinate literals crept into assertions (baseline: 0 matches)
grep -rn "POINT (\|POLYGON ((\|LINESTRING (" tests/ examples/ --include="*.py"

# 8. Lint and types
ruff format --check src tests && ruff check src tests && mypy src
```

Step 4 is the one that matters most. Every gate in this plan exists because an earlier one
was absent; shipping a new one without watching it go red would repeat exactly the failure
being fixed.

## Follow-on — the direction decision

Deliberately **not** part of this plan, and blocked on it: the version-matrix thesis is
untestable until the cross-format comparison actually works.

Across three pilots, 27 findings included exactly one version-sensitive result
(`epsg_to_prj(102100)` returning `''` under PROJ 9.1.1, where deprecated `900913` still
resolves), and GeoCase contributed nothing to finding it. The pilots' conclusion: as a set
of static example files GeoCase is well-built but replaceable by a committed
`tests/fixtures/` directory, and the only thing that makes it a *versioned package* is
tracking where GDAL/PROJ behaviour moves between releases.

Four questions to settle once this plan lands:

1. **Per-version expected values.** Is a queryable "which cases behave differently on GDAL
   3.6 vs 3.9?" matrix buildable and maintainable by one person, or is a perpetual CI grid
   across GDAL/PROJ releases a trap? Note that `CaseMetadata` has no version-sensitivity
   field today; the only escape hatch is the untyped `params` dict.
2. **A `geocase.literals` / `geocase.cases` namespace split**, to address the 90–97% noise
   rate the pilots measured. Note that `list_cases()` already supports `geometry_type`,
   `format`, `tags_any`, `tags_all` and `risk_types_any` — the real gaps are `path_for()`,
   `family()`, and that `geocase_cases` returns `[]` silently where the `geocase` fixture
   correctly raises `UsageError`.
3. **`geocase doctor`** as the adoption wedge — one pilot found a production environment
   silently missing its PROJ database. Highest apparent value per unit of effort, and a
   natural front end for (1) if it gets built. Note the CLI stub and its console script
   were deliberately removed before v1.0, so this is greenfield.
4. **Positioning** — away from "a corpus of geospatial edge cases" and toward untrusted,
   multi-format ingestion (survey consultancies, submission portals, data marketplaces,
   "drag your Shapefile here" apps), and away from controlled single-format ETL pipelines,
   where the pilots showed GeoCase loses for structural rather than fixable reasons.

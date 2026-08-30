# Vector Dataset Generation

> Consolidated from historical docs: `vector-dataset-generation-plan.md`, `building-comprehensive-vector-dataset.md`

This document defines how to grow vector cases inside the current GeoCase architecture.

---

## Overview

GeoCase currently discovers cases through `case-index.yaml` and loads per-case metadata from `case.yaml`.

For vector cases, the runtime contract is:

1. `src/geocase/data/core/vector/<case_id>/case.yaml` exists
2. `files.primary` points to a file in that folder
3. Case path is registered in `src/geocase/metadata/case-index.yaml`
4. Selectors/suites reference metadata fields (`tags`, `risk_types`, `geometry_type`, `format`, `test_tier`)

---

## Repository Layout

```text
src/geocase/
├── data/
│   └── core/
│       └── vector/
│           ├── polygon/
│           │   └── geojson/
│           │       └── simple_valid_polygon/
│           ├── special/
│           │   ├── dateline/
│           │   ├── invalid/
│           │   └── crs/
│           └── ...
├── metadata/
│   └── case-index.yaml
└── catalog/
    └── suites/
        ├── core-vector.yaml
        └── vector-topology.yaml
```

---

## Naming Strategy

Use **short, stable lowercase IDs**:

- `simple_valid_polygon`
- `self_intersecting_polygon`
- `classic_antimeridian_polygon`
- `mixed_encoding_attributes`

Use `title` and `description` for human-readable richness. Avoid long encoded names.

---

## Metadata Mapping

Most concepts map cleanly to `CaseMetadata`:

| Concept | GeoCase Field |
|---------|---------------|
| Geometry family/type | `category: vector`, `geometry_type` |
| Validity/pathology | `tags`, `risk_types`, `assertions.expect_valid_geometry` |
| CRS | `crs`, `assertions.expected_epsg`, `tags` |
| Format behavior | `format`, `expected_capabilities`, `params` |
| Engine expectation | `assertions` + optional `params["engine_expectations"]` |

### Example case.yaml

```yaml
id: bowtie_invalid_polygon
title: Self-intersecting bow-tie polygon
description: >
  Polygon with a clear self-intersection intended for topology and
  invalid-geometry behavior checks.
category: vector
format: GeoJSON
test_tier: unit
size_class: tiny
storage_class: bundled
redistributable: true
schema_version: "1.0"
status: validated

tags:
  - vector
  - polygon
  - invalid
  - topology
  - self_intersection

risk_types:
  - topology

behavioral_goal: >
  Ensure invalid polygon handling is detected consistently.

expected_capabilities:
  - load
  - geometry-validation

loader_hint: geopandas
geometry_type: Polygon
crs: EPSG:4326

files:
  primary: geometry.geojson
  notes: notes.md

source:
  name: geocase-curated
  license: MIT

assertions:
  expect_loadable: true
  expect_valid_geometry: false
  expected_epsg: 4326
  expected_geometry_types:
    - Polygon

params:
  location_label: Gulf of Guinea
  pathology:
    - self_intersection
```

---

## Coverage Matrix

### Geometry Types

| Geometry type | Status |
|---|---|
| Point | ✅ present |
| MultiPoint | ✅ present |
| LineString | ✅ present |
| MultiLineString | ✅ present |
| Polygon | ✅ present |
| MultiPolygon | ✅ present |
| GeometryCollection | ✅ present |

### Formats

| Format | Status |
|---|---|
| GeoJSON | ✅ broad coverage |
| GPKG | ✅ present |
| Shapefile | ✅ present |
| Parquet | ✅ present |
| GML | ✅ present |
| KML | ✅ present |
| CSV_WKT | ✅ present |
| Feather/Arrow | ✅ present |
| WKB | ✅ present |
| WKT | ✅ present |
| SQLite | ✅ present |
| FlatGeobuf | ✅ present |

### Spatial Coverage

| Category | Status |
|---|---|
| North pole | ⚠️ baseline point present; polygon complement still missing |
| South pole | ⚠️ baseline point present; polygon complement still missing |
| Equator | ⚠️ crossing line present; polygon complement still missing |
| EPSG:3857 | ⚠️ baseline present; precision follow-up still under review |
| Antimeridian/dateline | ✅ present |
| UTM boundaries | ✅ present |

### Edge-Case Categories

| Category | Status |
|---|---|
| Topology defects | ✅ present |
| CRS mismatch/reprojection | ✅ present |
| Schema/encoding issues | ✅ present |
| Empty/null geometry | ✅ present |
| Precision/rounding artifacts | ✅ present |
| Multipart dissolve/overlay | ✅ present |
| Ambiguous/engine-dependent | ✅ present |
| Degenerate but parseable | ✅ present |

---

## Gap Tracking

Regenerate the coverage matrix from metadata:

```bash
python scripts/generate_vector_coverage_matrix.py
python scripts/generate_vector_coverage_matrix.py --output docs/_generated/vector-coverage-matrix.md
```

### Remaining Gaps

| Category | Gap | Planned case |
|---|---|---|
| Format-specific | Parquet mixed schema | `parquet_mixed_schema_attributes` |
| Format-specific | KML format limits | `format_limited_kml_case` |
| Spatial complement | North pole polygon | `north_pole_polygon` |
| Spatial complement | South pole polygon | `south_pole_polygon` |
| Spatial complement | Equator polygon | `equator_polygon` |
| CRS refinement | Web Mercator precision follow-up | `web_mercator_precision_case` (if still justified) |
| Null vs empty semantics | Distinct null-geometry GPKG behavior | `null_geometry_row_gpkg` (if distinct from `empty_geometry_gpkg`) |
| Release policy | Geometry × format completeness decision | document defer/require decision before expanding sparse cells |

---

## Maintainer Workflow

### Step A — Create case folder

Create:
- `src/geocase/data/core/vector/<case_id>/case.yaml`
- `src/geocase/data/core/vector/<case_id>/<primary file>`
- Optional `notes.md`

### Step B — Fill metadata

Populate required `CaseMetadata` fields exactly as defined in `src/geocase/catalog/models.py`.

### Step C — Register in index

Add to `src/geocase/metadata/case-index.yaml`:

```yaml
- path: data/core/vector/<case_id>/case.yaml
```

### Step D — Include in suite(s)

Add case to suite files in `src/geocase/catalog/suites/`:
- `core-vector.yaml` (baseline)
- `vector-topology.yaml`, `vector-crs-edge.yaml`, etc. (specialized)

### Step E — Validate

```bash
python scripts/build_case_index.py --check
python scripts/validate_catalog.py
pytest tests/unit/test_loader.py tests/unit/test_registry.py -q
```

---

## Coordinate Reuse Policy

Use a hybrid strategy for location reuse across formats:

- **Canonical cross-format baselines:** Keep same coordinates across formats for comparison
- **Format-specific stress cases:** Use different coordinates if format quirks require it
- **Geography-dependent edge cases:** Use different locations when geography is the point (poles, antimeridian, etc.)
- **Default rule:** Reuse exact coordinates unless there's a clear reason not to

---

## `*_baseline` Fixtures Are Generated

**Never hand-edit a `<geometry>_<format>_baseline` payload.** Every one of the 60 is
written by `scripts/generate_vector_fixtures.py`, and its geometry is *derived* — read at
generation time from the case named in `params.canonical_source_case_id`, which always
points at the GeoJSON `simple_valid_<geometry>` canonical.

This is not a style preference. These fixtures were hand-authored until v1.0.0, and 53 of
the 60 had drifted to hold a different geometry from the canonical they declared. Because
the declaration was never dereferenced anywhere in `src/` or `tests/`, the divergence was
structurally invisible: a consumer who trusted the naming and diffed KML against Shapefile
got a cross-format difference that was purely a fixture accident. Two independent
evaluations hit it, and one lost its central question to it.

### To change a baseline geometry

Edit the **canonical** — `src/geocase/data/core/vector/<geometry>/geojson/simple_valid_<geometry>/geometry.geojson`
— then regenerate:

```bash
python scripts/generate_vector_fixtures.py
python scripts/generate_checksums.py
```

All eleven format twins move together, because they all read the same source. Editing one
twin directly cannot work: `generate_vector_fixtures.py --check` runs in CI and will fail.

Always run `generate_checksums.py` afterwards, and expect the five SpatiaLite databases to
show as modified **on every run even when nothing changed** — SpatiaLite writes wall-clock
timestamps and its own library versions into `spatialite_history`, so their bytes are not
reproducible. Everything else, GeoPackage and Shapefile included, is byte-stable. This is
why `--check` compares semantics rather than checksums; see the module docstring.

### To add a baseline

Create the case folder and `case.yaml` as usual, then give it both halves of the
declaration — the `cross_format_canonical` tag *and*
`params.canonical_source_case_id`. `scripts/validate_catalog.py` enforces that the two are
biconditional, that the id resolves, that the target is GeoJSON, and that the geometry
types match. Nothing else is needed: the generator discovers cases by walking `case.yaml`,
and `tests/unit/test_cross_format_canonical.py` auto-discovers from `case-index.yaml`, so a
new baseline is generated and gated without either file being edited.

### What the fixtures hold

Every baseline carries exactly one feature, `id: int64 = 1` and `name: str = <case_id>`, in
that order. The uniform schema is what makes a column diff between two members meaningful —
whatever differs is attributable to the driver. Three formats cannot honour it and are
documented exceptions: KML renames `name` to `Name` and synthesizes ~10 columns, and
WKT/WKB have no attribute slot at all. Format-idiomatic schemas belong in
`special/encoding/`, not here.

### Winding

Polygons are authored counter-clockwise (RFC 7946 / OGC right-hand rule) via
`shapely.geometry.polygon.orient(geom, sign=1.0)`, but compared **winding-insensitively**
through `shapely.normalize`, because the Shapefile specification mandates the opposite and
OGR rewrites orientation on write regardless of input. The orientation itself is asserted
by the `shapefile_ring_orientation` case, which exists precisely because it is unassertable
inside a baseline family.

---

## The Large Cases

Three cases under `vector/special/scale/` hold ~10,000 features each, against one
for every baseline and at most four elsewhere in the catalog:

| Case | Features | What only a full read sees |
|---|---|---|
| `invalid_geometry_at_scale_gpkg` | 10,000 | a self-intersecting bowtie at index 9,999 |
| `null_after_batch_boundary_gpkg` | 10,001 | the first NULL, after 10,000 non-NULL integers |
| `mixed_timezone_after_batch_gpkg` | 10,001 | a UTC offset that changes only at the last row |

The size is not the point; **discriminating power** is. A probe for `skip_features`,
`max_features`, Arrow batch chunking or a paged read still *executes* against a
one-feature fixture — it simply cannot fail, because with one feature every batch
boundary is the same boundary and every partial read is the full read. Each of these
puts its one defect past the boundary, so a consumer that reads a prefix reports clean
and a consumer that reads everything does not.

They are built by `_large_specs()` / `_write_large()` in
`scripts/generate_vector_fixtures.py` and covered by the same `--check` gate as
everything else here, with their own fingerprint: comparing 10,000 WKB blobs produces
an unreadable diff that says nothing about *what* changed, so `_fingerprint_large`
compares the schema, the bounds, and the **defect itself** — the property a bad
regeneration would actually destroy. Removing the bowtie makes `--check` report
`invalid_rows: expected [9999], got []`.

### Adding another one

Weigh it against the wheel first. These three take the payload tree from 2.1 MB to
5.1 MB and the wheel from 456 KB to 1.25 MB, against `verify_dist.py`'s 2 MB ceiling —
so roughly one more trio fits, and the one after that belongs in a remote manifest
instead. The ceiling is deliberately not raised to make room.

Then: give the case `size_class: small`, declare `params.expected_feature_count` (the
generator reads its size from there, so the metadata and the content gate cannot
disagree), add the id to `_LARGE_CASE_IDS`, and give it an attribute recipe in
`_large_frame` plus a defect clause in `_fingerprint_large`. Write it with
`SPATIAL_INDEX=NO` unless the index is the subject — the R-tree costs ~750 KB on 10,000
features.

---

## Multi-Format Strategy for Special Cases

Most special datasets test **geometry behaviors** that are independent of storage format. Don't duplicate geometry-behavior cases across formats.

Add format-specific variants only where the **format itself creates a distinct edge case**:

| Case | Format | Rationale |
|------|--------|-----------|
| `shapefile_field_truncation` | Shapefile | 10-character field name limit |
| `shapefile_encoding_legacy` | Shapefile | DBF code page handling |
| `shapefile_ring_orientation` | Shapefile | CW exterior rings, against RFC 7946's CCW |
| `precision_loss_geojson_roundtrip` | GeoJSON | Text serialization precision |
| `empty_geometry_gpkg` | GPKG | NULL vs EMPTY representation |

---

## Suite Organization

| Suite | Purpose |
|-------|---------|
| `core-vector` | Default fast CI set |
| `vector-topology` | Topology defects and repairs |
| `vector-crs-edge` | CRS and projection edge cases |
| `vector-schema-encoding` | Format-specific encoding issues |

---

## Validation Loop

Run this for every case batch before merge:

```bash
python scripts/build_case_index.py --check
python scripts/validate_catalog.py
pytest tests/unit/test_loader.py tests/unit/test_registry.py tests/unit/test_selectors.py tests/unit/test_suites.py -q
```

---

## Definition of Done

A vector dataset increment is done when:

- New case files exist and load as expected
- Generated index is up to date
- Suites are reviewed and updated if needed
- Validation scripts pass
- Relevant unit tests pass
- Docs mention any new conventions/tags introduced

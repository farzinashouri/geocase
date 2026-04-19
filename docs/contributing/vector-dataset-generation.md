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

## Multi-Format Strategy for Special Cases

Most special datasets test **geometry behaviors** that are independent of storage format. Don't duplicate geometry-behavior cases across formats.

Add format-specific variants only where the **format itself creates a distinct edge case**:

| Case | Format | Rationale |
|------|--------|-----------|
| `shapefile_field_truncation` | Shapefile | 10-character field name limit |
| `shapefile_encoding_legacy` | Shapefile | DBF code page handling |
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

### Coverage matrix (current vs target)

Use this matrix as the release gate for "comprehensive" status.

#### A) Geometry types

| Geometry type | Current coverage (core vector) | Target |
|---|---:|---:|
| Point | ✅ present | ✅ required |
| MultiPoint | ✅ present | ✅ required |
| LineString | ✅ present | ✅ required |
| MultiLineString | ✅ present | ✅ required |
| Polygon | ✅ present | ✅ required |
| MultiPolygon | ✅ present | ✅ required |
| GeometryCollection | ✅ present | ✅ required |

#### B) Formats

| Format | Current coverage (core vector) | Target |
|---|---:|---:|
| GeoJSON | ✅ broad coverage | ✅ required |
| GPKG | ✅ present | ✅ required |
| Shapefile | ✅ present | ✅ required |
| Parquet | ✅ present | ✅ required |
| GML | ✅ present | ✅ required |
| KML | ✅ present | ✅ required |
| CSV_WKT | ✅ present | ✅ required |
| Feather/Arrow variants | ✅ present | ✅ required |
| WKB | ✅ present | ✅ required |
| WKT | ✅ present | ✅ required |
| SQLite | ✅ present | ✅ required |
| FlatGeobuf | ✅ present | ✅ required |

#### C) Complexity and validity

| Dimension | Current coverage (core vector) | Target |
|---|---:|---:|
| Simple baseline geometries | ✅ present | ✅ required |
| Complex/multipart geometries | ✅ present | ✅ required |
| Valid datasets | ✅ present | ✅ required |
| Invalid/pathological datasets | ✅ present | ✅ required |
| Ambiguous / engine-dependent validity | ✅ present | ✅ required |
| Degenerate but parseable validity | ✅ present | ✅ required |
| Format-limited validity | ✅ present | ✅ required |

#### D) Spatial reference and geographic coverage

| Category | Current coverage (core vector) | Target |
|---|---:|---:|
| North pole | ✅ present | ✅ required |
| South pole | ✅ present | ✅ required |
| Equator | ✅ present | ✅ required |
| EPSG:3857 | ✅ present | ✅ required |

#### E) Edge-case categories

| Category | Current coverage (core vector) | Target |
|---|---:|---:|
| Antimeridian/dateline | ✅ present | ✅ required |
| CRS mismatch/reprojection | ✅ present | ✅ required |
| Topology defects | ✅ present | ✅ required |
| Schema/encoding issues | ✅ present | ✅ required |
| Empty/null geometry behavior | ✅ present | ✅ required |
| Precision/rounding artifacts | ✅ present | ✅ required |
| Multipart dissolve/overlay behavior | ✅ present | ✅ required |

#### F) Minimum target policy per matrix cell

- For each supported geometry type × format combination: at least one valid baseline fixture.
- For each geometry family: at least one complex fixture and one invalid/pathological fixture.
- Include explicit coverage for ambiguous / engine-dependent, degenerate but parseable, and format-limited validity cases.
- Include explicit coverage for north pole, south pole, equator, and `EPSG:3857` scenarios.
- For each edge-case category: at least one targeted fixture with explicit `risk_types` and assertions.
- For each non-GeoJSON format (`GPKG`, `Shapefile`, `Parquet`, `GML`, `KML`, `CSV_WKT`, Feather/Arrow variants, `WKB`, `WKT`, `SQLite`, `FlatGeobuf`): at least one schema/encoding-focused or format-limited fixture.

#### G) Phase 2 re-baselined gaps

Use the live tree under `src/geocase/data/core/vector/` as the source of truth for this checklist.

| Axis | Gap id | Current status | Planned case id(s) |
|---|---|---|---|
| Format-specific | `parquet_mixed_schema_attributes` | ✅ covered in live catalog | `parquet_mixed_schema_attributes` |
| Format-specific | `format_limited_kml_case` | ✅ covered in live catalog | `format_limited_kml_case` |
| Spatial complement | `north_pole_polygon` | ✅ covered in live catalog | `north_pole_polygon` |
| Spatial complement | `south_pole_polygon` | ✅ covered in live catalog | `south_pole_polygon` |
| Spatial complement | `equator_polygon` | ✅ covered in live catalog | `equator_polygon` |
| CRS refinement | `web_mercator_precision_case` | ↩️ deferred past v1.0 | `web_mercator_precision_case` |
| Null-vs-empty semantics | `null_geometry_row_gpkg` | ✅ covered in live catalog | `empty_geometry_gpkg` |
| Release policy | `matrix-completeness-v1` | ↩️ deferred past v1.0 | `geometrycollection_followups`, `columnar_format_followups` |

# Empty Geometry in GeoPackage Case

## Purpose

This case tests the distinction between NULL and EMPTY geometries in GeoPackage
format. This is a critical edge case that many loaders handle incorrectly.

## Problem Demonstrated

GeoPackage (SQLite-based) distinguishes two "missing geometry" states:

| State | SQL Value | WKB Representation | Meaning |
|-------|-----------|-------------------|---------|
| NULL | `NULL` | No value stored | "No geometry recorded" |
| EMPTY | WKB blob | `POINT EMPTY` (7 bytes) | "A point with no coordinates" |

## Why This Matters

Different operations behave differently with NULL vs EMPTY:

| Operation | NULL Geometry | EMPTY Geometry |
|-----------|--------------|----------------|
| `IS NULL` check | TRUE | FALSE |
| Spatial index | Not indexed | May be indexed |
| `ST_IsEmpty()` | NULL (or error) | TRUE |
| Bounds calculation | Excluded | Zero-area bounds |
| Export to GeoJSON | `null` or omitted | `{"type": "Point", "coordinates": []}` |

## Test Data

This GeoPackage contains 4 rows:

| Row | ID | Geometry | State |
|-----|------|----------|-------|
| 1 | valid_1 | POINT(10 50) | Valid geometry |
| 2 | valid_2 | POINT(11 51) | Valid geometry |
| 3 | null_row | SQL NULL | NULL geometry |
| 4 | empty_row | POINT EMPTY | EMPTY geometry |

## Expected Behavior

- Loaders should successfully read all 4 rows
- NULL and EMPTY geometries should be distinguishable
- Spatial operations should handle both states correctly
- Export should preserve the NULL/EMPTY distinction

## Format-Specific Behavior

| Format | NULL Support | EMPTY Support | Notes |
|--------|-------------|---------------|-------|
| GeoPackage | Yes (SQL NULL) | Yes (WKB EMPTY) | Full distinction |
| Shapefile | No (all NULL) | Sort of | No true NULL, empty = deleted |
| GeoJSON | Yes (`null`) | Yes (`[]` coords) | Spec allows both |
| WKT | No | Yes (`POINT EMPTY`) | NULL not representable |

This case is **GeoPackage-specific** because of SQLite's explicit NULL handling.

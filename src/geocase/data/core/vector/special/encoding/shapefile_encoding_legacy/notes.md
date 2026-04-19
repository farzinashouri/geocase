# Shapefile Legacy DBF Encoding Case

## Purpose

This case tests handling of legacy code page encoding in Shapefile DBF files.
Many older Shapefiles use Windows-1252 (CP1252) or other code pages instead
of UTF-8 for text attributes.

## Problem Demonstrated

Shapefile encoding handling is complex:

1. **No standard encoding**: DBF files don't have a built-in encoding declaration
2. **Code page files**: The optional `.cpg` sidecar file specifies encoding
3. **Legacy defaults**: Many tools assume a system default (often Windows-1252)
4. **Mojibake risk**: UTF-8 assumption on CP1252 data corrupts characters

## Test Data

City names with special characters encoded in Windows-1252:

| City | Characters | Encoding Challenge |
|------|------------|-------------------|
| Zürich | ü (0xFC) | German umlaut |
| Köln | ö (0xF6) | German umlaut |
| Malmö | ö (0xF6) | Swedish character |
| São Paulo | ã (0xE3) | Portuguese tilde |

## Expected Behavior

### With `.cpg` file present (this case)

- Loaders should detect Windows-1252 encoding from `.cpg` file
- Characters should render correctly without mojibake
- Attribute values should match expected strings

### Without `.cpg` file

- Behavior varies by loader and platform
- May produce mojibake (e.g., "ZÃ¼rich" instead of "Zürich")
- Some loaders attempt encoding detection heuristics

## Format-Specific Behavior

This edge case is **specific to Shapefile/DBF format**:

- GeoJSON mandates UTF-8
- GeoPackage uses SQLite's UTF-8 text handling
- Parquet/Arrow use UTF-8 by default

Shapefile's lack of encoding standardization makes it a common source of
internationalization bugs in geospatial workflows.

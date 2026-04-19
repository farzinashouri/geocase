# Shapefile Field Name Truncation Case

## Purpose

This case tests Shapefile's 10-character field name limitation. The DBF format
used by Shapefiles restricts field names to 10 characters, which causes
truncation when longer names are used.

## Problem Demonstrated

When writing data with long field names to Shapefile format:

1. **Truncation**: Field names longer than 10 characters are silently truncated
2. **Collision**: Truncation can cause multiple fields to have the same name
3. **Data Loss**: Some drivers may drop or rename colliding fields

## Original vs Truncated Field Names

| Original Name | Truncated | Notes |
|---------------|-----------|-------|
| `temperature_celsius` | `temperatur` | Truncated at 10 chars |
| `temperature_fahrenheit` | `temper_1` | Renamed to avoid collision |
| `precipitation_mm` | `precipitat` | Truncated at 10 chars |
| `wind_speed_knots` | `wind_speed` | Exactly 10 chars, no truncation |

## Expected Behavior

- Loaders should successfully read the file
- Attribute inspection should reveal truncated/renamed field names
- Roundtrip tests should detect field name changes
- Schema validation should flag the truncation if comparing against original schema

## Test Scenarios

1. **Load and inspect**: Verify file loads and geometry is valid
2. **Field name check**: Compare loaded field names against expected truncated names
3. **Roundtrip warning**: If re-exporting to Shapefile, verify no additional truncation occurs
4. **Cross-format comparison**: Compare against GeoJSON version with original field names

## Format-Specific Behavior

This edge case is **unique to Shapefile format** due to the DBF specification.
Other formats (GeoJSON, GPKG, Parquet) do not have this limitation.

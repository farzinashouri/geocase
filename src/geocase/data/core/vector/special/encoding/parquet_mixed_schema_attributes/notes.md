# parquet_mixed_schema_attributes

## Purpose

This case tests Parquet/GeoParquet's native nullable type support with a
deliberately mixed attribute schema.

## Schema details

| Column        | Arrow type       | Nulls? | Notes                               |
|---------------|------------------|--------|-------------------------------------|
| `id`          | `int64`          | No     | Simple non-null integer identifier  |
| `name`        | `string`         | Yes    | Row 3 is null                       |
| `value_int`   | `Int64` (nullable) | Yes  | Row 2 is null — tests nullable int  |
| `value_float` | `float64`        | Yes    | Row 4 is NaN                        |
| `is_active`   | `boolean` (nullable) | Yes | Row 3 is null                      |
| `tags`        | `string`         | Yes    | Row 3 is null; CSV-in-string values |
| `geometry`    | `Point`          | No     | 4 valid WGS 84 points              |

## What this case catches

- Loaders that silently cast `Int64` (nullable) → `float64` (losing the
  integer/null distinction).
- Loaders that drop or coerce nullable `boolean` columns.
- Loaders that conflate `None` (null string) with empty string `""`.
- Schema round-trip failures when writing back to Parquet.

## Geometry

Four simple WGS 84 points along a NE diagonal across northern Europe.

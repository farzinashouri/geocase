# MultiLineString CSV WKT Baseline

## Purpose
Tests MultiLineString geometry loading from CSV with WKT geometry column.

## Data
- WKT: `MULTILINESTRING ((0 0, 1 1), (2 2, 3 3))`
- Attributes: id, name, value

## Validation
- Geometry type: MultiLineString
- Feature count: 1
- Note: CSV format does not preserve CRS

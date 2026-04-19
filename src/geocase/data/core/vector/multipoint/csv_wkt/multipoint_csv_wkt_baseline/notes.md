# MultiPoint CSV WKT Baseline

## Purpose
Tests MultiPoint geometry loading from CSV with WKT geometry column.

## Data
- WKT: `MULTIPOINT ((0 0), (1 1), (2 2))`
- Attributes: id, name, value

## Validation
- Geometry type: MultiPoint
- Feature count: 1
- Note: CSV format does not preserve CRS

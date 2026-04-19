# MultiPolygon CSV WKT Baseline

## Purpose
Tests MultiPolygon geometry loading from CSV with WKT geometry column.

## Data
- WKT: `MULTIPOLYGON (((0 0, 1 0, 1 1, 0 1, 0 0)), ((2 2, 3 2, 3 3, 2 3, 2 2)))`
- Attributes: id, name, value

## Validation
- Geometry type: MultiPolygon
- Feature count: 1
- Note: CSV format does not preserve CRS

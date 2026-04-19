# Polygon CSV WKT Baseline

## Purpose
Tests Polygon geometry loading from CSV with WKT geometry column.

## Data
- WKT: `POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))`
- Attributes: id, name, value

## Validation
- Geometry type: Polygon
- Feature count: 1
- Note: CSV format does not preserve CRS

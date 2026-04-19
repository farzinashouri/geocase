# Point CSV WKT Baseline

## Purpose
Tests Point geometry loading from CSV with WKT geometry column.

## Data
- Single point at (10, 52)
- Attributes: id, name, value
- WKT geometry in "geometry" column

## Validation
- Geometry type: Point
- Feature count: 1
- Note: CSV format does not preserve CRS

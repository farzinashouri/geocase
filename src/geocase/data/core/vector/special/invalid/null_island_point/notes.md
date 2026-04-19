# Null Island Point

## Purpose
Tests detection of suspicious (0, 0) coordinates that typically indicate geocoding failures.

## Background
"Null Island" is a colloquial name for the point at 0°N 0°E in the Atlantic Ocean.
It's become famous in GIS circles because it's where points end up when:
- Geocoding fails silently and returns null/undefined
- Null values are cast to 0.0 during data processing
- Default coordinate values are used as fallbacks

## Expected Behavior
- **Loaders**: Will load successfully (it's valid geometry)
- **Data quality checks**: Should flag as suspicious
- **Spatial analysis**: Should exclude or quarantine these points

## Detection Strategies
1. Exact match: `lon == 0.0 and lat == 0.0`
2. Tolerance: Within ~1km of (0, 0) to catch floating-point artifacts
3. Statistical: Anomaly detection for coordinate clustering at origin

## Real-World Occurrence
Extremely common in:
- Web scraping pipelines
- Batch geocoding with error suppression
- ETL processes with null coercion

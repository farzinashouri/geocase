# GeoJSON Precision Loss Roundtrip Case

## Purpose

This case tests coordinate precision preservation during GeoJSON text
serialization. GeoJSON uses decimal string representation for coordinates,
which can lose precision compared to binary IEEE 754 double representation.

## Problem Demonstrated

GeoJSON precision challenges:

1. **Text vs Binary**: Decimal text cannot exactly represent all floating-point values
2. **Serializer variance**: Different libraries use different default precision (6-15 digits)
3. **Cumulative drift**: Multiple read/write cycles can accumulate precision errors
4. **Comparison failures**: High-precision coordinate comparisons may fail unexpectedly

## Test Data

Three points with coordinates at IEEE 754 double precision limits:

| Point | Longitude | Latitude | Challenge |
|-------|-----------|----------|-----------|
| 1 | 10.123456789012345 | 50.987654321098765 | Full 15+ significant digits |
| 2 | -122.41941550000001 | 37.77492950000001 | Trailing digits from binary representation |
| 3 | 0.00000000000001 | 0.00000000000001 | Very small values near zero |

## Expected Behavior

- **First read**: Coordinates should load with maximum available precision
- **Roundtrip test**: Write then read should preserve coordinates within tolerance
- **Multi-cycle test**: N roundtrips should not accumulate unbounded drift

## Precision Tolerances

| Scenario | Tolerance |
|----------|-----------|
| Single roundtrip | 1e-14 (sub-nanometer at equator) |
| 10 roundtrips | 1e-12 (acceptable drift) |
| Format comparison | Binary formats (GPKG, WKB) should preserve full precision |

## Format-Specific Behavior

This is a **GeoJSON-specific edge case**:

- **GeoJSON**: Text serialization, precision depends on serializer settings
- **GeoPackage**: SQLite BLOB storage, full IEEE 754 precision
- **WKB**: Binary format, full IEEE 754 precision
- **Shapefile**: Double precision in SHP file, full IEEE 754 precision

GeoJSON's human-readable text format trades some precision for readability.

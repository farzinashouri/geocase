# format_limited_kml_case

## Purpose

This case demonstrates inherent limitations of the KML format when used
to store vector data with typed attributes.

## KML format limitations exercised

1. **All attributes become strings.** KML `<SimpleField>` supports
   `type="string"`, `type="int"`, `type="float"`, etc., but in practice
   most KML producers and the OGR/GDAL KML driver store everything as
   strings. After a round-trip through KML, `population=15000` (int)
   becomes `"15000"` (string).

2. **Coordinates are always WGS 84.** KML mandates EPSG:4326. Data in
   other CRSs must be reprojected before writing to KML.

3. **Z coordinates are included.** Even 2D polygons get `0` as a Z
   value in KML coordinates, producing `POLYGON Z` geometries on
   read-back.

4. **No native null support.** Missing attribute values can only be
   represented as empty strings or by omitting the `<SimpleData>` tag
   entirely, which loaders may interpret differently.

## Schema details

| Attribute    | Original type | KML round-trip type | Notes                        |
|-------------|---------------|---------------------|------------------------------|
| `population` | `int`         | `string`            | "15000" not 15000            |
| `area_km2`   | `float`       | `string`            | "89.123456789" as text       |
| `is_urban`   | `bool`        | `string`            | "true"/"false" as text       |
| `category`   | `string`      | `string`            | Unchanged — already a string |

## What this case catches

- Code that does arithmetic on KML attributes without explicit type
  casting (e.g. `gdf["population"].sum()` returns string concatenation).
- Cross-format converters that silently assume attribute types are
  preserved through KML.
- Loaders that treat KML `type="int"` schema hints as authoritative
  when the actual values are strings.

## Geometry

Three simple WGS 84 polygons (rectangular zones) across northern Europe.

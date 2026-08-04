# Dataset Catalog

What data GeoCase actually ships, why those formats were chosen, and where on Earth the
cases put a coordinate in order to exercise a specific geodetic path.

This page is the reasoning. The enumeration lives next door, generated from the catalog
itself and gated in CI: the [case catalog](_generated/catalog/index.md) lists every case
with its properties, and the coverage matrices roll the same data up by axis
([vector](_generated/vector-coverage-matrix.md),
[raster](_generated/raster-coverage-matrix.md)). If a table here and a generated table
ever disagree, the generated one is right.

!!! note "All bundled data is synthetic"

    Every bundled case is `geocase-curated` or `geocase-synthetic`. No case carries a real
    provenance URL or an imaging agency, and nothing here depicts a real acquisition.
    Coordinates are **nominal** — chosen to put data into a geodetic *condition* (a UTM
    zone exception, a meridian convergence, an antimeridian split), not to represent a
    place. Read the map below as "conditions tested", never as "places imaged".

## At a glance

| | Count |
|---|---:|
| **Total bundled cases** | **134** |
| Vector | 103 |
| Raster | 30 |
| NetCDF | 1 |
| Declared remote (not fetchable) | 7 |

Bundled payload is **4.2 MB** across 16 formats. Every bundled case is `storage_class:
bundled` and ships inside the wheel; 133 are `size_class: tiny` and one is `small`. By
test tier: 117 `unit`, 17 `integration`.

The seven remote cases are *declared*, not available — see
[Remote and non-bundled](#remote-and-non-bundled).

## Why these formats

Formats are not collected for completeness. Each one earns its place by being the shortest
path to a failure mode that the others cannot produce.

| Format | What it represents | The failure mode it uniquely exposes |
|---|---|---|
| **GeoJSON** (37) | The lingua franca of web geospatial | Coordinate precision loss on roundtrip; CRS is *always* WGS84 by spec, so a reprojection bug has nowhere to hide |
| **GeoTIFF** (30) | The raster baseline | Everything raster: dtype, nodata convention, transform, band count, overviews |
| **Shapefile** (8) | The format that refuses to die | DBF 10-character field-name truncation and code-page encoding — both silent, both data-destroying |
| **GPKG** (8) | The modern OGC container | SQL container semantics; the distinction between a NULL row and an empty geometry |
| **KML** (7) | Consumer/visualization exchange | Forced WGS84 regardless of source CRS, and string-only ExtendedData that flattens every numeric type |
| **CSV_WKT** (6) | Geometry smuggled through a spreadsheet | No CRS anywhere in the file — the reader must be told, or must guess |
| **WKB** (6) | The binary interchange primitive | Byte-order and geometry-type parsing, with no metadata envelope at all |
| **WKT** (6) | The text interchange primitive | Precision-by-formatting, and CRS-less serialization |
| **GML** (6) | The OGC/INSPIRE XML lineage | Axis-order ambiguity — the classic lat/lon versus lon/lat inversion |
| **SQLite / SpatiaLite** (6) | Spatial SQL outside GPKG | Driver-specific behavior distinct from GPKG despite the shared container |
| **FlatGeobuf** (6) | Streamable, indexed binary | Spatial-index assumptions and a schema fixed by the first feature |
| **Parquet** (3), **Feather** (2), **Arrow** (1), **GeoArrow** (1) | Columnar analytics | Nullable-dtype downcast — a nullable integer column silently becoming float, and null/empty conflation |
| **NetCDF** (1) | Multidimensional scientific arrays | Dimension ordering and the CF conventions, where the CRS is an attribute rather than a header |

The columnar family is deliberately sparse rather than a full matrix: those formats are
covered where the nullable-dtype path differs, not for every geometry type. The holes are
visible in the [vector coverage matrix](_generated/vector-coverage-matrix.md) and listed
below.

## Vector datasets

103 cases, in three groups.

### The geometry × format baseline (66)

Six geometry types — Point, MultiPoint, LineString, MultiLineString, Polygon,
MultiPolygon — each written into the eleven formats that support them: GeoJSON, GPKG,
Shapefile, KML, GML, SQLite, WKB, WKT, CSV_WKT, FlatGeobuf, and one columnar format each
where applicable.

The columnar coverage is intentionally partial, and the holes are the interesting part:

| Format | Geometries covered | Why not all six |
|---|---|---|
| Parquet | Polygon, MultiLineString (+1 encoding case) | The nullable-dtype path does not vary by geometry type |
| Feather | Point, MultiPoint | Same Arrow memory model as Parquet; two geometries prove the IPC path |
| Arrow | Point | Proves the in-memory IPC stream distinct from the file formats |
| GeoArrow | LineString | Proves the geoarrow encoding, where coordinates are native columns rather than serialized blobs |

All six baseline geometries sit in western/central Europe at low precision, which keeps
them readable in a diff: the Point baseline is a single vertex at **12.5°E, 55.7°N**
(Copenhagen), and the other five occupy a small box around **10–11.5°E, 49.8–51°N**. The
locations carry no meaning — these cases test serialization, not geodesy.

### `special/` edge cases (36)

Eight families, each targeting one failure mode. Full properties for every id are on the
[case catalog](_generated/catalog/index.md); the geodetic rationale is under
[Where in the world we test](#where-in-the-world-we-test).

| Family | Count | What it exercises |
|---|---:|---|
| `crs` | 11 | UTM zone selection, polar degeneracy, equator crossing, Web Mercator, rasterize alignment across CRS |
| `dateline` | 6 | Antimeridian splitting, longitude wrapping past ±180, transitive cluster splits |
| `invalid` | 6 | Self-intersection, unclosed rings, spikes, out-of-range coordinates, Null Island |
| `encoding` | 5 | Shapefile field truncation and code pages, KML type flattening, mixed attribute schemas |
| `precision` | 3 | Coordinate drift, near-duplicate clustering, format-imposed precision limits |
| `empty` | 2 | Empty geometry versus NULL geometry |
| `degenerate` | 2 | Zero-length lines, disjoint multi-part geometry |
| `holes` | 1 | Interior rings and ring-ordering |

### GeometryCollection (1)

`geometrycollection_mixed_valid` — a single case, because mixed-type collections are where
format support diverges most sharply: several formats in the table above cannot represent
one at all.

## Raster datasets

30 GeoTIFFs, in four groups.

**Product families (17)** — optical RGB, Sentinel-2-like multispectral, mixed-resolution
multispectral, COG (single-band and multispectral), SAR (VV and dual-pol), DEM (sentinel
and NaN nodata), NDVI (float and scaled int16), landcover, water mask, external overviews,
and the equator/dateline/polar optical trio. These carry the realistic band counts, dtypes
and nodata conventions that the dtype family isolates.

**Dtype family (5)** — `int8`, `int16`, `int32`, `float64`, and a 3-band `float32`, all
10×10 at the same origin. Isolating dtype from every other variable is the point: see
[Raster dtypes and radiometric resolution](contributing/raster-dtypes-and-radiometric-resolution.md).

**Nodata / alignment / CRS family (3)** — `geotiff_nodata_small` and its deliberately
shifted twin (origin moved 1000 m east, same grid) expose off-by-one-pixel alignment
assumptions; `geotiff_utm_boundary` spans a 20 km extent at a zone edge.

**Footprint edge cases (5)** — all-valid, a nodata hole in the centre, a sparse diagonal on
a non-square grid, two disjoint islands, and a thin corridor. These test footprint and
validity-mask derivation, where an algorithm that assumes a rectangular valid region fails.

Nodata conventions vary on purpose: `-9999` sentinel, `0`, `255`, `-32768`, and NaN all
appear, because reading a NaN convention as a sentinel is a real and silent bug.

## NetCDF

`latlon_small` — one case. It exists so the CF-conventions path, where the CRS is an
attribute rather than a file header, is exercised at least once.

## Remote and non-bundled

Two manifests under `extended-manifests/` declare seven cases that are **not fetchable**.
Every `sha256` is the literal `replace_me`, every `base_uri` points at `example.org`, and
nothing has ever been published. Transport is deliberately deferred to v1.1; see
[Remote datasets](remote-datasets.md) for the discovery API and the errors these cases
raise.

| Manifest | Case ID | Declared size | Bundled analog |
|---|---|---:|---|
| `satellite-scenes` | `optical_rgb_scene` | 48 MB | `optical_rgb_small` |
| `satellite-scenes` | `multispectral_s2_scene` | 260 MB | `multispectral_s2_like_small` |
| `satellite-scenes` | `sar_vv_scene` | 180 MB | `sar_vv_small` |
| `satellite-scenes` | `dem_scene` | 62 MB | `dem_small` |
| `satellite-scenes` | `landcover_scene` | 34 MB | `landcover_small` |
| `public-extended` | `coastal_scene_small` | 1.3 MB | — |
| `public-extended` | `utm_boundary_scene` | 1.5 MB | — |

The `bundled_analog` mapping is the useful part today: each remote scene names the bundled
case that exercises the same code path at 1/1000th the size. Five of the seven have one,
which means a test written against a bundled analog will keep working when transport
lands.

## Where in the world we test

!!! note "Coordinates are conditions, not places"

    Nothing below was imaged anywhere. Each cluster exists because a specific coordinate
    puts the data into a geodetic condition that breaks a specific naive implementation.

```
    -180  -150  -120   -90   -60   -30    0    30    60    90   120   150   180
      +-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
  90N |                                   E                                   |
      |                        . _  .-.        _.-"""-._     G                |
  60N |            .-"""-.__.-"      "-._.-""""          "-.__.-"     _.-.    |
      |         .-"     C      B  A  .                        .    .-"    "-. |
  30N |        (      _.       F  D  |         _                  (          )|
      |         "-._-"          |    \      .-" "-.                "-.    _.-"|
   0  |             \           H---------------------H              \  _.-"  |
      |              "-._      /     \     "._      _."               "-"     |
  30S |                  "-.__/       "-.__.-" "-.-"                          |
      |                       \          |                                    |
  60S |                        "-._      /                                    |
      |                            "----"                                     |
  90S |                                   F                                   |
      +-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
```

Markers are approximate to the nearest cell; the table carries the real coordinates.

| Marker | Cluster | Coordinates | CRS involved | Cases | Why this spot |
|---|---|---|---|---:|---|
| **A** | Central Europe baselines | 10–11.5°E, 49.8–51°N | EPSG:4326 | 65 | No geodetic significance. Round numbers at low precision so a serialization diff is readable by eye. |
| **A** | Copenhagen | 12.5°E, 55.7°N | EPSG:4326 | 1 + precision cluster | The Point baseline and the near-duplicate cluster at 12°E, 55°N, where coordinate drift shows up in the sixth decimal. |
| **B** | UTM 33N synthetic tile | 15°E, **40.65°N** (500000 E, 4500000 N) | EPSG:32633 | 15 | The false-easting origin of zone 33N. Most rasters live here. Note the *northing* implies southern Italy, not Scandinavia — the tile is nominal. |
| **B** | UTM 33N northern band | 15°E, 50.5°N (500000 E, 5.6e6 N) | EPSG:32633 | 3 | The nodata/shifted pair and the zone-boundary raster, one northing band north of the main tile. |
| **C** | Svalbard | 19.5–20.5°E, 77.5–78.5°N | EPSG:4326 → UTM | 1 | **Zone 33X is a hand-carved exception.** The naive `floor((lon + 180) / 6) + 1` returns zone 34 here and is wrong. This is the single highest-value coordinate in the catalog. |
| **D** | Czechia | 14.9–15.1°E, 50.58–50.70°N | EPSG:4326 + EPSG:32633 | 2 | The rasterize-match pair: the same polygon in geographic and projected CRS, so grid alignment across a reprojection can be asserted. |
| **E** | North Pole | 0°E, 90°N; 84–89.5°N band | EPSG:4326 | 2 | Meridian convergence makes area and centroid degenerate, and longitude becomes undefined at the point itself. |
| **F** | South Pole | 0°E, −90°N; −89.5 to −84°N band | EPSG:4326 | 2 | The southern mirror. Also the only bundled geometry south of the equator. |
| **G** | Antimeridian | ±179–190°E, 0–50°N | EPSG:4326 | 6 + 1 raster | Splits UTM 32601/32660 and breaks every naive bbox, which computes a min/max spanning the whole globe the wrong way round. Includes `wrapped_longitude_point` at a literal 190°E — valid input that many readers silently accept and never normalize. |
| **H** | Equator | −30 to 30°E, ±1–5°N | EPSG:4326 | 2 + 1 raster | Hemisphere-boundary arithmetic and the sign flip in northing. |
| **H** | Null Island | 0°E, 0°N | EPSG:4326 | 1 | The geocoding-failure sentinel. A pipeline that emits (0, 0) on parse failure is indistinguishable from one that succeeded, unless something tests for it. |
| — | Web Mercator baseline | 1000000, 1000000 m (≈ 8.98°E, 8.95°N) | EPSG:3857 | 1 | Metres mistaken for degrees is a common bug; these coordinates make it obvious. |
| — | Arctic stereographic | −2000000, 2000000 m (≈ 135°W, **64.4°N**) | EPSG:3995 | 1 | `optical_polar_small` exercises the polar stereographic *projection*, though its extent lands at 64°N rather than near the pole. |
| — | Nominal-origin tiles | 500000 E, ~1000 N | EPSG:32633 | 8 | The dtype family and two footprint cases sit at near-zero northing, which is nominally on the equator. The origin is a placeholder — these cases test dtype and footprint, not location. |

Attribute values carry one more geography: the encoding cases use European city names
(Zürich, Köln, Malmö, São Paulo) to exercise code pages and non-ASCII field content. São
Paulo is the only southern-hemisphere value anywhere in the catalog, and it is a string,
not a coordinate.

### Coverage gaps

Stated plainly, because a gap on a list is more useful than a placeholder in the wheel:

- **No southern-hemisphere UTM geometry.** Every projected case uses a northern zone. The
  false-northing of 10,000,000 m that southern zones apply is untested.
- **No southern-hemisphere raster.** Same gap, on the raster side.
- **Nothing in Asia, Africa, Australia, or the Americas.** Every coordinate is European,
  polar, or on a meridian/equator line.
- **No case near the UTM validity limits** (84°N / 80°S), where the projection stops being
  defined and a reader must fall back to UPS.
- **No Norway zone-32V exception.** The catalog covers the Svalbard 33X exception but not
  the other hand-carved one, and an implementation can pass 33X while failing 32V.
- **No rotated or skewed affine transform, and no non-square pixels.** Tracked for v1.1;
  the `affine_transform_quirk` stub that once claimed this coverage was deleted rather
  than left implying a commitment it did not keep.

## See also

- [Case discovery](case-discovery.md) — filtering and selecting cases through the API.
- [Adding a case](adding-a-case.md) — authoring a new one.
- [Testing edge cases](contributing/testing-edge-cases.md) — the reasoning behind the
  `special/` families.
- [Remote datasets](remote-datasets.md) — the manifest surface and its current limits.

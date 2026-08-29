# Dense Ring Polygon (4096 vertices, GeoPackage)

The geometry is identical to `dense_ring_polygon_4k` -- the same `_dense_parametric_ring(vertices=4096, lobes=17, amplitude=0.18)`
output -- written here through the GDAL GeoPackage driver instead of as JSON
text.

## Why both

The GeoJSON form proves the coordinate list survives *serialization*; this one
proves it survives a **driver**. Those fail differently. A 4096-vertex ring in
a GeoPackage is a single binary WKB blob inside a SQLite BLOB column, so what
gets tested here is the writer's geometry buffer, the blob column's handling of
a payload well past the small-value fast path, and the reader's WKB parse --
none of which the text form touches.

Despite sharing a geometry with another case, this is **not** a member of the
cross-format transcoding family: it declares no `canonical_source_case_id` and
carries no `cross_format_canonical` tag, because that family's canonicals are
hand-authored single-feature GeoJSON files and this geometry is generated. The
`--check` gate covers it through `_procedural_specs()` instead.

# Invalid Geometry at Feature 9,999 (GeoPackage)

10,000 polygons on a regular lattice. The first 9,999 are valid triangles; the
last is a self-intersecting bowtie.

## Why the position is the case

Every other invalid-geometry case in the catalog holds one or two features, so
the invalid one is also the first one. That makes them useless for the question
this case asks: *did the consumer validate the dataset, or the first page of
it?* With one feature there is no difference between the two, and a probe that
cannot fail is a probe that terminates a search with a false green.

Index 9,999 is past every batch boundary a reader is likely to have. Any read
of a prefix — one batch, a head sample, a paged sweep that stops early —
reports the layer fully valid, and only a full read finds the defect.

## The geometry is deliberately boring

A lattice of identical triangles, not a realistic landscape. The bowtie is the
only interesting thing in the file, so a finding here cannot be confused with a
geometric quirk somewhere else in the data. Nothing overlaps: the triangles are
0.003° across on a 0.005° grid.

The bowtie itself is the classic form — the ring's second and fourth vertices
swapped, so its two edges cross at the centre. GEOS, GDAL and PostGIS agree it
is invalid, which matters: a case whose invalidity is engine-dependent tests
the engine rather than the consumer. That is what
`ambiguous_engine_dependent_polygon` is for.

## Generated, not committed

Built by `scripts/generate_vector_fixtures.py` (`_large_specs`), so it is
covered by the `--check` regeneration gate. `hole_center_nodata` drifted into
the exact inverse of its own description precisely because it was hand-written
and sat outside that gate.

The feature count comes from `params.expected_feature_count` in `case.yaml`, so
the number the generator writes and the number the content gate checks cannot
disagree.

## Size

1.4 MB, written with `SPATIAL_INDEX=NO`. The R-tree would add roughly 750 KB —
more than half the payload again — to accelerate a query no case here performs.
The R-tree is covered deliberately by the SpatiaLite cases, at one feature each.

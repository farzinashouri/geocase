# Spike Invalid Polygon

This polygon contains a self-touching spike. `make_valid` typically repairs it
into a mixed `GeometryCollection` with one polygon and one linear artifact,
which is useful for testing whether repair helpers keep only polygonal output.

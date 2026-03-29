# Self Intersecting Polygon

## Purpose

Deliberately invalid polygon (self-intersection) used to ensure validation and
topology checks catch bad geometry.

## What to expect

- Dataset should still load.
- OGC validity should fail.
- Topology-focused checks should report a self-intersection.

## Typical checks

- `assert_invalid_geometry(gdf)`
- `assert_no_self_intersections(gdf)` should fail
- `assert_matches_vector_hints(case, gdf)` should pass because
	`expect_valid_geometry: false`

## Common failure modes

- Pipelines silently accepting invalid geometry.
- Downstream area/centroid calculations returning misleading values.

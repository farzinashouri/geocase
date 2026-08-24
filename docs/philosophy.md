---
description: "Why GeoCase ships curated test cases rather than sample files: realistic enough to reveal real bugs, small enough to run and maintain in CI."
---

# Philosophy

GeoCase is built around one idea:

> geospatial tests should be realistic enough to reveal real bugs,
> but small enough to be easy to run and maintain.

## Why GeoCase exists

Spatial systems often fail in places where toy examples look fine:

- dateline crossing
- CRS mismatch
- invalid topology
- raster nodata handling
- UTM boundary assumptions
- encoding issues in attributes
- geometry collections and multipart features

Developers usually solve this by accumulating random local samples, but those files are hard to discover, hard to explain, and hard to reuse consistently.

GeoCase replaces that with a catalog of explicit test cases.

## A case is more than a file

A GeoCase case includes:

- the sample data
- metadata explaining its risk
- intended behavioral goal
- loader hints
- assertions and expected capabilities
- suitability for unit, integration, slow, or remote testing

## Why parameterized tests are central

GeoCase is not mainly a data dump. It is a catalog designed to feed parameterized tests.

Instead of writing many handpicked tests with hardcoded paths, a user should be able to say:

- all vector unit cases
- all CRS edge cases
- all raster nodata cases
- all antimeridian cases

and run them through one reusable test function.

## Bundled versus remote

GeoCase keeps the packaged core intentionally small.

- **Bundled** cases are tiny and fast.
- **Remote** cases are fetched on demand.
- **Private** cases are user- or organization-specific.

This keeps the open toolkit practical while allowing richer real-world testing.


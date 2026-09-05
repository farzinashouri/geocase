---
description: "Why GeoCase ships curated test cases rather than sample files: realistic enough to reveal real bugs, small enough to run and maintain in CI."
---

# Philosophy

GeoCase is built around one idea:

> geospatial tests should be realistic enough to reveal real bugs,
> but small enough to be easy to run and maintain.

## Why GeoCase exists

Spatial systems often fail in places where toy examples look fine. Most of them are
georeferencing and geometry assumptions — where the code believes a pixel or a vertex is:

- rotated geotransforms, where the shortcut inverse matrix is wrong and quiet about it
- bottom-up rasters with a positive `e` term
- pixel-is-area versus pixel-is-point anchoring
- dateline crossing, and footprints that never got split
- CRS mismatch, and EPSG axis order
- UTM boundary assumptions
- invalid topology
- raster nodata handling
- encoding issues in attributes
- geometry collections and multipart features

Radiometric conventions — Sentinel-1 and Sentinel-2 scale factors, BOA offsets, dB
conversion, machine-checked against `geofacts` — are one vertical inside this, not the
centre of it.

Developers usually solve this by accumulating random local samples, but those files are hard to discover, hard to explain, and hard to reuse consistently.

GeoCase replaces that with a catalog of explicit test cases.

## Not only what you missed — what you got wrong

The obvious value of a corpus is coverage: it catches the case you forgot. That competes with
careful review, and careful review sometimes wins.

The less obvious value is the one worth building for. An external consumer running the
catalog against a production codebase reported:

> The fixtures didn't just catch what I missed — they corrected what I'd gotten wrong with
> confidence. That's a different and better product than coverage.

The case in question was `rotated_two_islands`. It **overturned a conclusion that reporter had
already committed to in writing** — an attribution made deliberately, reviewed, and wrong.
No amount of re-reading the source produces that, because re-reading the source is exactly
what produced the confident wrong answer. Only a file whose correct behaviour was decided by
someone else does.

That is the standard a case is designed against: not "would a careful reader miss this?" but
"could a careful reader be confidently wrong about this?"

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


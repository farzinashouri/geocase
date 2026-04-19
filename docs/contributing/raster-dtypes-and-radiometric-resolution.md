# Raster Dtypes and Radiometric Resolution

This note explains why the Phase 3 roadmap item
`Different dtypes (int8, int16, int32, float32, float64)` is **related to**
radiometric resolution but should not be read as **only** a radiometric
resolution concern.

---

## Short Version

Raster `dtype` describes the numeric storage type used for pixel values.
Radiometric resolution describes how finely a raster can represent
measurement levels.

These concepts overlap, but they are not identical.

- `dtype` is an implementation and behavior detail
- radiometric resolution is a measurement-detail concept
- GeoCase needs to test both the representational limits **and** the numeric
  behavior that different dtypes introduce

---

## What Is Raster `dtype`?

A raster dtype is the on-disk and in-memory numeric type used for each pixel.
Examples include:

- `int8`
- `int16`
- `int32`
- `float32`
- `float64`

In practice, dtype affects:

- the range of values that can be stored,
- whether values are signed or unsigned,
- whether fractional values are allowed,
- whether arithmetic can overflow or truncate,
- how NoData is encoded and interpreted,
- whether `NaN` is available.

For GeoCase, this means dtype is not just metadata — it changes how raster
algorithms behave.

---

## What Is Radiometric Resolution?

Radiometric resolution is the number of distinct intensity or measurement
levels a raster can represent.

Typical examples:

- 8-bit raster: $2^8 = 256$ levels
- 16-bit raster: $2^{16} = 65{,}536$ levels

This is often discussed in remote sensing because it affects how precisely a
sensor captures brightness, reflectance, temperature, or similar values.

Radiometric resolution is therefore about **measurement granularity**.

---

## How They Overlap

Dtype often constrains or enables radiometric resolution.

Examples:

- an 8-bit integer raster usually implies a relatively small set of possible
  values,
- a 16-bit integer raster supports far more distinct levels,
- a floating-point raster can represent continuous-valued outputs more
  naturally than an integer raster.

That is why the two ideas are related.

---

## Why They Are Not the Same Thing

Two rasters can have similar conceptual measurement intent but very different
runtime behavior because of dtype.

### Example 1: integer vs floating-point

A `float32` raster is not just a “higher radiometric resolution” raster.
It also supports:

- fractional values,
- `NaN`,
- different rounding behavior,
- different precision loss patterns than integers.

### Example 2: signed vs unsigned

A signed integer raster can store negative values.
That matters for:

- anomalies,
- temperature deltas,
- residual/error layers,
- some analysis outputs.

This is not primarily a radiometric-resolution issue; it is a numeric-range and
semantic-behavior issue.

### Example 3: overflow and casting

A raster-processing function may work on `float32` input but silently overflow,
clip, or truncate on `int8` or `int16` input.

That is a dtype-behavior concern even when the data concept is otherwise the
same.

---

## Why GeoCase Should Test Dtypes Explicitly

The roadmap item exists because raster functions often make hidden assumptions
about pixel storage.

Common failure modes include:

- assuming all rasters are `float32`,
- losing fractional precision when writing outputs,
- mishandling signed values,
- converting NoData incorrectly during casts,
- treating `NaN` and sentinel NoData values as interchangeable,
- performing statistics without considering integer overflow or float precision,
- changing dtype accidentally during clipping, masking, or reprojection.

A dtype test matrix helps catch those errors early.

---

## What the Phase 3 Bullet Means in Practice

In the roadmap, `Different dtypes (int8, int16, int32, float32, float64)`
should be read as:

> Add raster fixtures and tests that exercise different pixel storage types and
> their numeric behavior, not merely different bit depths.

That includes:

- integer vs floating-point handling,
- small-range vs large-range storage,
- signed vs unsigned expectations where relevant,
- sentinel NoData vs `NaN`,
- preservation of dtype through common raster operations.

---

## Suggested GeoCase Coverage Goals

For Phase 3, a practical dtype coverage set would validate that GeoCase users
can test functions against:

- **small integer raster** — catches clipping/overflow assumptions,
- **larger integer raster** — catches range assumptions,
- **floating-point raster** — catches precision and `NaN` behavior,
- **mixed NoData conventions** — sentinel values vs floating `NaN`,
- **dtype-preservation scenarios** — load, clip, sample, reproject, write.

This does not require an exhaustive matrix immediately. A few small curated
fixtures can provide high-value coverage.

---

## Recommended Wording for Planning Docs

If a plan needs to be more explicit, prefer wording like:

- `Different raster dtypes and numeric behaviors (int8, int16, int32, float32, float64)`

or

- `Different pixel storage types / radiometric precision scenarios`

The first wording is usually clearer for engineering work because it points
straight at the behavior we want to test.

---

## Bottom Line

Radiometric resolution is part of the story, but the roadmap item is broader.

For GeoCase, dtype coverage is really about ensuring raster-processing code is
robust across different numeric storage models, not just across different
sensor bit depths.

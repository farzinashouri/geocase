# UTC Offset Changes at Row 10,000 (GeoPackage)

10,001 points. The `observed` DATETIME column carries `2024-01-01T12:00:00.000`
at `+01:00` for the first 10,000 rows, and the same wall clock at `+05:30` for
the last.

## What it discriminates

GeoPackage stores DATETIME as ISO 8601 **text**, so both offsets survive on
disk exactly as written. A reader that infers a timezone from a head sample
finds one offset and fixes the column at it; a reader that scans the whole
column finds two and has to fall back to UTC.

Observed with pyogrio 0.12.1 / GDAL 3.12.2 on both code paths:

| read | dtype |
|---|---|
| `read_dataframe(path, max_features=100)` | `datetime64[ms, UTC+01:00]` |
| `read_dataframe(path)` | `datetime64[ms, UTC]` |

Both are correct answers to different questions, and both convert the instants
properly. The hazard is downstream: a consumer that builds a schema from a
sample and then reads the rest against it gets a tz-aware column whose type
does not match what it prepared for, and a consumer that *drops* the offset
rather than converting places the last observation 4.5 hours from where it
belongs.

## The file is deliberately GPKG-non-conformant

GeoPackage requirement 15 says DATETIME must be stored in UTC with a literal
`Z` suffix. A numeric offset like `+01:00` is valid ISO 8601 but violates that
requirement, and GDAL says so on read:

```
RuntimeWarning: Non-conformant content for record 1 in column observed,
2024-01-01T12:00:00.000+01:00, successfully parsed
```

This is the case's subject, not an oversight, and it was measured rather than
assumed. A **conformant** version of this file — the same two instants written
as `...11:00:00.000Z` and `...06:30:00.000Z` — shows **no dtype instability at
all**: partial and full reads both return `datetime64[ms, UTC]`, on both
pyogrio code paths. The divergence exists precisely because the offsets are
numeric.

So the honest framing is narrow: this case does not show that GPKG DATETIME
columns are unstable. It shows what happens when a consumer meets one of the
many real-world GeoPackages that ignore requirement 15 — the file still parses,
GDAL still warns, and the column's dtype now depends on how much of it was
read.

## Why 4.5 hours

`+05:30` against `+01:00` is deliberately not a whole number of hours and
deliberately far apart. A reader that discards the offset instead of converting
lands the last row on a visibly different UTC instant, so the failure is
observable rather than a relabelling nobody notices.

## Why the column is written as SQL text

No pandas dtype survives this. A `datetime64[ns, tz]` column holds exactly one
timezone by construction, and an object column of per-value `tzinfo` is
normalised to UTC by the writer — either way the mixed offset is gone before it
reaches the file. So the generator writes the rows through geopandas and then
sets `observed` with SQL, which is also how a real dataset acquires mixed
offsets: from a producer that recorded local time.

## Generated, not committed

Built by `scripts/generate_vector_fixtures.py` (`_large_specs`), under the
`--check` regeneration gate. `VACUUM` runs after the column is filled: an
`ALTER TABLE` plus 10,000 updates leaves enough free pages to inflate the file
by ~40%.

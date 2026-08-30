# First NULL After 10,000 Non-NULL Values (GeoPackage)

10,001 points. The `measure` column holds an integer for the first 10,000 rows
and NULL for the last.

## What it discriminates

A reader that types a column from a head sample sees 10,000 integers and says
integer. A reader that scans the column has to accommodate one missing value,
which in pandas means widening to float — so the *same column of the same file*
comes back with a different dtype depending on how much was read.

Observed with pyogrio 0.12.1 / GDAL 3.12.2 on both code paths:

| read | dtype |
|---|---|
| `read_dataframe(path, max_features=100)` | `int64` |
| `read_dataframe(path)` | `float64` |
| `read_dataframe(path, max_features=100, use_arrow=True)` | `int64` |
| `read_dataframe(path, use_arrow=True)` | `float64` |

This is documented pyogrio behaviour rather than a bug — but a consumer that
builds a schema from a sample and then reads the rest against it gets a type
mismatch it did not cause and cannot see in a small fixture. That is the
failure mode the case exists to make reachable.

## Why `Int64` on the write side

The column is built as pandas' nullable `Int64`, not `int64` or `float64`.
A numpy int column cannot hold the NULL at all, and a float column would put
the widening *in the fixture* — where it is the thing under test, not a
property of the data. `Int64` writes a genuine SQL NULL into an INTEGER column,
which is what a real dataset looks like.

## Generated, not committed

Built by `scripts/generate_vector_fixtures.py` (`_large_specs`), under the
`--check` regeneration gate. The feature count comes from
`params.expected_feature_count` in `case.yaml`, so the generator and the
content gate cannot disagree about the size.

Written with `SPATIAL_INDEX=NO`; see the sibling case's notes for why.

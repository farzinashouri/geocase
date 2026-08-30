# CF Time Units and Non-Conventional Dimension Order

## Purpose

One file carrying two related CF traps: a time axis stored as offsets from an
epoch, on a variable whose dimensions are **not** in the order most code
assumes.

`t2m` has dims `(longitude, latitude, time)` — x before y, time last. `time` is
`[0, 24, 48]` with `units = "hours since 2020-01-01 00:00:00"` and
`calendar = "gregorian"`.

## Why the two are combined in one fixture

Deliberately, and it is worth stating because the alternative looks tidier.

A `time` dimension has to go **somewhere** in the ordering. Any CF-time fixture
is therefore already making a dimension-order statement, whether or not it
declares one. Splitting these into two cases would produce two files that each
carry both properties while each declaring only one — which is precisely the
defect that got `coordinate_order` removed from `latlon_small`: a label with no
bytes behind it.

## What goes wrong

**Dimension order.** Code that assumes `(time, latitude, longitude)` and indexes
positionally — `values[0]` for "the first timestep", or a bare `.T` — gets a
transposed array. With a square grid it produces a plausible map of nothing; here
the shape is `(8, 5, 3)`, so it usually raises instead, which is the better
outcome and the reason the sizes differ.

**Time units.** Undecoded, the axis is `[0, 24, 48]` — three small integers that
mean nothing without the `units` attribute. Treated as timestamps, hours, or
indices, they all "work" and all give different answers:

```python
xarray.open_dataset(path, decode_times=False)["time"]  # [0, 24, 48]
xarray.open_dataset(path)["time"]                      # 2020-01-01, -02, -03
```

The values are one day apart, not one hour, which is what makes the mistake
visible if anyone checks.

## Typical checks

- `list(ds["t2m"].dims) == ["longitude", "latitude", "time"]`.
- Decoded times land on consecutive days in January 2020.
- `decode_times=False` returns the raw offsets and the `units` string.

## Related

`latlon_small` is the conventional counterpart: `(latitude, longitude)`,
no time axis. It used to declare `coordinate_order` and `dimension_mismatch`
without exercising either; those risk types now live here, on bytes that
demonstrate them.

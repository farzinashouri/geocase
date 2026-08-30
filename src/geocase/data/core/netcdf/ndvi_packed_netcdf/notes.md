# Packed int16 NDVI (NetCDF)

## Purpose

NDVI stored under the standard CF packing convention: `int16` on disk, with
`scale_factor = 1e-4` and `add_offset = 0.0`. The physical values span
`[-1, 1]`; the stored values span `[-10000, 10000]`.

## Why this is a trap and not just a format detail

The failure is **silent and plausible**. A reader that ignores `scale_factor`
does not crash and does not warn — it returns integers in the thousands, which
look like perfectly reasonable numbers until someone compares them to an NDVI
scale. The reads that matter here are a pair:

```python
raw = xarray.open_dataset(path, mask_and_scale=False)   # int16, max 10000
ok  = xarray.open_dataset(path)                          # float, max 1.0
```

The fill value compounds it. `_FillValue = -32768` scaled rather than masked
becomes `-3.2768`, still a finite float and still outside NDVI's range — so it
survives into an average and quietly drags it down.

## Cross-container pair

This case deliberately mirrors the raster case **`ndvi_scaled_int16_small`**,
which carries the same failure mode in a GeoTIFF. The two are linked in both
directions via `params.analogous_case_id`.

They are worth having as a pair because the packing metadata lives in a
completely different place in each container — a GDAL band scale in one, a CF
variable attribute in the other — and libraries routinely handle one and not the
other. A reader that passes one of these and fails the other has exactly the gap
the pair exists to find.

## Typical checks

- Open with and without `mask_and_scale` and confirm the two disagree.
- Decoded values fall inside `[-1, 1]`.
- `scale_factor` is `1e-4` (gated by `expected_scale_factor`).
- The fill cell is masked, not scaled.

# Validating `geocase` against rio-tiler — findings and verdict

**Date:** 2026-08-26
**Target:** rio-tiler 9.4.3 (`rio_tiler/` in this checkout is **byte-identical** to the
PyPI 9.4.3 sdist — verified with `diff -r`; every defect below is in shipping code)
**Tooling:** rasterio 1.4.4 / GDAL 3.10.3, numpy 2.4.6, morecantile 7.0.3, geocase 1.0.0rc2
**Question:** does `geocase`'s curated edge-case corpus find real bugs that agentic AI or
traditional methods (test suite / ruff / mypy / coverage) cannot?

> Scope note: this file documents an evaluation performed *using* this repository as a test
> target. It is not upstream rio-tiler documentation. The package source was not modified.

---

## 1. Verdict

**Don't adopt geocase as a bug-finding tool.** Adopt it, if at all, as a small
regression-fixture pack.

| Method | Cost | Real bugs found |
|---|---|---|
| geocase conformance mode (declared assertions) | 30 cases | **0** |
| geocase invariants + differential | full session | 1 novel + 1 already-open upstream |
| `ruff check` (repo config) | seconds | **0** |
| `ruff check --select ALL` | seconds | 0 real (1963 stylistic) |
| `mypy` | seconds | 0 real (1 numpy-typing complaint) |
| `pytest --cov` (73%, suite green) | 291s | **0** |
| **one agent, geocase forbidden** | **12 min, 93k tokens** | **6, incl. the geocase finding** |

The binding constraint on bug discovery was the **oracle** — differential comparison against
GDAL — not the fixtures.

---

## 2. Defects found in rio-tiler 9.4.3

Ordered by how confident and how serious. All verified against independent
rasterio/GDAL ground truth.

### A. Sheared/rotated geotransforms are silently mis-registered

rio-tiler builds a `WarpedVRT` for GCPs (`io/rasterio.py:100`) but never checks for shear
terms (`transform.b`/`transform.d`) in the geotransform.

Fixture: 8x8 float32, `Affine(20, 5, 1000, -5, -20, 2000)`, EPSG:32633, nodata -9999.

| call | result |
|---|---|
| `part(dst_crs == source CRS)` | 13/64 mask cells disagree with GDAL; 10 valid px vs 15 |
| `feature(dst_crs == source)` | same 13/64 |
| `part(dst_crs=3857)` | correct (WarpedVRT branch) |
| `tile()` | correct |
| `point()` | correct |
| `read()` / `preview()` | returns the **raw sheared array** labelled with the north-up envelope bounds |

No warning is emitted in any case. Georeferencing error up to 49.5 m (1.98 px) on an 8x8,
and it scales with raster size. On a 64x64 rotated fixture the marker-pixel error was
15 m E–W / 100 m N–S.

Root causes:
- `rio_tiler/reader.py:487` — `windows.from_bounds(*bounds, transform=src_dst.transform)`.
  rasterio's `from_bounds` silently drops the rotation terms, so the window is computed as
  if the raster were north-up. For an 8x8 it returns
  `Window(col_off=-2.67, row_off=-2.67, width=13.33, height=13.33)`.
- `rio_tiler/utils.py:404` — `dst_transform = src_dst.transform` when CRSs match, then
  `.a`/`.e` are read as resolution; wrong under shear.
- `rio_tiler/reader.py:313` + `rio_tiler/models.py:603-609` — `out_bounds` is the
  axis-aligned envelope and `ImageData.transform = from_bounds(...)` can only express
  north-up transforms.

Appears unreported upstream: a GitHub search of cogeotiff/rio-tiler issues for "rotated"
returns 0 results. Related rasterio issues: #3176, #1420, #2787, #3179.

### B. `read().band_descriptions` is wrong on every multiband raster — leaked loop variable

`rio_tiler/reader.py:322-324`:

```python
band_descriptions=[
    dataset.descriptions[ix - 1] or f"b{idx}" for idx in indexes
],
```

The comprehension variable is `idx`, but the index used is `ix`, which leaks from the
`for ix in indexes:` statistics loop at `reader.py:268` and is therefore pinned to the
last band index for every entry.

Verified — source descriptions `('red', 'green', 'blue')`:

```
read().band_descriptions       -> ['blue', 'blue', 'blue']     # expected red, green, blue
read(indexes=(3,1))            -> ['red', 'red']               # expected blue, red
info().band_descriptions       -> correct
```

Two public APIs silently disagree. One-character fix.

### C. `ImageData.statistics()` mutates the image in place

`rio_tiler/utils.py:158` calls `numpy.ma.fix_invalid(data, copy=False)` on the caller's
array; `models.py:928` passes `self.array` straight through.

```
before img.statistics():  data [1. 2. nan 4.]     mask [F F F F]
after  img.statistics():  data [1. 2. 1e+20 4.]   mask [F F T F]
```

A read-only query rewrites NaN to 1e20 and flips the mask. `to_raster()` and `render()`
subsequently emit different bytes depending on whether statistics were computed first.

### D. Internal mask band discarded when a nodata value is also set

`rio_tiler/reader.py:265-266` unconditionally overwrites GDAL's authoritative mask:

```python
if nodata is not None:
    ...
    data.mask = data.data == nodata
```

On a fixture whose `mask_flag_enums == [MaskFlags.per_dataset]` (mask band is
authoritative, no nodata flag):

| | rasterio truth | rio-tiler |
|---|---|---|
| masked pixels | 512 | 526 |
| mean | 108.199 | 123.912 |

14.5% mean error.

### E. Per-band nodata collapsed to band 1's, then applied to all bands

`rio_tiler/reader.py:124` collapses `src_dst.nodatavals` to a single scalar, applied to
every band at `reader.py:266` and pushed into `WarpedVRT(src_nodata=…, nodata=…)` at
`reader.py:127-140`. Measured 684% error on band 2's mean via a VRT fixture.

*Confidence note: confirmed in source; the VRT fixture was not independently rebuilt.*

### F. `_warp.warp()` mis-registers tiles — the experimental async readers return wrong pixels

Oracle: sync `Reader` (WarpedVRT) vs `experimental.geotiff.Reader` (uses `_warp.warp`),
both against `rasterio.warp.reproject` onto the 256x256 tile grid.

```
cog.tif, tile 9/175/98 (native 2658x2667):
  sync (WarpedVRT)   vs GDAL:     0/65536 px differ,  maxabs 0.0     <- EXACT
  async (_warp.warp) vs GDAL:  4531/65536 px differ,  maxabs 5072.0  <- WRONG
```

It is a **registration offset**, not resampling noise: rolling the async array by
(dy=-2, dx=+3) px drops nearest-mode disagreement from 2326 to 818 on a 64x64 COG.
Per-resampling error runs 1.5% of data range (average) to 7.1% (bilinear).

`plans/warp_two_step_pipeline.md:5` states the explicit design goal is "to match what the
sync reader's `WarpedVRT + dataset.read(out_shape=...)` pipeline does internally." It does
not match, and the sync side is the correct one.

Mitigating: this is the `experimental` module, which emits `RioTilerExperimentalWarning`
and is documented "subject to change and deprecation". The maintainers appear to know
something is off — `tests/test_async_geotiff.py:371` has
`numpy.testing.assert_array_equal(sync_tile.array, tile.array)` **commented out**, replaced
by `assert_allclose(..., rtol=1.5)`, a 150% relative tolerance that cannot fail on this data.

### G. Categorical `categories` silently coerced into the band dtype

`rio_tiler/utils.py:170` — `numpy.array(categories).astype(keys.dtype)` with no range or
exactness check. On uint8 data, requested category `300` wraps to `44` and is credited
value 44's count; the returned key is silently rewritten to `44`. Float `1.5` truncates to `1`.

### H. Antimeridian handling — already a known open bug

`optical_dateline_small` (EPSG:4326, bounds 179.9, 0.68, 180.22, 1.0) yields
`minzoom = maxzoom = 0` for a ~2 km/px dataset. `_dst_geom_in_tms_crs` returns
width=23, **height=0**. `tile_exists()` never returns True for the x=0 column, so the
0.22° that wraps to -180..-179.78 — 69% of the image — is unreachable at every zoom tested.

Root cause: rasterio's `calculate_default_transform` returns `(23, 0)` for seam-crossing
bounds; rio-tiler consumes it without validating (its `try/except` catches throws, not
degenerate-but-non-throwing output).

This is **cogeotiff/rio-tiler#702**, open since May 2024. Good regression fixture, not a
novel discovery.

---

## 3. Verified clean (negative results)

- **`tile_exists` non-finite branch** (`io/base.py:202`, `return True` on non-finite bounds):
  never fires. 0 of 65536 tiles at z=8 on EPSG:3995 produce non-finite transformed bounds
  under PROJ/GDAL 3.10.3. Independently corroborated by coverage marking line 203 uncovered.
- **dtype / nodata / scale / colormap / render / expression** across all 30 raster cases:
  clean. `unscale=True` differs from float64 truth by ≤4.8e-8 (float32 rounding);
  `render(PNG)` correctly raises `InvalidFormat` for 4-band uint16.
- **NetCDF `latlon_small` half-pixel registration:** exact. CF cell-centre coords imply
  edge bounds matching GDAL's netCDF driver to ~1e-15 on all four edges.
- **Mosaic alignment** (`geotiff_nodata_small` + `_shifted`): all 7 pixel-selection methods
  consistent with numpy.
- **Nodata "bleed" on downsampling:** rio-tiler matches rasterio `out_shape` reads exactly
  for nearest/average/bilinear/cubic. Pure GDAL semantics.
- **`statistics` `valid_percent`:** differs only by rio-tiler's 2-decimal rounding.
- From the no-corpus agent, independently: boundless `part`, `buffer`/`padding`,
  `align_bounds_with_dataset`, GCP-only datasets, alpha/RGBA, NaN nodata, expressions,
  percentiles, south-up and x-flipped transforms — all exact.

---

## 4. Evidence for the verdict

### 4.1 Traditional methods find none of this

- `ruff check rio_tiler/` with the repo's config: **all checks passed**.
- `ruff check --select ALL`: 1963 findings, all stylistic (docstrings, RET504, SIM103,
  ERA001…). Nothing pointing at shear, antimeridian, or warp registration.
- `mypy rio_tiler/`: 1 error (`models.py:127`, unrelated numpy-bool indexing complaint).
- `pytest --cov`: 453 passed, 12 xfailed, 6 xpassed, 73% total.

The most damning number in the exercise: **`_warp.py` sits at 97% line coverage and is
wrong.** Its one uncovered line (150) is an unrelated alpha-band resize. Every line
implicated in defect F is executed by the green suite — which then compares the result to
the correct answer with `rtol=1.5` and passes. Coverage cannot see this class of bug.

### 4.2 The corpus is narrower than the repo's own fixtures

Inventory of the 48 GeoTIFFs in `tests/fixtures/`:

- 12 distinct CRSs — including seven UTM zones and Equirectangular **Mars** and **Europa**
- 5 dtypes, 9 distinct nodata values (incl. nan, -3.4e38, -1.27e30)
- 36 with overviews, 9 with non-square pixels, 1 with a colormap
- antimeridian/full-earth: `cog_dateline.tif`, `cog_fullearth.tif`, `cog_world.tif`
- GCPs: `cog_gcps.tif`, `cog_gcps_ovr.tif`; alpha/mask: `cog_rgba`, `cog_rgb_mask`
- **sheared/rotated transforms: 0 of 48**

geocase's 30 cases (all 8x8 to 64x64) are close to a strict **subset**, adding exactly three
shapes the repo lacks: a sheared affine, EPSG:3995, and int8/int32. Only the first mattered.

Additionally, **28 of the 30 raster cases are striped, not tiled**. `async_geotiff.GeoTIFF.open`
rejects them outright (`TypeError: General error: Not a tiled TIFF`), so the async/COG
range-request surface is reachable by 2 cases.

### 4.3 The corpus was not necessary — control arm B

One general-purpose agent, hard-forbidden from importing or reading `geocase` in any form,
told only to hunt silent-wrong-pixel bugs using self-authored rasterio fixtures and a
differential oracle. Budget: 12 minutes, 93k tokens, 46 tool calls.

It **independently rediscovered defect A within ~90 seconds** (writing its own `rotated.tif`),
and described it *more* precisely than the geocase-driven run — splitting it into the
`read()`/`preview()` transform-fabrication bug and the `part()` window bug, and correctly
identifying that `tile()` and `point()` are unaffected.

It then found defects **B, C, D, E, G**, none of which the geocase-driven investigation
surfaced. It also produced a long credible clean list and correctly declined to report three
near-misses (≤1px two-stage resampling drift, a `max_size` aspect-ratio doc mismatch, and
dead code at `utils.py:496`).

Defects A and F both reproduce with no geocase involvement — A in ~12 lines of rasterio,
F on this repo's own `cog.tif`, where the error is *larger* than on geocase's 64x64 COGs.

---

## 5. Corpus defects found in geocase 1.0.0rc2

- **`hole_center_nodata` false-passes.** Metadata says "valid pixels ring a central NoData
  void"; `notes.md` says "donut-like shape around NoData"; `behavioral_goal` says "ensure
  footprint generation handles interior NoData correctly". The actual raster has nodata
  **only on the 1-pixel outer border** — the interior 10x10 is fully valid. The bundled
  `hole_center_nodata_footprint.geojson` is a MultiPolygon with a single 5-point ring and no
  interior ring. A consumer testing interior-hole preservation gets a green light from a case
  that cannot test it.
- **5 cases declare a nodata value but contain zero nodata pixels:**
  `cog_multispectral_small`, `landcover_small`, `multispectral_mixed_resolution_small`,
  `multispectral_s2_like_small`, `ndvi_scaled_int16_small`.
- **All raster cases are 8x8–64x64** — too small to reach tiling, windowing, overview, or
  batch-boundary bugs. (Mirrors the "max 4 features" finding in the earlier pyogrio report.)
- The 5 footprint cases all share one directory.

Checked and **not** defects: `files.sidecars` correctly lists
`geotiff_external_overviews_small.tif.ovr`; `geotiff_nodata_small_shifted` is accurate
(pixel arrays byte-identical, only the geotransform origin moves).

---

## 6. Recommendations

**For geocase:**

1. Drop the conformance / declared-assertion mode as a consumer-validation feature, or
   reposition it honestly as a corpus self-check. It has now found zero bugs across two
   libraries (rio-tiler and pyogrio).
2. **Ship the oracle, not the files.** Every bug in this report came from a differential
   comparison against an independent implementation. That is the reusable asset; the
   fixtures are not.
3. Fix `hole_center_nodata` before anyone else relies on it.
4. Add realistically-sized and tiled/COG cases if the async and windowing surfaces are
   meant to be reachable.
5. Keep the sheared-transform and dateline cases — they are genuinely useful regressions
   once fixes exist.

**For rio-tiler** (worth reporting upstream, in this order):

1. **B** — `read().band_descriptions` leaked loop variable. Unambiguous, one-character fix.
2. **C** — `statistics()` mutating its input.
3. **A** — sheared geotransforms; at minimum warn instead of silently mis-registering.
4. **D**/**E** — mask-band and per-band-nodata handling.
5. **F** — `_warp.warp()` registration, and restore the real assertion in
   `tests/test_async_geotiff.py:371`.

---

## 7. Reproducing

Probe scripts and raw results are under the session scratchpad
(`probes/`, `results/FINDINGS.md`), not in this repo. Key scripts:

| script | what it shows |
|---|---|
| `probes/warpdiff/p_asyncdiff.py` | sync vs async differential over all 30 cases |
| `probes/warpdiff/p_truth.py` | both paths vs GDAL `reproject` ground truth |
| `probes/warpdiff/p_nogeocase.py` | defect F on this repo's own fixtures |
| `probes/verify/v.py` | defects B, C, D verified empirically |
| `probes/control/p_fixtures.py` | fixture-coverage inventory (§4.2) |
| `probes/rest/p_polar2.py`, `p_misc2.py` | negative results (§3) |
| `repro_rotated_nogeocase.py` | defect A in ~12 lines of rasterio |

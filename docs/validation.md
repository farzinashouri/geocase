---
description: "Two rounds of differential validation pointed the GeoCase corpus at ten widely used geospatial libraries and found 26 confirmed defects, most of them silent — and zero overlap between what the corpus caught and what code review caught."
---

# What ten geospatial libraries got wrong, and how we found out

*A unified report on two rounds of differential validation against the GeoCase corpus.*

> Date: 2026-08-31 · Corpus: geocase 1.0.0rc3, 154 cases (117 vector / 34 raster / 3 netcdf)
> Environment: Python 3.14.3, GDAL 3.12.2
> Round 1: pyogrio · rio-tiler · geocube · fiona
> Round 2: titiler · stackstac · odc-stac · lonboard · geoarrow-python · pyproj

---

## The short version

We pointed the same corpus of deliberately awkward geospatial files at ten
widely used Python libraries, and read every file at least two different ways
that ought to agree. Where two readings disagreed, one of them was wrong — and
finding out which one produced **26 confirmed defects**, most of them silent.

"Silent" is the important word. Only a handful of these bugs raise an error.
The rest return a plausible-looking array, or a valid HTTP 200, containing the
wrong numbers in the wrong place on the Earth.

| | Round 1 | Round 2 | Total |
|---|---|---|---|
| Libraries tested | 4 | 6 (+1 incidental) | 10 |
| Confirmed findings | 9 | 17 | **26** |
| Found by the corpus, missed by code review | 5 | 14 | **19** |
| Found by code review, missed by the corpus | 4 | 3 | **7** |
| Found by **both** methods | 0 | 0 | **0** |

That last row is the single most interesting number in this document, and the
[final section](#the-two-methods-never-overlap) is about why.

---

## The method, in one paragraph

Never trust a single reading. For each file we obtain the answer twice — two
libraries, or two code paths inside one library, or a library against a
neutral reference such as GDAL's `WarpedVRT` — and compare. Neither reading is
treated as the truth; the *disagreement* is the finding, and only then do we
open the source to work out which side is at fault. This matters because there
is no oracle for "what should this GeoTIFF contain": the only thing we can
assert with confidence is that two correct implementations must agree.

The second method is plain code review with the corpus deliberately shut off —
reading the library source at HEAD, writing tiny synthetic probes, never
opening a case file. The two passes ran independently and in that order.

---

## Round 1 — the warm-up

Four libraries, all in the mainstream vector/raster reading stack.

| Library | Verdict |
|---|---|
| **rio-tiler** | 3 findings — two silent geographic-correctness bugs |
| **fiona** | 3 findings — a driver gap and two dunder-contract violations |
| **pyogrio** | 2 findings (found by an earlier run; ours missed both) |
| **geocube** | 1 finding — a silently ignored argument |

### The two that mattered

**rio-tiler serves rotated rasters at the wrong place on Earth.** A GeoTIFF
whose affine transform has rotation terms (`transform.b`, `transform.d`) is
perfectly legal. rio-tiler returns the raw, *unrotated* pixel array, while
simultaneously reporting north-up bounds for it. Every pixel is therefore
placed at a wrong ground position, with no error and no warning.

| reading | valid pixels | correct? |
|---|---|---|
| `WarpedVRT` (neutral reference) | 7 | — |
| `Reader.read()` | 9 | **no** — the raw unwarped array |
| `Reader.part()` | 4 | **no** |
| `Reader.preview()` | 9 | **no** |
| `Reader(dataset=WarpedVRT).read()` | 7 | yes — the workaround |

The cause is one line: `rio_tiler/io/rasterio.py:100` wraps a dataset in a
correcting `WarpedVRT` only `if self.dataset.gcps[0]` — ground control points.
A rotated affine is never checked. The one-line fix is to test the rotation
terms too.

**rio-tiler inverts the bounds of bottom-up rasters.** A GeoTIFF with a
positive `transform.e` stores its rows south-to-north. rio-tiler passes
rasterio's inverted bounding box straight through, so `Reader.bounds` comes
back with the bottom edge *above* the top — an implied height of −360 metres.
`Reader.feature()` then raises, while `Reader.part()` over the exact same area
succeeds.

### And the ones we got wrong

We reported pyogrio **clean**. It had two live bugs, both already documented
in this very repository, and both still reproducing on the newest release. We
missed them because our harness varied only one axis — library A against
library B on a plain read — and both bugs live in *option* space:

- `fid_as_index=True` with `use_arrow=True` crashes, **but only on GeoJSON**.
  We spot-checked with a GeoPackage, the one format that works.
- A spatial filter plus the Arrow path wrongly admits a NULL-geometry row.
  We never passed `bbox=` at all.

This is the lesson round 1 paid for: **a corpus of files is not a test.** A
case only discriminates when it is combined with the option that makes it
discriminate. `empty_geometry_gpkg` is inert without `bbox=`; forty-four
GeoJSON files are inert without `fid_as_index=True`.

---

## Round 2 — the STAC and Arrow generation

Six libraries, chosen because they sit one layer *above* round 1's — they
consume STAC metadata, serve tiles over HTTP, or move geometry through Arrow.

| Library | Verdict |
|---|---|
| **titiler** | **6 findings** — 2 rio-tiler defects republished over HTTP, 4 new at the service layer |
| **geoarrow-python** | **4 findings** — 2 in pyarrow type dispatch, 2 in geoarrow-pandas |
| **odc-stac** | **3 findings** — one destroys data on the most ordinary call there is |
| **stackstac** | **2 findings** — both block ordinary use outright |
| **lonboard** | **2 findings** — both about geometries that are *absent* |
| **pyproj** | clean to this run, under both methods |
| *rio-stac* (incidental) | 1 finding |

### The best instrument we built: two libraries, one input

stackstac and odc-stac do the same job — load STAC assets onto a common grid —
and they were written independently. So we synthesised one STAC Item per raster
case and fed the **byte-identical** Item to both, across 34 rasters × 10 option
combinations, with `rasterio` + `WarpedVRT` on the same grid to break ties.

Every disagreement is a finding by construction. Three of the round's five most
severe bugs came out of this one comparison:

| behaviour | stackstac | odc-stac |
|---|---|---|
| CRS unit conversion when reprojecting | **correct** | **1×1 output** ❌ |
| `raster:bands` scale/offset | applies it | **ignores it** ❌ |
| rotated affine | refuses honestly (`NotImplementedError`) | carries it correctly |
| multi-band single-file assets | refuses by design | reads them |
| accepts a `pystac.Item` | **rejects all of them** ❌ | reads them |
| output dtype other than float64 | **unreachable** ❌ | any dtype |

Note that neither library wins. Each is right where the other is wrong, which
is exactly why the comparison works and why neither could have been used as an
oracle for the other.

### The worst bug of both rounds

```python
odc.stac.load([item], bands=["band1"], crs="EPSG:4326")
```

Reprojecting a 16×16 raster of 10-metre pixels into WGS84 returns a **1 × 1
array**. The number `10` is carried across the unit change unconverted, so a
ten-*metre* pixel becomes a ten-*degree* pixel — roughly 1,100 km on a side.
The whole raster lands in one cell. No exception, no warning.

**31 of the 34 rasters in the corpus collapsed to a single pixel on this axis.**
The three survivors were already stored in a degree-based CRS. In the other
direction it inflates instead: a 0.01°-pixel source requested in EPSG:3857
derives a 1.78 M × 1.78 M grid — about 25 TB.

| request | result |
|---|---|
| `load(item)` | 16×16 ✔ |
| `load(item, crs="EPSG:4326")` | **1×1** ✘ |
| `load(item, crs="EPSG:4326", resolution=0.0001)` | 15×19 ✔ |

Giving an explicit `resolution=` fixes it, which is why this survives in
production pipelines: everyone who hit it added a resolution and moved on.

### Two libraries, one Item, values 10,000× apart

```
odc-stac  .load():   -9922.00000 ..  -7647.00000   (raw integers)
stackstac .stack():      -0.99220 ..     -0.76470   (scaled, scale=0.0001)
```

odc-stac extracts only `("nodata", "data_type", "unit")` from `raster:bands`
and has nowhere to put a scale or an offset. This is precisely how scaled
integer products ship — Sentinel-2 L2A baseline 04.00 carries `offset: -0.1` —
so ignoring it shifts every reflectance value in the scene. Neither library
warns; you find out by loading the same data twice.

### The bugs that block ordinary use

**stackstac rejects every `pystac.Item`.** pystac ≥ 1.13 migrates STAC's
projection extension to v2.0 on load, renaming `proj:epsg` to `proj:code`.
stackstac reads only `proj:epsg` — `grep -rn "proj:code" stackstac/` returns
nothing — so the library's own documented workflow now fails on every Item,
with a message naming the one field the Item does not carry. Passing the same
Item as a raw `dict` works fine.

**stackstac cannot produce any dtype but float64.** Three places validate a
scalar by testing its Python *type* rather than its value:

```python
np.can_cast(type(asset_scale), dtype)   # type(1.0) is float -> float64
```

`can_cast(float64, float32, "safe")` is `False` no matter what the value is, so
`dtype="float32"` fails on all 34 corpus rasters — including ones with no
scaling metadata at all, and ones where `scale=1.0, offset=0.0` make the
rescaling a no-op. The capability is fine; only the check is wrong.

### titiler: everything below it, republished over HTTP

titiler sits on rio-tiler, so round 1's two bugs got a second life. We re-ran
both round-1 reproductions against the current rio-tiler first — both still
reproduce — and then watched them come out of the HTTP API unchanged.

| endpoint | what a client sees |
|---|---|
| `/cog/preview` on a rotated raster | HTTP 200, the raw unwarped array, `/cog/info` describing it north-up. "rotat" appears nowhere in any response. |
| `/cog/info` on a bottom-up raster | `bounds: [500000, 4200360, 500360, 4200000]` — bottom above top |
| any follow-up request using those bounds | **HTTP 500**, "Bounds and transform are inconsistent" |

Every route out of `/cog/info` for a bottom-up source ends in a server error,
and a property of the *file* is reported as a fault of the *server*.

Four more defects are introduced at the service layer itself. The one with
teeth is **colour applied to numeric formats**:

```
On disk                   : 1 band uint8, class codes [1, 2, 3], 256-entry palette
rio-tiler library preview : (1, 16, 16), values [1, 2, 3]     <- correct
titiler /cog/preview.npy  : (3, 16, 16), values [0, 128, 200, 255]
titiler /cog/preview.tif  : 4 bands, band-1 values [0, 128]
```

`.npy` and `.tif` are the *numeric* formats — the ones you request precisely
because you want the values. The dataset's own palette is applied before the
output format is even considered, so land-cover class codes come back as RGBA
and are **unrecoverable**: a palette is many-to-one onto colour. Nothing in the
response says a colormap was applied, and the library underneath returns the
codes correctly.

The remaining titiler findings are error-handling: a 4-band PNG request returns
`500` with a message blaming the wrong band count (the refusal is about a
*fifth* band, the mask, appended by rio-tiler as alpha), and antimeridian
sources produce TileJSON with `maxx = 180.22` — out of spec for both TileJSON
3.0 and RFC 7946.

### lonboard and geoarrow: the geometry that isn't there

Both lonboard findings are about absence. It drops the Arrow validity bitmap —

```
geopandas .to_arrow(geoarrow)   null mask: [False, False, True, False]
lonboard  .from_geopandas()     null mask: [False, False, False, False]
```

— so "this feature has no geometry" becomes "this feature is at NaN, NaN", a
different claim. And a frame legitimately filtered down to *no* geometries
raises `ValueError: 0-length dimension not currently supported` instead of
drawing an empty map.

geoarrow-python has the mirror-image problem: `as_geoarrow()` on an all-empty
array raises `AttributeError`, because type inference with no coordinates to
infer from returns plain `pyarrow.null()` and the next line reads an attribute
off it. Separately, `geoarrow-pandas` violates the pandas ExtensionArray
contract in a way that can silently corrupt a DataFrame:

| expression | geoarrow-pandas | pandas contract |
|---|---|---|
| `a == b` (lengths 3 vs 2) | `array([True, False])` — **length 2** | `ValueError` |
| `a == None` | `TypeError: not iterable` | `[False, False, False]` |
| `a == 5` | `TypeError: not iterable` | `[False, False, False]` |
| `a == "POINT (0 0)"` | compares against the string's **characters** | — |

The cause is `zip(self, other)` with no length check and no scalar handling. A
truncated boolean mask assigned back into a DataFrame is a silent wrong answer.

---

## What was clean, and what "clean" means

**pyproj came through both methods clean**, which is a real result and worth
stating. Four probes fired and all four ran down to an explanation rather than
a defect: longitude wrapping (lossy in representation, correct in position),
the pole singularity (longitude is undefined at a pole), float noise of
1–4 × 10⁻⁶ *metres* (our tolerance was too tight), and an axis-order probe that
behaved correctly. **titiler.xarray** was likewise clean on all three NetCDF
cases — and notably decoded CF `scale_factor` correctly, the same class of
metadata odc-stac drops on the STAC side.

But "clean" here means **clean to this run, on these probes, at these versions**
— never absence of defects. Round 1 called a library clean and was wrong twice.

### We were also wrong about lonboard, briefly

An early sweep reported five coordinate divergences in lonboard. All five were
our fault. lonboard emits `OGC:CRS84`, whose `to_epsg()` is `None` and which
does not compare equal to `EPSG:4326` unless axis order is ignored — so our
comparison took the wrong branch. Checked properly, the coordinates match to
`atol=1e-9`.

Five false findings is the same order of magnitude as that library's true
findings. **A differential harness needs its equality predicate audited as
carefully as the libraries it tests.**

---

## The two methods never overlap

Across 26 findings and ten libraries, the corpus method and the code-review
method have found **zero bugs in common**. Not "few". Zero, twice, in two
independent rounds.

| | Corpus sweep | Code review |
|---|---|---|
| Round 1 | 5 | 4 |
| Round 2 | 14 | 3 |
| **Total** | **19** | **7** |
| **Found by both** | **0** | **0** |

The reason is structural, and once you see it the zero stops being surprising.

**Corpus findings are about bytes on disk.** An affine convention, a driver
allow-list, a scale factor in an asset's metadata, a palette in a TIFF header.
Almost all of them require a *specific file* to exist, and none can be reached
by reading source unless you already suspect the exact condition. You cannot
grep for "what happens to a rotated raster" — you have to have a rotated
raster.

**Review findings are about API contracts.** A docstring promising one thing
while the code does another; a dunder raising where Python forbids it; a
released package broken against its own released dependency. Most of them
involve no file at all — which makes them *structurally impossible* for a
corpus of test data to find. No GeoTIFF anywhere will ever cause
`Object.__eq__` to raise.

There is a third category worth naming, because it is the one that stings:
findings a corpus sweep can walk straight past. Round 1's harness compared
`mask > 0`, which is correct at every dtype — and therefore could not see that
`ImageData.mask` breaks its documented 0/255 contract. The sweep ran *over* the
bug.

### What this means if you are testing a library

1. **Run both methods.** Either one alone will report a clean library that
   isn't. That happened three times across these two rounds.
2. **Vary options, not just inputs.** Round 1 missed two pyogrio bugs holding
   the right files and never passing `bbox=` or `fid_as_index=`. Files are
   inert without the option that makes them discriminate.
3. **Never nominate an oracle.** Every strong finding in round 2 came from two
   implementations disagreeing, with the tie broken afterwards by a third.
4. **Audit your comparison.** Ours produced five false positives from one CRS
   equality check.
5. **Report "clean to this run"** and list exactly what you swept, so the next
   run extends your work instead of repeating it.

---

## Findings at a glance

| # | Library | Finding | Severity | Found by |
|---|---|---|---|---|
| 1 | rio-tiler | Rotated affine silently mis-georeferenced | HIGH | corpus |
| 2 | rio-tiler | Bottom-up bounds inverted; `feature()` raises | MED | corpus |
| 3 | rio-tiler | `ImageData.mask` breaks its documented 0/255 contract | MED-LOW | review |
| 4 | fiona | KML/LIBKML commented out of `supported_drivers`, misleading error | LOW | corpus |
| 5 | fiona | `Object.__eq__` raises instead of returning `False` | MED | review |
| 6 | fiona | `Feature.__eq__` unguarded → `AttributeError` | MED | review |
| 7 | geocube | `fill` silently ignored by default point method | MED-LOW | review |
| 8 | pyogrio | `fid_as_index` + Arrow crashes on GeoJSON | MED | corpus |
| 9 | pyogrio | GPKG spatial filter + Arrow admits NULL geometry | MED | corpus |
| 10 | stackstac | Rejects every `pystac.Item` (`proj:code` unsupported) | HIGH | corpus |
| 11 | odc-stac | `crs=` without `resolution=` reuses resolution across a unit change | HIGH | corpus |
| 12 | odc-stac | Ignores declared `raster:bands` scale/offset | MED | corpus |
| 13 | stackstac | No output dtype but `float64` is reachable | MED | corpus |
| 14 | titiler | Republishes rotated-affine mis-georeferencing over HTTP | HIGH | corpus |
| 15 | titiler | Bottom-up bounds republished; corrected request 500s | MED | corpus |
| 16 | titiler | Colormap applied to `.npy` / `.tif`; class codes unrecoverable | MED | corpus |
| 17 | titiler | 4-band PNG → 500, wrong band count in the message | MED | corpus |
| 18 | titiler | Antimeridian source → out-of-spec TileJSON and GeoJSON | LOW-MED | corpus |
| 19 | lonboard | Arrow validity bitmap dropped | MED | corpus |
| 20 | lonboard | All-empty geometry frame raises | MED | corpus |
| 21 | geoarrow-pyarrow | `as_geoarrow()` raises on an all-empty array | MED | corpus |
| 22 | geoarrow-pyarrow | GeometryCollection builds a name its own C core rejects | LOW-MED | corpus |
| 23 | geoarrow-pandas | `__eq__` violates the ExtensionArray contract | MED | review |
| 24 | geoarrow-pandas | Released version broken against released geoarrow-pyarrow | MED | review |
| 25 | odc-stac | Ambiguous band alias resolved silently | MED | review |
| 26 | rio-stac | Inverted `proj:bbox` for bottom-up rasters | MED | corpus |

Every finding above ships a standalone reproduction that builds its own file
and imports no geocase code, a source-confirmed root cause with a `file:line`,
and a ready-to-paste upstream issue body. All reproductions were re-verified in
an interpreter with `geocase` blocked from import.

**Nothing has been filed upstream.** These are drafts.

## Where the raw material lives

The harnesses, frozen per-case results, 18 standalone reproductions and the
upstream issue drafts are held outside this repository, in the two validation
workspaces the runs were executed from — round 1 in `geocase_validation/`,
round 2 in `geocase_validator/`. Each round's `findings/` directory holds its
`REPORT.md`, its `COMPARISON.md` and per-consumer JSON; round 2 additionally
separates `corpus/` from `review/` results so the two methods can be compared
without either contaminating the other.

What those runs imply for the corpus itself is worked out in the project's
planning log, which is kept in the repository and read on GitHub rather than
published here:

- [Plan 37 — the raster corpus and the differential adapters](https://github.com/farzinashouri/geocase/blob/main/docs/plans/37-raster-signal-and-differential-adapters.md)
- [Plan 38 — six consumers and the STAC adapter](https://github.com/farzinashouri/geocase/blob/main/docs/plans/38-six-consumer-round-2-and-the-stac-adapter.md)
- [Plan 39 — the release, the site, and going public](https://github.com/farzinashouri/geocase/blob/main/docs/plans/39-going-public-upstream-first.md)

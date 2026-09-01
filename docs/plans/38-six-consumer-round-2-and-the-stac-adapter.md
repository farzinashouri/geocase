# Plan 38 — Six Consumers, Eighteen Defects, and the STAC Adapter the Corpus Had to Grow

> **Status: proposed 2026-08-31.** A second external differential run — this
> time against **titiler, stackstac, odc-stac, lonboard, geoarrow-python and
> pyproj** — found **18 defects across 7 libraries**, eleven of them attributable
> to a specific case. That is [Plan 37](37-raster-signal-and-differential-adapters.md)'s
> signal repeated on a surface it never touched, and it settles the entry
> condition [Plan 28](28-validate-geocase.md) Phase 4 has been waiting on since
> August: the raster adapter protocol is now justified twice over, and this plan
> starts it. It also carries three corrections to the corpus's own picture of
> itself — two "gaps" this plan's brief predicted turn out to already exist, and
> one turns out to be the corpus's single most productive raster case. Phase 1
> records the divergences; Phase 2 ships the **STAC-Item adapter** the run had to
> build by hand; Phase 3 adds the option-pair matrix and the equality predicate
> whose absence produced five false findings; Phase 4 adds the four cases the
> round genuinely could not express; Phase 5 files three of the seventeen issue
> drafts, because three runs have now shown the corpus finds real defects and
> **none has shown that anyone outside this repository wants them**.

## Context

A validation run on 2026-08-31 read the 1.0.0rc3 corpus (154 cases) with six
consumers under Python 3.14.3 / GDAL 3.12.2, using the differential shape
[`geocase.differential`](../../src/geocase/differential.py) documents: read each
case two or three ways that must agree, and report the disagreement. Full
report, harness, frozen per-method results and 16 standalone reproductions are
in `/Users/farzinashouri/projects/geocase_validator/` (`findings/REPORT.md`,
`findings/COMPARISON.md`).

| Consumer | Version | Result |
|---|---|---|
| **titiler** | 2.2.1 (rio-tiler 9.4.3) | **6 defects** — 2 are Plan 37's rio-tiler pair, republished over HTTP; 4 originate at the service layer |
| **odc-stac** | 0.5.3 | **3 defects** — one returns a **1×1 array** for the most ordinary reprojection call there is |
| **geoarrow-python** | pyarrow 0.2.0 / pandas 0.1.1 | **4 defects** — 2 in type dispatch, 2 in geoarrow-pandas |
| **stackstac** | 0.5.1 | **2 defects** — both block ordinary use outright |
| **lonboard** | 0.16.0 | **2 defects** — both about geometries that are *absent* rather than present |
| **pyproj** | 3.7.2 | clean to this run, under **both** methods |
| *titiler.xarray* | 2.2.1 | clean to this run — all 3 NetCDF cases pass, **including CF packing** |
| *rio-stac* | 0.12.0 | 1 defect, found incidentally — the corpus had to synthesise STAC Items to test the other two, and the synthesiser is broken for one convention |

### The instrument that produced most of it

The strongest thing in this round was **stackstac against odc-stac**: two
independent implementations of one operation (load STAC assets onto a common
grid), so neither can be assumed correct and every disagreement is a finding by
construction. `rasterio` + `WarpedVRT` at the same geobox broke the ties. 34
rasters × 10 option combinations, plus a **pinned** family in which both
libraries and the reference were handed the *identical* target geobox, so a
pixel disagreement is a defect rather than a convention difference.

| axis | stackstac | odc-stac |
|---|---|---|
| CRS unit conversion when reprojecting | correct | **1×1 output** |
| `raster:bands` scale/offset | applies it | **ignores it** |
| rotated affine | refuses honestly (`NotImplementedError`) | carries it correctly |
| pystac Items | **rejects all of them** | reads them |
| output dtype | **only float64 reachable** | any dtype |

Three of the run's five most severe findings came out of that one comparison,
and in each the corpus supplied the *case* while the option matrix supplied the
*discrimination*. That is Plan 37's sharpest input — *a corpus finding needs a
case **and** the option combination that makes it discriminate* — confirmed
prospectively rather than in hindsight.

### One axis, two encodings, opposite outcomes

The corpus happens to carry the scale/offset concept twice — as STAC
`raster:bands` on `ndvi_scaled_int16_small`, and as CF `scale_factor` on
`ndvi_packed_netcdf`. Round 2 ran both: **odc-stac dropped the STAC form and
returned raw DN; titiler.xarray decoded the CF form correctly.** A corpus that
holds one concept in two encodings can say which consumer is wrong rather than
only that two consumers differ, and that is worth stating as a curation
principle rather than leaving as an accident.

### Which case found what

Ten defects are attributable to a specific case. Every one of them is a case
curated around a **named failure mode**, not a format baseline — the same
pattern Plans 28 and 37 record, now on a third independent run:

| case | defect it found |
|---|---|
| `rotated_two_islands` | titiler serves raw unwarped pixels under north-up bounds (HIGH), and the three-way stackstac/odc-stac/rio-tiler split on rotation |
| `bottom_up_dem_small` | titiler republishes inverted bounds and 500s on the normalised request; **rio-stac writes an invalid `proj:bbox`** |
| `ndvi_scaled_int16_small` | odc-stac silently ignores declared `scale`/`offset` — a 10 000× value difference against stackstac |
| `landcover_small`, `landcover_ambiguous_zero_small` | titiler returns **colours, not data**, from `/preview.npy` and `.tif` |
| `cog_multispectral_small`, `multispectral_s2_like_small` | titiler 500s on 4-band PNG, with the wrong band count in the message |
| `optical_dateline_small` | titiler emits out-of-spec TileJSON bounds/centre and GeoJSON longitude |
| `empty_geometry_gpkg` | lonboard drops the Arrow validity bitmap |
| `empty_polygon` | lonboard raises on an all-empty frame; geoarrow raises an internal `AttributeError` |
| `geometrycollection_mixed_valid` | geoarrow builds an extension name its own C core rejects |
| all 34 rasters, on the `crs=` axis | odc-stac collapses **31 of 34** to a single pixel |

### Why these cases pay: the consumers do not test these conventions at all

The obvious objection to a curated corpus is that its cases are trivial to
rebuild — `rotated_two_islands` is an 8×8 GeoTIFF with a skewed affine, and any
of these projects could write one in twenty lines. That objection is
**post-hoc**: the reproduction is written *after* the finding, and its
simplicity is a property of hindsight rather than of the search.

Measured instead of assumed. Keyword probe of each consumer's **own** test
suite, at the same commits this round tested:

| library (test dir probed) | `.py` | files with `def test` | `nodata` | rotation / skew | bottom-up | empty geom | scale |
|---|---|---|---|---|---|---|---|
| stackstac (`stackstac/tests`) | 4 | 3 | 2 | **0** | **0** | 0 | 0 |
| odc-stac (`tests`) | 10 | 6 | 15 | **0** | **0** | 0 | 1 |
| titiler (`core/tests`) | 18 | 16 | 4 | **0** | **0** | 1 | 1 |
| lonboard (`tests`) | 33 | 22 | 0 | **0** | **0** | 1 | 0 |
| geoarrow-pyarrow (`tests`) | 5 | 5 | 0 | **0** | **0** | 1 | 0 |

The first three columns are controls: the suites are real, actively maintained,
and odc-stac's touches nodata in fifteen files. **Not one of the five has a test
that mentions rotation or a bottom-up affine** — the two conventions that
produced the most severe findings of both round 1 and round 2, across five
different libraries.

So the difficulty was never writing the file. It is knowing which file to write,
and having it present at the moment of testing. Everyone writes the north-up,
unrotated, unscaled, non-empty version, because that is what comes to mind.

Two supporting observations:

- **The review pass found 0 of the 14.** With all six codebases open and
  specifically hunting, source review reached none of the corpus's findings. If
  these were obvious on inspection, some would have fallen out.
- **Hand-rolled fixtures fail silently.** [Plan 28](28-validate-geocase.md)
  Phase 1 found six geocase cases declaring nodata with zero nodata pixels, and
  `hole_center_nodata` shipping as the *inverse* of its description. A fixture
  that is subtly wrong yields a passing test for the wrong reason and says
  nothing. That is the argument for content-gated fixtures over ad-hoc ones, and
  it is an argument geocase earned by catching it in itself.

*Method limit, stated so the table is not over-read:* this is a keyword probe,
not a semantic audit. A test could construct a rotated transform without using
the words "rotate" or "skew". Treat the zeros as a strong indicator rather than
proof, and confirm by reading before quoting them upstream.

### The honest part: three findings the corpus did not really find

`findings/COMPARISON.md` counts fourteen findings that geocase caught and the
review pass missed. **Eleven** is the number this plan should be built on,
because three of the fourteen were surfaced by the *run* and not by a *case*:

- The stackstac `proj:code` defect was hit **while building the harness**, on
  the first call, before any case was read. Any STAC Item triggers it.
- The stackstac dtype defect fired **identically on all 34 rasters**. It
  discriminates between *options*, not between files.
- The odc-stac `crs=`/resolution defect needs a source whose CRS units differ
  from the target's — so it does depend on the corpus holding *something* — but
  all 31 metre-CRS rasters expose it identically. No case does work another
  would not.

Recording that distinction matters more than the headline. A corpus that claims
credit for defects any input would have found cannot tell which of its cases are
earning their keep — which is precisely the question Phase 4 has to answer when
it decides what to add.

### A second method, and zero overlap — for the third time

A review pass over the same six repositories at HEAD, opening **no case file**
and reading **no corpus result** (both recorded in `findings/review/*.json`),
found **four** further defects. **None overlapped.** Plan 37 recorded zero
overlap on 9 findings across 4 libraries; this is zero overlap on 18 across 7.

The mechanism is now clear enough to state as a rule:

> A **corpus** finding requires a byte pattern the consumer's model cannot
> represent. A **review** finding requires a stated promise the consumer breaks.
> Those sets are nearly disjoint, because code that breaks a promise usually
> breaks it for every input, and bytes that break a model usually do so without
> any promise having been made about them.

Three of the four review findings are **structurally unreachable** by a corpus of
test data — no file appears anywhere in their reproduction (`__eq__` truncating
on a length mismatch; a released package that cannot import; a bare `assert` on
request data). The fourth, odc-stac's silent band-alias resolution, is reachable
in principle and is the subject of Phase 4.2.

Two cheap review techniques did most of the work and neither is systematised:
`grep` for dunders across every repo (four minutes; found the `__eq__` defect,
and cleared pyproj's four correctly-guarded implementations), and **reading the
source's own comments** — odc-stac's band-alias defect was found by
`# maybe warn about ambiguity?` sitting in `model.py`, a note the project had
already written and nobody had grepped for.

### The method's own failure, recorded

The lonboard sweep first reported **five divergences that were the harness's
fault**. lonboard emits **OGC:CRS84**, whose `to_epsg()` is `None` and which does
not compare equal to `EPSG:4326` unless axis order is ignored, so the comparison
read a *correct* reprojection as a coordinate error. Five false findings against
two true ones for that library, caught only because every divergence was
hand-checked against `gdf.to_crs(4326)` before write-up.

This is Plan 37's hand-rolled-harness lesson in a new costume, and it points the
same way: **geocase should ship the comparison, not just the files.** A
`compare_cases` that knows CRS84 and EPSG:4326 are the same CRS is written once,
not once per consumer. Phase 3.2 is that predicate.

### Three corrections to the corpus's picture of itself

This plan's brief predicted five corpus gaps. Measured against the catalog, two
of them do not exist, and one names the corpus's **most productive raster case**:

| predicted gap | reality |
|---|---|
| "a raster with `scale`/`offset` set" | **Three exist** — `ndvi_scaled_int16_small` (scale 0.0001) and `multispectral_{mixed_resolution,s2_like}_small` (scale 0.0001, **offset −0.1**, the Sentinel-2 baseline-04.00 shape). The first of them found odc-stac's scale/offset defect. Not a gap; a success — and `ndvi_packed_netcdf` covers the same axis in CF form, where titiler.xarray decoded it **correctly**, giving the corpus a matched pass/fail pair on one concept. |
| "a raster whose nodata is also a legitimate value" | **Seven exist** — `landcover_ambiguous_zero_small` (0 on uint8), `water_mask_small` (255 on uint8), and five uint16 rasters with nodata 0. [Plan 32](32-footprint-truth-and-ambiguous-zero.md) built exactly this. Not a gap. |
| "a second CRS family in the raster set" | **Real gap, confirmed.** 31 of 34 are EPSG:32633; the other three are 2 × EPSG:4326 and 1 × EPSG:3995. |
| "a multi-item / overlapping-footprint raster group" | **Real gap, confirmed**, and now with a defect attached that it would have caught. |
| "a rotated raster that is not the only one of its kind" | **Real gap, confirmed.** Still exactly one, and it found a defect for the second run running. |

Phase 4 builds the three that are real and adds a fourth the round exposed.

---

## Phase 1 — Record the divergences, and gate the conventions that paid

Every finding below is a consumer defect, not a corpus defect, so nothing in
`case.yaml` is wrong. What is missing is the record, so a repeat run reports
`known` rather than re-deriving — which is what `CaseMetadata.known_divergences`
exists for.

### 1.1 Record the seven case-attributable consumer divergences (TDD)

**Failing test first:** extend `tests/unit/test_known_divergences.py` to assert a
record with the named `consumer` on each of:

| case | consumer | what to record |
|---|---|---|
| `rotated_two_islands` | `titiler` | `/cog/preview` serves the raw unwarped array under north-up `/cog/info` bounds; 13 valid px against a `WarpedVRT` reference of 10. Root cause is rio-tiler's `io/rasterio.py:100` guard, so this record joins the `rio-tiler` one Plan 37 §1.1 adds. |
| `bottom_up_dem_small` | `titiler` | `/cog/info` returns `miny > maxy`; the normalised `/cog/bbox` request then returns **HTTP 500**. |
| `bottom_up_dem_small` | `rio-stac` | `create_stac_item` writes `proj:bbox` unnormalised, so the Item is invalid per the projection extension while its WGS84 `bbox` is correct. |
| `ndvi_scaled_int16_small` | `odc-stac` | declared `raster:bands` `scale` is dropped at `_mdtools.py:125-131`; values are raw DN, 10 000× from stackstac's. |
| `landcover_small` | `titiler` | `/preview.npy` and `.tif` return the dataset's colormap applied, not class codes; the codes are unrecoverable. |
| `optical_dateline_small` | `titiler` | TileJSON `bounds`/`center` and `/info.geojson` carry longitudes > 180; `bounds_to_geometry` handles only the `minx > maxx` convention. |
| `empty_geometry_gpkg` | `lonboard` | `from_geopandas` emits no Arrow validity bitmap, so a NULL geometry is indistinguishable from a NaN-coordinate one. geopandas' own export is the reference. |
| `empty_polygon` | `lonboard`, `geoarrow-pyarrow` | an all-empty frame raises `ValueError: 0-length dimension`; `as_geoarrow` raises an internal `AttributeError` because `infer_type_common` returns `pa.null()`. |
| `geometrycollection_mixed_valid` | `geoarrow-pyarrow` | `as_geoarrow` builds `geoarrow.geometrycollection`, which its own C core rejects with errno 22, instead of the WKB fallback its docstring promises. |

Follow `empty_geometry_gpkg`'s existing record for wording and field use, and
name each `consumer` exactly as a differential run's `consumer=` argument will,
since `_match_known` matches on that alone.

**Do not record** the two stackstac defects against any case. They are not
case-attributable (see *the honest part* above), and a `known_divergences` entry
on an arbitrary case would be a false claim about which case found what.

### 1.2 Gate the conventions, not just the findings

Plan 37 §1.3 proposes `tests/unit/test_transform_conventions.py` for the rotated
and bottom-up affines. Round 2 makes that gate more valuable than Plan 37 could
know — both conventions found defects **again**, in different libraries, and
`bottom_up_dem_small` found two. Extend the same file with the properties round 2
proved load-bearing, each read from the real bytes:

- `ndvi_scaled_int16_small` has `scales != (1.0,)`; `multispectral_s2_like_small`
  has `offsets != (0.0,)`. A regeneration that normalised these away would delete
  the corpus's only coverage of the axis that caught odc-stac.
- `landcover_small` and `landcover_ambiguous_zero_small` carry a colormap.
- `optical_dateline_small` has `bounds.right > 180` (the *unwrapped* convention).
  Normalising it to the wrapped form would silently move it onto the code path
  titiler already handles.

### 1.3 Regenerate and re-gate

`known_divergences` is part of the model, so run
`scripts/build_case_index.py --check`, `scripts/validate_catalog.py`,
`scripts/validate_case_content.py` and `scripts/generate_catalog_pages.py --check`;
regenerate and commit what they name.

---

## Phase 2 — The raster adapter protocol, and the STAC-Item adapter

[`differential.py`](../../src/geocase/differential.py) says it is *"scoped to the
vector / two-code-path shape the evidence covers; the raster adapter protocol is
Phase 4 and is not started."* Two independent runs have now produced raster
defects — Plan 37's two, and round 2's eight — so the entry condition is met and
the scope note is out of date.

Plan 37 Phase 2 specifies the array comparator. This phase adds the piece round 2
proved is missing beneath it.

### 2.1 `geocase.stac` — Items, because two consumers cannot read a file

Neither stackstac nor odc-stac can consume a bare GeoTIFF; both take STAC Items.
The run had to synthesise one per raster case with `rio_stac.create_stac_item`
before it could test anything — and that synthesiser turned out to be **wrong for
`bottom_up_dem_small`**, writing an inverted `proj:bbox`. A corpus whose users
must each write that adapter will each hit that bug, and most will misattribute
it to the consumer.

Ship it:

```python
from geocase.stac import item_for_case, items_for_cases

item = item_for_case("dem_small")            # -> dict, projection extension v1.1 AND v2.0
items = items_for_cases(category="raster")   # -> byte-identical input for every consumer
```

Three requirements the run's hand-built version had to learn:

1. **Emit both `proj:epsg` and `proj:code`.** stackstac reads only the former;
   pystac ≥ 1.13 rewrites it to the latter on `from_dict`. An adapter that emits
   one of them silently excludes a consumer. Emitting both is spec-legal and is
   the only way one Item serves both.
2. **Normalise `proj:bbox`.** Not rio-stac's inverted passthrough — the corpus
   knows its own conventions and should not propagate an invalid Item.
3. **Offer per-band assets *and* a whole-file asset.** stackstac's model is one
   band per asset and it refuses the 9 multi-band rasters; odc-stac reads them.
   Both shapes must be reachable so the difference is a *choice* the harness
   records, not a failure it trips over.

### 2.2 Guardrails, because a differential harness can hang or OOM

The run's first sweep was **killed by the OS after 28 CPU-minutes and 3 GB RSS**,
and a later one had a case that did not return a geobox in 90 seconds. Both were
consumer defects — odc-stac deriving a 3.17 × 10¹² pixel grid, and the same root
cause failing to terminate on an antimeridian source — but a harness that dies
reports nothing at all.

The raster adapter must therefore ship with:

- a **lazy size probe** before any compute, with a documented pixel cap, so an
  absurd derived grid is *recorded as the finding* rather than allocated; and
- a **per-load timeout**, because odc-stac's hang happens while deriving the
  geobox, upstream of any shape a size check could see.

Both are ~15 lines and neither is discoverable until it has cost an afternoon.

### 2.3 Comparison in the common currency

Cross-library raster comparison needs values in one representation. The run
settled on float64 with nodata folded to NaN, which then requires Plan 37 §2.2's
NaN-equals-NaN rule. Note the trap it hit: `.filled(np.nan)` on an *integer*
masked array raises, so the cast must precede the fill. That belongs in the
adapter, not in each consumer's harness.

---

## Phase 3 — Ship the comparison, not just the files

### 3.1 The option-pair matrix

Plan 37 says Phase 2 "must ship documented consumer option-pairs, not just files
and an array comparator". Round 2 is the evidence for what those pairs are worth:
**odc-stac's HIGH defect needed `crs=`**, **stackstac's needed `dtype=`**, and
odc-stac's scale/offset defect needed a scaled case *and* a second library. A
sweep varying only library-vs-library on a plain read — Plan 37's recorded
failure — finds none of the three.

Ship the matrix the run used, as data rather than as prose: default; explicit
CRS (at least two targets, one changing units); explicit resolution above and
below native; explicit bounds; nodata/fill override; dtype override; resampling
nearest vs bilinear; chunked vs single-chunk.

The unit-changing CRS target is the one to call out. It is a single option value,
it found a HIGH defect, and it is the one a consumer author is least likely to
think of testing.

### 3.2 An equality predicate that knows what a CRS is

This is the direct remedy for the five false lonboard findings. `default_compare`
should not treat `OGC:CRS84` and `EPSG:4326` as different CRSs, and no consumer's
harness author should have to discover that they do.

Ship, with tests:

- CRS equality that ignores axis order where the caller asks for it, and that
  resolves CRS84 → 4326;
- geometry comparison that distinguishes **NULL** from **EMPTY** from
  **NaN-coordinate** — round 2 produced three separate defects living exactly in
  the gaps between those three, and a comparator that conflates them cannot see
  any of them;
- mask comparison by **equality**, not truthiness (Plan 37 §2.2 already requires
  this for the same reason: a `mask > 0` comparison stepped over a real defect in
  round 1).

### 3.3 Write down that a divergence needs an explanation, not just a count

The pyproj sweep fired four probes and all four were expected behaviour —
longitude wrapping to [−180, 180], the pole's undefined longitude, sub-micrometre
float noise, and a probe that cannot discriminate when source and target CRS are
the same. Each is recorded in `findings/corpus/pyproj.json` under `explanations`,
**keyed**, so a repeat run classifies them automatically.

That pattern — a machine-readable explanation attached to a divergence class,
not a paragraph in a report — is what `known_divergences` does for cases, and
`differential` should do it for probes. Without it every run re-investigates the
same four, and the fifth, real one is buried.

---

## Phase 4 — The four cases this round could not express

Three from the corrected gap list, plus one the run exposed. **No new
`from_origin` EPSG:32633 baselines** — Plan 37 §3 already says the corpus is
thick there and thin on convention divergence, and round 2 confirms it: the
single rotated raster and the single bottom-up raster found four defects between
them, while the 31 north-up UTM baselines found their defects only in aggregate,
on an option axis.

### 4.1 A multi-item raster group with overlapping footprints

The gap with the most attached evidence. Every geocase raster case is one
standalone file, so the corpus cannot express: stacking order, mosaic
compositing, temporal grouping, or **two assets in one Item**. `odc.stac.load`
and `stackstac.stack` both take a *sequence* of Items and their whole reason for
existing is what happens across that sequence — the run could only ever hand
them a list of one.

Three or four small rasters sharing a CRS with deliberate partial overlap and
distinct constant values, so that "which pixel won" is readable by inspection.

### 4.2 Two assets sharing a band alias

The corpus-unreachable review finding, made reachable. Two assets in one group
both declaring `eo:bands` `common_name: "red"` — the ordinary Sentinel-2 shape —
so that a consumer resolving the alias silently to the first candidate is
*visible*. odc-stac does exactly that today and the source carries its own
`# maybe warn about ambiguity?` note.

This is the strongest argument in the round for the corpus growing an
Item-shaped concept rather than only a file-shaped one, and it should be built
on top of 4.1 rather than beside it.

### 4.3 A second CRS family in the raster set

31 of 34 rasters are EPSG:32633, which makes any "same case, two CRSs" assertion
untestable and leaves reprojection sweeps leaning entirely on the *target* CRS
for variation. A matched pair — the same footprint written in a projected CRS and
in a geographic one — makes the unit-change axis that caught odc-stac assertable
from inside the corpus, rather than only via an external consumer's option.

Prefer a **pair with a declared relationship**, following
`utm_zone_33n_to_32n_pair` and `crs_mismatch_overlay_pair`
([Plan 36](36-rc3-release-runbook-and-crs-mismatch.md) §2): a divergence that is
a relationship between two inputs is not expressible by two independently
selectable cases.

### 4.4 A second rotated raster

`rotated_two_islands` is now 2-for-2 across two runs and three libraries, and it
is still the only one of its kind. A second — different skew sign, different
pixel size, ideally non-square pixels — turns a single point into an axis, and
distinguishes "handles rotation" from "handles *this* rotation".

Non-square pixels are worth folding in deliberately: the run found that
`nonsquare_diagonal_sparse` exposes an API asymmetry (a scalar `resolution=`
cannot express them, so a harness that passes one silently squares the grid).
That was the harness's bug, but the corpus is what made it visible.

### 4.5 Explicitly *not* proposed

- **A scale/offset raster.** Three exist and one found a defect.
- **A nodata-that-is-also-valid raster.** Seven exist; [Plan 32](32-footprint-truth-and-ambiguous-zero.md) built them.
- **A palettised raster.** Two exist and they found titiler's data-loss defect.
- **More format baselines.** Third run in a row where none found anything.

---

## Phase 5 — Close the loop upstream, and test the premise

[Plan 37](37-raster-signal-and-differential-adapters.md) Phase 4 set the shape:
the defects belong to the consumers, and geocase's obligation is the
reproduction and the record. Round 2 adds a second obligation, because it is now
the third run in a row to conclude the corpus works **without a single external
party having said so**.

### 5.1 File a sample, not the whole batch

Seventeen ready-to-paste drafts sit in
`/Users/farzinashouri/projects/geocase_validator/issues/`. **File three**, not
seventeen:

- `odc-stac-crs-without-resolution-units.md` — the most severe, with a
  self-contained repro and a named root cause at `_mdtools.py:1166-1181`.
- `titiler-invalid-format-500.md` — the cheapest to accept: a one-line
  `DEFAULT_STATUS_CODES` addition.
- `stackstac-proj-code-unsupported.md` — the most broadly felt, since it breaks
  the library's own documented `item_collection()` workflow.

Three is deliberate. A batch of seventeen from an unknown reporter reads as
automated output and gets triaged as a unit; three well-formed reports with
working reproductions get read individually. Every draft is standalone and
imports only the library under test, so none asks a maintainer to install
geocase.

**The reason this is a phase and not an afterthought:** maintainer response is
the only evidence available about whether anyone outside this repository values
the output. Three runs have now established that the corpus finds real defects.
Zero have established that anyone wants them. That asymmetry is the largest open
risk in the project and it is also the cheapest to reduce — the reports are
already written.

Record what comes back — accepted, fixed, disputed, ignored — against each draft.
A dispute is more informative than silence and much more informative than
another validation round.

### 5.2 Record the outcome where the claim lives

`docs/geocase_validate/` holds the prior external runs and is what
[Plan 28](28-validate-geocase.md) reasons from. Add round 2's report beside them,
and add a line to Plan 28's verdict table recording that six further consumers
were tested and what was found. Plan 37 asks the same for round 1; both should
land together so the table reads as one sequence rather than two.

### 5.3 The distribution question — flagged, not resolved here

Round 2 surfaced a packaging question this plan is the wrong place to settle:
**nobody downloads a corpus, but people do add a dev-dependency.** The findings
argue that the natural delivery shape is a `pytest` fixture pack a library adds
to its own CI in one line — which would put `rotated_two_islands` and
`bottom_up_dem_small` in front of exactly the five suites shown above to have no
coverage of them — rather than a dataset a consumer must discover, download and
write a harness against.

That belongs to [Plan 25](25-ship-geocase-as-a-package.md) and
[Plan 21](21-adoption-action-plan.md), not here. Recorded so the input is not
lost: **this round's strongest adoption argument is that the corpus's best cases
are missing from the test suites of every library it was run against**, and a
fixture pack is the delivery mechanism that acts on that directly.

---

## Verification

- `tests/unit/test_known_divergences.py` asserts a record for each of the nine
  case/consumer pairs in §1.1, and fails first on an empty list.
- `tests/unit/test_transform_conventions.py` reads real bytes and fails if
  `ndvi_scaled_int16_small` loses its scale, `optical_dateline_small` is
  normalised to the wrapped convention, or either palettised case loses its
  colormap.
- `geocase.stac.item_for_case("bottom_up_dem_small")` emits a **min/max-ordered**
  `proj:bbox`, and every emitted Item carries both `proj:epsg` and `proj:code`.
  A test asserts `stackstac`-shaped and `pystac`-shaped consumption of the same
  Item both find a CRS.
- The raster adapter refuses to allocate a grid above its documented cap and
  records it as a finding; a load that exceeds the timeout is recorded, not
  raised.
- `default_compare` reports `OGC:CRS84` and `EPSG:4326` as the same CRS, and
  distinguishes NULL from EMPTY from NaN-coordinate geometries. Regression test
  built from the lonboard false-positive case.
- `scripts/validate_catalog.py`, `scripts/validate_case_content.py`,
  `scripts/build_case_index.py --check` and
  `scripts/generate_catalog_pages.py --check` are green after every phase.
- `mkdocs build --strict` passes with this plan and its `index.md` entry added.
- **Phase 5.1 is the exception to the round's "nothing is filed" rule, and it is
  deliberate.** The run itself filed nothing; this plan *proposes* filing three
  of the seventeen drafts, with the outcome recorded against each. The remaining
  fourteen stay unfiled pending what those three return.
- Plan 28's verdict table names round 2, its six consumers and the date, so a
  reader of the premise sees the evidence that has accumulated against it.
- The upstream test-coverage table in Context is reproducible from the recorded
  commits, and its stated method limit (keyword probe, not semantic audit) is
  carried with it wherever it is quoted.

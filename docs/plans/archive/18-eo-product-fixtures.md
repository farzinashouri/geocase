# Plan 18 — EO product fixtures: the input is *not* cheap

## Context

Plan 14 rejected the corpus-as-product thesis on one sentence:

> **The input is the cheap part.** A dateline-crossing polygon is six lines of Shapely and a
> 2 KB commit — ten minutes, once.

**That was reasoned entirely on vector geometry and never re-tested for raster.** For a
Sentinel-2 L2A stack or a Sentinel-1 GRD scene it is likely false: you cannot write one inline
in a unit test, and neither can a coding model. That is the gap this plan investigates — the
main obstacle to unit-testing raster-intensive applications is not the assertion, it is
*having a realistic product to assert against*.

### Why this survives the objection that killed Plan 14

Step 0 (2026-08-09) found agents got 9/10 geospatial operations right, and the benchmark runs
since show **zero silent failures on raster**. Reasoning-based traps are largely closed.

But Plan 14 conceded exactly one surviving category:

> **What is unaffected.** Anything depending on facts a model cannot have.

EO product specifications are that category. Sentinel-2 baseline 04.00's `BOA_ADD_OFFSET` of
−1000, the quantification value of 10000, which bands are native 10/20/60 m, the SCL class
codes, S1 GRD's amplitude-vs-dB convention — these are **lookup facts, not derivable ones**. A
model asked for an S2 fixture emits something plausible with the wrong offset, because −1000 is
something you know or you don't. No amount of reasoning recovers it.

That is a materially better-founded claim than "models write silently-wrong geometry code,"
which Step 0 already refuted.

### What the corpus actually contains today — the finding that reshapes this plan

The argument is sound in principle but **does not apply to the fixtures currently bundled**.
Measured directly with rasterio during planning:

| Fixture | Declared | Actual bytes |
|---|---|---|
| `multispectral_s2_like_small` | S2-like | 4 bands (not 13), uint16, **scales=(1,1,1,1)** — no 10000 quantification, no −1000 offset, 16×16 |
| `multispectral_mixed_resolution_small` | `risk_types: resolution_mismatch` | all three bands at **10 m**; band named `swir_20m` but resampled onto one grid, so no mismatch exists to mishandle |
| `sar_vv_small`, `sar_dualpol_small` | SAR VV/VH | plain float32 arrays, **nodata=None**, no dB-vs-linear, no calibration, no border noise |
| all seven product families | EO products | **`tags={}`** — zero product metadata |

These are 16×16 arrays with EO-flavoured band descriptions. A model produces any of them in
~15 lines of rasterio. **"AI can't build these" is false of these files.** The corpus does not
currently embody the thesis it would need to embody.

**The gap between those two facts is the entire opportunity**, and it is unbuilt.

### Intended outcome

A `geocase.synth` generator producing spec-accurate synthetic EO products at unit-test scale,
with its outputs committed as the corpus fixtures so the corpus becomes reproducible from
audited code. Gated on one measurement that can kill it.

---

## Phase 0 — The gate

**Blocks everything below.** The premise is directly testable with the harness that already
exists, and testing it costs a day.

New benchmark task `s2_fixture`, `trap_category: product-spec`:

```
make_s2_l2a_fixture(path, size=32) -> None
```

Prompt (neutral): *create a small synthetic Sentinel-2 L2A product as a GeoTIFF suitable as a
unit-test fixture, covering the four 10 m bands, for processing baseline 04.00.* Naming the
product **is** the specification — that is legitimate contract, not a leaked hint. Everything
graded below is a lookup fact the product name implies.

Scoped to the four 10 m bands (B2/B3/B4/B8) so one GeoTIFF suffices; real L2A is per-band JP2
at three resolutions, which is not gradeable in a single file.

- **control** — opens with rasterio; 4 bands; `uint16`; a UTM CRS; 10 m pixels. Every model
  should pass this; it isolates the trap from rasterio fluency.
- **edge** — `nodata == 0`; band `scales == 10000`; **`offsets == -1000`** (baseline 04.00).
  The offset is the sharp, obscure, checkable fact and the headline number.

No corpus fixture is needed: the oracle is the published spec, so this task is free of the
trap-2 problem entirely.

### Decision rule, fixed in advance

| Result | Action |
|---|---|
| Models systematically omit the offset/quantification across ≥2 families | **Premise confirmed.** Build Phase 1. |
| Models reliably emit spec-accurate fixtures | **Premise refuted — stop.** They can do it on the fly, which is the negation of the claim. Keep the task; it is a good benchmark task regardless. |
| LOUD/MISSING dominant | Measuring rasterio fluency, not spec knowledge. Tighten the prompt's contract and re-run **before** concluding anything. |

The third row is live: existing `zonal_mean` results are already LOUD-dominant, which is that
signature.

### Gate verdict (2026-08-12) — row 1, with a capability-tier boundary

The task was built and run. Valid trials (API 429s and one truncated reply excluded):

| Model | Tier | Control | Edge |
|---|---|---|---|
| Claude Opus 5 (clean-room, ×2) | frontier | PASS | **PASS** — `scales=1e-4`, `offsets=-0.1`, tags `-1000`/`10000` |
| Claude Sonnet 5 (clean-room) | frontier | PASS | **PASS** — tags `BOA_ADD_OFFSET=-1000`, quantification `10000` |
| Claude Haiku 4.5 (clean-room) | small | PASS | SILENT — `scales=(1,…)`, `offsets=(0,…)`, `tags={}`, no nodata |
| openai/gpt-oss-20b:free (×2) | small | PASS | SILENT — identical shape |
| nvidia/nemotron-3-ultra-550b:free | free | PASS | SILENT — identical shape |

**Row 1 is met** — ≥2 families systematically omit the radiometry, and the misses are
byte-for-byte the shape of the fixtures already in the corpus (flat scale, zero offset, empty
tags). Row 3 does not fire: every model that returned runnable code passed the control.

**But the premise as stated above is refuted for frontier models.** Opus and Sonnet emit the
baseline 04.00 radiometry unprompted; −1000 *is* in their weights. Two consequences:

1. Phase 1 proceeds, justified as closing a gap for **small/cheap models** (and by the corpus's
   independently false `risk_types` labels) — not under "AI can't build these".
2. The grader's encoding rule as originally drafted here (`scales == 10000`,
   `offsets == -1000`) was itself wrong — trap 1 fired on first contact. In GDAL's
   `value = raw*scale + offset` convention the self-consistent form is `1e-4`/`-0.1`, and real
   granules carry the numbers in `MTD_MSIL2A.xml` tags with *no* GDAL scale/offset at all. The
   shipped grader accepts the fact in either encoding; the first draft would have scored
   spec-correct frontier output SILENT and confirmed the premise on a measurement artifact.
   Verification item 6 below is corrected accordingly.

---

## Phase 1 — `geocase.synth` (only if the gate confirms)

### Layout

- `src/geocase/synth/spec.py` — every constant, each **citing spec document, version and
  section inline at the constant**
- `src/geocase/synth/sentinel2.py` — `sentinel2_l2a(size=32, bands=..., baseline="04.00", nodata_border=False, scl=False)`
- `src/geocase/synth/sentinel1.py` — `sentinel1_grd(size=32, pol="VV+VH", units="dB"|"linear", border_noise=False)`
- `src/geocase/synth/__init__.py` — flat re-export

Parameterisation is the reason this is a generator and not a file set: a unit test wants a
32×32 product with real structure, and the useful axes (baseline, polarisation, dB vs linear,
nodata border present or absent, SCL on or off) are combinatorial. Static files cannot span
them; a generator can, and its correctness lives in one audited place.

### Corpus regeneration

Extend `scripts/generate_raster_fixtures.py` to emit the product fixtures **from the
generator**, keeping its existing `--check` reproducibility gate. The seven thin product
fixtures above are regenerated with real fidelity; the generator becomes the single source of
truth and `--check` catches drift.

Byte changes invalidate any `sha256` pin in `benchmark/tasks/*/task.yaml` — **no current task
references these cases**, so the blast radius is nil today, but re-run
`tests/benchmark/test_fixture_isolation.py` and `test_results_pin.py` to confirm.

### The hard part — how do we know *our* fidelity is right?

This is the plan's central risk and it must not be waved past. A hand-written "spec-accurate"
fixture is only worth depending on if the fidelity is verified, otherwise it is Plan 13's
defect wearing a better costume — and `multispectral_mixed_resolution_small` already carries
`risk_types: resolution_mismatch` on a file with no resolution mismatch, which is that failure
in miniature.

Two mechanisms, both required:

1. **Cite the spec at every constant.** Document, version, section — in code, next to the
   value, not in prose elsewhere.
2. **Vendor a real product's metadata as the witness.** A genuine `MTD_MSIL2A.xml` (a few
   hundred KB; Copernicus data is free and open, so redistribution is fine) committed under
   `tests/synth/data/`, with `tests/synth/test_spec_fidelity.py` asserting our constants match
   what the real granule declares. This makes fidelity **machine-checked against the actual
   authority** rather than against the author's reading of a PDF. Do the same for an S1 GRD
   annotation XML.

Mechanism 2 is what makes the whole plan defensible. Without it this is one person's reading
of a spec, asserted confidently — the exact shape of the defect the project is named after.

---

## Files

**New:** `src/geocase/synth/{__init__,spec,sentinel2,sentinel1}.py`;
`src/geocase/benchmark/tasks/s2_fixture/{task.yaml,prompt.md,probe.md,grader.py}`;
`tests/synth/test_spec_fidelity.py`; `tests/synth/data/` (vendored real metadata)

**Modified:** `src/geocase/benchmark/taxonomy.py` (add `product-spec` to
`GEO_TRAP_CATEGORIES` — `TaskMeta` validates against it and rejects otherwise);
`tests/benchmark/test_oracles.py` (GOOD/TRAPPED pair, auto-enrolled via
`NEW_TASKS = sorted(GOOD)`); `scripts/generate_raster_fixtures.py`; the seven product
`case.yaml` files (assertions updated to the real scale/offset/nodata)

**Not touched:** `footprint_edge_cases/*_footprint.geojson` — `notes.md` records them as
"generated by the GDAL footprint utility", i.e. recorded tool output, not an independent
answer. Grading against them measures agreement with `gdal_footprint` (Plan 15, trap 2). The
`.tif` files are fine as input; the `.geojson` files must never be read by a grader.

---

## Traps

1. **Our spec constants are themselves an oracle.** Mechanism 2 above is not optional. Getting
   −1000 wrong ships a corpus that lies with more confidence than the current one.
2. **Naming the product is contract; naming the *fact* is a leak.** `prompt.md` may say
   "Sentinel-2 L2A, baseline 04.00". It must never say "remember the offset" or mention
   scale/offset at all. (Plan 14, trap 6.)
3. **Baseline 04.00 is a dated change** (products from 2022-01-25). The generator must take
   `baseline` as a parameter and produce *no* offset for earlier baselines, or it encodes a
   different wrong answer.
4. **Do not regenerate the corpus before the gate reports.** The gate is binding.
5. **Scope discipline.** S2 L2A and S1 GRD only. Landsat, MODIS, PlanetScope and the rest are
   how this becomes an unbounded product-catalog project — the failure mode Plan 14's risk
   section names.
6. **Task count changes break naive cross-run comparison** — Plan 17 already requires per-task
   intersection; confirm `run_report.py` states it.

---

## Verification

```bash
# 1. Oracle correctness before any model is measured — TRAPPED must return SILENT, not LOUD
python -m pytest tests/benchmark/test_oracles.py -q -k s2_fixture

# 2. Prompt neutrality — must print nothing
grep -rniE "offset|scale|quantific|nodata|trap" src/geocase/benchmark/tasks/s2_fixture/prompt.md

# 3. RUN THE GATE: >=3 model families, >=2 trials. Apply the decision rule before Phase 1.
#    (flags corrected from the draft: it is --config, and --domain is required
#    now that a second domain exists)
python -m geocase.benchmark run --config configs/models-free-gate18.yaml --domain geo --tasks s2_fixture --trials 2

# --- everything below only if the gate confirms ---

# 4. Our fidelity is checked against a REAL granule, not against our own reading
python -m pytest tests/synth/test_spec_fidelity.py -q

# 5. Corpus is reproducible from the generator
python scripts/generate_raster_fixtures.py --check

# 6. The regenerated fixtures actually carry fidelity now. NOTE: corrected from
#    the draft, which asserted scales==10000/offsets==-1000 — arithmetically
#    wrong under GDAL's value = raw*scale + offset convention (trap 1, caught
#    by the gate run). The self-consistent band form is 1e-4 / -0.1.
python -c "
import rasterio
with rasterio.open('src/geocase/data/core/raster/multispectral_s2_like_small/multispectral_s2_like_small.tif') as s:
    assert s.scales == (1e-4,)*s.count, s.scales
    assert s.offsets == (-0.1,)*s.count, s.offsets
    assert s.nodata == 0
    t = s.tags()
    assert t.get('BOA_ADD_OFFSET') == '-1000', t
    assert t.get('QUANTIFICATION_VALUE') == '10000', t
print('fidelity present')
"

# 7. Nothing downstream broke
python -m pytest tests/benchmark/test_fixture_isolation.py tests/benchmark/test_results_pin.py -q
python -m pytest tests -q

ruff format --check src tests && ruff check src tests && mypy src
```

Item 4 matters most. If our constants are not checked against a real product, this plan ships
a more confident version of the defect it exists to fix.

---

## Also available, deliberately not in this plan

Three silent-failure raster traps verified against real corpus bytes during planning, all
currently untested by any task: rotated affine on `rotated_two_islands.tif` (naive drops the
b/d terms → 32.6 m error, in-bounds and in the right CRS); non-square pixels on
`nonsquare_diagonal_sparse.tif` (60×30 m → area exactly 2× wrong); int16 scale/offset on
`ndvi_scaled_int16_small.tif`. These are cheap tasks and they close the
`affine_transform_quirk` gap that [`development-plan.md:475`](../development-plan.md)
records as promised-and-never-delivered. They belong to the *silent-failure* thesis, not the
*fixture-fidelity* thesis, so they are kept separate rather than bundled in to pad this plan.

---
description: "Find bugs in a library by reading every case two ways and comparing — the mode that found two real defects in pyogrio and GDAL."
---

# Differential testing

Most of this documentation describes one mode: load a case, run your function,
assert it did the right thing. This page describes a different one, and the
evidence says it is the more productive of the two.

An independent validation run pointed geocase's vector corpus at
[pyogrio](https://pyogrio.readthedocs.io/) and found two real defects — a crash
in `read_dataframe(fid_as_index=True, use_arrow=True)`, since patched upstream,
and a GPKG spatial-filter divergence traced into GDAL's `GetArrowStream` and
filed there. **Both came from comparing pyogrio against itself**, not from any
assertion geocase declares:

> The most productive thing built here was ~100 lines: read every case two
> ways, compare, report divergences.

`geocase.differential` is that harness, shipped.

## Why it works without an oracle

In declared-assertion mode, geocase has to know the right answer. That caps
what it can catch at what a curator thought to write down.

In differential mode **neither path is the oracle**. You point two things that
*ought* to agree at the same bytes, and the finding is the disagreement. That
works on questions geocase has no opinion about, which is why it found bugs in
a mature, widely-used library where assert-against-declared-truth found none.

Anything with two code paths qualifies:

| Left | Right |
|---|---|
| `use_arrow=False` | `use_arrow=True` |
| eager read | lazy / chunked read |
| the C implementation | the pure-Python fallback |
| the version you ship | the version you are about to ship |
| your library | a second library that should agree |

## The shortest useful run

```python
from functools import partial

import pyogrio

from geocase.differential import compare_cases, summarize

results = compare_cases(
    left=partial(pyogrio.read_dataframe, use_arrow=False),
    right=partial(pyogrio.read_dataframe, use_arrow=True),
    consumer="pyogrio",
    category="vector",
)

print(summarize(results))
for result in results:
    if result.outcome == "diverged":
        print(result.case_id, result.detail)
```

A reader is any callable taking the path to a case's primary file. Keyword
arguments beyond the documented ones — `category`, `include_ids`,
`risk_types_any`, and the rest — are forwarded straight to
[`geocase.list_cases`](case-discovery.md), so selection is the catalog's own
and not a second thing to learn.

The runnable version is
[`examples/test_differential_pyogrio.py`](https://github.com/farzinashouri/geocase/blob/main/examples/test_differential_pyogrio.py).

## The four outcomes

| Outcome | Means |
|---|---|
| `agree` | Both paths produced the same result — **or both raised the same way**. A curated-failure case is agreement: the two paths agree that it fails. |
| `diverged` | The finding. They disagree, and nothing on the case says they should. |
| `known` | They disagree, and the case's `known_divergences` already records it for this consumer. Investigated, not silenced. |
| `errored` | Exactly one path raised. Distinct from `diverged` because a crash and a wrong answer need different triage. |

Two of these are worth dwelling on.

**Both paths failing identically is `agree`, not `diverged`.** Otherwise every
case in the corpus that is *meant* to fail reports a finding, and the noise
hides the real ones.

**Exactly one path raising is `errored`, not `diverged`.** It is very often the
most interesting result in the run — the pyogrio `fid_as_index` crash surfaced
exactly this way — but it needs to be visibly a crash rather than filed
alongside "these two row counts differ".

## Filter to what your reader can actually open

Run an OGR-based reader over the whole vector corpus unfiltered and 20 of 113
cases report `errored` for a reason that is not your library's fault: 13 are
bare WKB/WKT geometry blobs that no OGR driver opens at all, and 7 need
`libgdal-arrow-parquet`. `required_drivers` makes that predictable *before*
reading:

```python
available = set(pyogrio.list_drivers())
openable = [
    case
    for case in geocase.list_cases(category="vector")
    if all(driver in available for driver in case.assertions.required_drivers)
]

results = compare_cases(left=..., right=..., cases=openable)
```

The empty-string sentinel in that field is falsy on purpose, so the filter above
excludes the bare-blob cases without you needing to know it exists.

Do **not** reach for `loader_hint` here. It names the reader geocase itself
dispatches to and marks all 113 vector cases `geopandas`, so it cannot answer
"can *my* reader open this?".

## Making repeat runs cumulative

The GPKG divergence will reproduce for every user until GDAL fixes it. Without
somewhere to record that, the next person re-investigates from scratch — and,
worse, cannot tell a newly introduced bug on that case from the one already
understood.

So it is recorded on the case, and `compare_cases` consults it:

```python
result = ...  # empty_geometry_gpkg, read under a bbox both ways
result.outcome                      # "known"
result.known_divergence.consumer    # "pyogrio"
result.known_divergence.upstream_url
```

A record only excuses the consumer it was recorded against, and only when you
pass `consumer=`. Omit it to opt out of the catalogue entirely, which is what
you want when auditing whether the recorded divergences are still real. See
[Adding a case](adding-a-case.md) for the metadata block.

## Teaching it what to ignore

The default comparison understands GeoDataFrames — row count first, then
columns, then values, because "2 rows against 3" is a more useful sentence than
a dump of two frames. It treats `None`, `NaN`, `NaT` and `NA` as the same
missing value, since no two readers agree on which to return and the difference
is noise. It stops there: `""` and `0` are values a reader genuinely returned,
and equating them to absence would hide a real defect.

Real runs meet more noise than that. pyogrio's two paths, for instance, produce
`object` dtype and pandas `str` dtype for the same KML text field. Pass your own
`compare=` — it takes the two results and returns a description of the
difference, or `None` when they agree:

```python
def compare_ignoring_dtypes(left, right):
    if len(left) != len(right):
        return f"row count differs: {len(left)} vs {len(right)}"
    if list(left.columns) != list(right.columns):
        return f"columns differ: {list(left.columns)} vs {list(right.columns)}"
    return None


results = compare_cases(left=..., right=..., compare=compare_ignoring_dtypes)
```

Narrow the comparison deliberately, and write down why. A harness that ignores
too much reports a clean run over a corpus it never really examined — the same
false green the [content gate](adding-a-case.md) exists to prevent on the
metadata side.

## Guardrails: a harness that dies reports nothing

The round-2 run's first sweep was killed by the OS after 28 CPU-minutes and
3 GB of RSS, because odc-stac derived a 3.17 x 10^12 pixel grid from an
antimeridian source. A later sweep had a case that did not return a geobox in
90 seconds. Both were consumer defects — and in both, the defect destroyed the
report that would have named it.

`guarded_reader` wraps a reader with the two protections that costs an
afternoon to discover:

```python
from geocase.differential import compare_cases, compare_arrays, guarded_reader

results = compare_cases(
    left=guarded_reader(read_odc, size_probe=probe_geobox, timeout=90),
    right=guarded_reader(read_stackstac, timeout=90),
    compare=compare_arrays,
    consumer="odc-stac",
    category="raster",
)
```

- **A lazy size probe.** `size_probe` is called with the path *before* the
  reader and returns the shape the read would produce. Over
  `max_pixels`, the read never happens and `PixelBudgetError` is raised — so
  the absurd grid is recorded as the finding rather than allocated.
- **A per-load timeout.** odc-stac's hang happens while *deriving* the geobox,
  upstream of any shape a size check could see, so a size probe alone does not
  save the run. Over `timeout` seconds, `ReaderTimeoutError`.

Both surface through `compare_case` as ordinary reader exceptions, which is the
point: the run continues, and the number appears in the report.

## Comparing rasters in a common currency

Cross-library raster comparison needs values in one representation.
`to_common_currency` is the one the round-2 run settled on — float64, with
nodata folded to NaN — and it pairs with `compare_arrays`, whose NaN-equals-NaN
rule is what makes two readers' different fill values agree instead of
producing a finding per nodata pixel:

```python
from geocase.differential import compare_arrays, to_common_currency

left = to_common_currency(odc_array, nodata=-9999)
right = to_common_currency(stackstac_array, nodata=0)
compare_arrays(left, right)  # None
```

It absorbs one trap in particular: `.filled(np.nan)` on an **integer** masked
array raises, so the cast to float64 has to precede the fill. That belongs in
the adapter, not in every consumer's harness.

## Vary an option, not just a library

Round 2 is the evidence for what an option axis is worth. **odc-stac's HIGH
defect needed `crs=`**, **stackstac's needed `dtype=`**, and odc-stac's
scale/offset defect needed a scaled case *and* a second library. A sweep
varying only library-against-library on a plain read finds none of the three.

The eight axes that run used ship as data, in `OPTION_PAIRS`:

```python
from geocase.differential import option_pairs

for pair in option_pairs(found_defect=True):
    print(pair.name, pair.left, "vs", pair.right, "--", pair.evidence)
```

`default`, `explicit_crs`, `resolution`, `bounds`, `nodata`, `dtype`,
`resampling`, `chunking`. The option *keys* follow odc-stac / stackstac
spelling; map them if your consumer names things differently — the value here
is the enumeration of axes, not the keyword strings.

The one to call out is the **unit-changing CRS target**. It is a single option
value, it found a HIGH defect, and it is the axis a consumer author is least
likely to think of testing. The
[CRS family pair](_generated/catalog/cases/crs_family_pair_projected.md) makes
it assertable from inside the corpus as well.

## A predicate that knows what a CRS is

Round 2 produced **five false findings** against lonboard for one reason: the
harness thought `OGC:CRS84` and `EPSG:4326` were different CRSs. `crs_equal`
is the remedy, and `default_compare` uses it on any CRS-shaped mapping:

```python
from geocase.differential import crs_equal

crs_equal("OGC:CRS84", "EPSG:4326")   # True
crs_equal(4326, "epsg:4326")          # True
crs_equal("EPSG:4326", "EPSG:32633")  # False
crs_equal(None, "EPSG:4326")          # False -- a missing CRS is not every CRS
```

Geometries need the same care in a different place. `compare_geometries`
distinguishes **NULL** from **EMPTY** from a **NaN-coordinate** geometry,
because round 2 produced three separate defects living exactly in the gaps
between those three. A comparator that folds them into "missing" reports
agreement on all three; one that folds them into "different" reports a finding
on every curated empty geometry in the corpus.

## Explain a divergence class once

The pyproj sweep fired four probes and all four were expected behaviour:
longitude wrapping to [-180, 180], the pole's undefined longitude,
sub-micrometre float noise, and a probe that cannot discriminate when source
and target CRS are the same. Without a record, every run re-investigates the
same four and the fifth, real one is buried.

`known_divergences` does this for *cases*; `PROBE_EXPLANATIONS` does it for
*classes*. Pass `explain=True` and a matched divergence is reported as `known`
with its explanation attached:

```python
results = compare_cases(left=..., right=..., explain=True, category="vector")

for result in results:
    if result.outcome == "known" and result.probe_explanation:
        print(result.case_id, result.probe_explanation.key)  # e.g. longitude_wrap
```

It is off by default: a caller who did not ask should see the raw divergence,
because an explanation that fires unasked is indistinguishable from a
comparator bug. A catalogued `known_divergence` still wins when both apply,
because it is the more specific statement.

## Where the corpus pays off

The distribution of the pyogrio run's findings is the most useful thing it
reported. Both bugs came from cases built around a **named failure mode** —
`dateline_chain_cluster` and `empty_geometry_gpkg`, both under `vector/special/`
— and neither came from the ~60 `*_baseline` files, which contributed runtime.

If you are choosing where to point a differential harness first, start with
`risk_types_any=[...]` rather than the whole catalog.

## Related docs

- [Case discovery](case-discovery.md) — the selectors `compare_cases` forwards to
- [Adding a case](adding-a-case.md) — `required_drivers`, `known_divergences`
- [Testing your function](testing-your-function-with-geocase.md) — the declared-assertion mode
- [STAC Items](stac-items.md) — feeding stackstac and odc-stac from the corpus

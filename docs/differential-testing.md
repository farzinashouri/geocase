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

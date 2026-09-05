# Phase 2 — the fixture gate

**Status: open. No interviews recorded yet. Phase 3 fixture work other than the
nodata carve-out does not start until this reports.**

Five conversations, no code, decision rule pre-committed below. This is the
Phase 2, and it exists because of one sentence in Rejector B's closing caveat:

> Ask prospective adopters what's actually preventing their raster tests today.
> It's often dependency injection, not fixture fidelity. Knowing that early
> saves you from building for a problem your users don't have.

Their own blocker was a hardcoded absolute path to a 1.5 GB coastline file
inside the function under test. **No fixture library can fix that.** If that
pattern is the norm, most of the remaining plan is building for a problem its
users do not have — and that is knowable for the price of five conversations.

## The question

Ask exactly this, open, and record the answer verbatim:

> **What stops you unit-testing your raster code today?**

**Do not ask "would fixtures help you?"** That measures politeness (trap 5). The
question must not name fixtures, geocase, or any candidate answer. Let them
volunteer the obstacle. Same discipline as Plan 14 trap 6 and Plan 18 trap 2,
applied to humans instead of models.

Mixed sample: compute-side (code that computes on pixels) and read-side (code
that reads rasters and does something else with them). Read-side is the larger
population and is under-represented in the evidence so far.

## Recording

One file per interview, `NN-short-slug.md`, using `TEMPLATE.md`. Verbatim
answer first, classification second — in that order, so the classification is
visibly derived from what they said rather than the other way round.

Classify into exactly one primary category:

| Category | Meaning |
|---|---|
| `fixture-fidelity` | Their test data does not resemble real products enough to catch what breaks |
| `dependency-injection` | Hardcoded paths, un-injectable I/O, no seam to insert test data |
| `environment` | GDAL/PROJ/QGIS installation, container, or CI environment problems |
| `output-assertion` | They can make inputs, but cannot assert the output is right |
| `none` | "Nothing, we test fine" |

## The decision rule, fixed in advance

| Result | Action |
|---|---|
| ≥3 of 5 `fixture-fidelity` or `output-assertion` | Build Phase 3 as scoped. |
| ≥3 of 5 `dependency-injection` | **Do not build the generator** beyond the nodata carve-out. Ship Phase 1 only, publish the finding. Consider whether the honest deliverable is a short piece on testable-raster-code structure rather than a package. |
| Split / `environment`-dominant | Nodata fixture only, then stop pending a second adopter. |

If `output-assertion` scores ≥3 of 5, it displaces vector fixtures (§3.4) in
priority — that is the one category with a live gap and no existing seed beyond
`assertions/footprint.py`.

## What is NOT gated by this

The **nodata fixture** is exempt. Tier 1 rows 1–3 (nodata border, ambiguous
zero, all-nodata/degenerate stats) carry 3/3 convergence and a confirmed live
bug in the only compute-side adopter. That evidence does not weaken because five
maintainers answer a question about a different obstacle. It is built already —
see `geocase.raster`.

Everything else in Phase 3 waits: presets, vector fixtures, `geocase.granule`,
output assertions.

## Honesty note

Two hazards this project called severe have deflated on contact with
measurement: Plan 14's Step 0, and the BOA offset claim. Assume this gate can
produce an answer that kills work already half-wanted, and record it anyway. The
value of a pre-committed rule is that it binds when the answer is inconvenient.

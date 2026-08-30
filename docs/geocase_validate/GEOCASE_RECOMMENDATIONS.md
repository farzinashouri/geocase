# Recommendations for `geocase`

**Date:** 2026-08-26
**Basis:** validation of geocase 1.0.0rc2 against rio-tiler 9.4.3 (see
[`GEOCASE_VALIDATION_REPORT.md`](./GEOCASE_VALIDATION_REPORT.md)), plus the earlier
pyogrio run.

> Scope note: this file is an evaluation artifact produced while using this repository as a
> test target. It is not upstream rio-tiler documentation, and the `rio_tiler/` package was
> not modified.

---

## The core diagnosis

Every defect found in both exercises came from **comparing two independent implementations,
or checking a property that must hold regardless of the answer.** Zero came from comparing a
file to its own declared metadata.

Meanwhile, a control-arm agent forbidden from touching geocase reproduced the headline
finding (sheared geotransforms) in ~90 seconds using self-authored `rasterio` fixtures, and
went on to find five further defects the geocase-driven run never surfaced.

So the files are not the moat, and the current packaging puts the files at the center.

**The pivot: geocase should ship generators and oracles, not a file corpus.**

---

## 1. Ship property / metamorphic oracles — this is the product

Most geospatial bugs are invisible to "is this value right?" but loud under "does this
relation hold?". Two *generic* properties would have caught two of the rio-tiler bugs with
no fixture curation at all.

**API purity** — a query must not mutate its receiver:

```python
before = deepcopy(img)
img.statistics()
assert img == before
```

That is exactly defect C (`ImageData.statistics()` rewriting NaN → 1e20 in place).

**Band-permutation equivariance** — `read(indexes=(3,1))` must equal `read()[[2,0]]`,
*including metadata*:

```python
assert r.read(indexes=(3, 1)).band_descriptions == [d[2], d[0]]
```

That is exactly defect B (the leaked loop variable in `reader.py:322`).

Others worth shipping for the raster/tiling domain:

| property | catches |
|---|---|
| `part(full_bounds) == read()` | window arithmetic |
| reprojection round-trip A→B→A within tolerance | accumulating warp error |
| 4 child tiles at z+1 mosaic ≈ parent tile at z | tile-grid registration (would have caught defect F) |
| translation equivariance: shift the geotransform, output shifts identically | window/offset bugs — **you already ship the `_shifted` pair and never use it as an oracle** |
| rotation equivariance: rotate fixture 90°, output rotates | shear/affine handling (defect A) |
| nodata-value relabelling leaves valid pixels unchanged | mask/nodata conflation (defects D, E) |
| overview read ≈ full-res read decimated | overview-selection bugs |
| statistics invariant to read path (`read` vs `part` vs windowed) | internal consistency |

These are library-agnostic. Express them once against an adapter interface and they run
against rio-tiler, rasterio, GDAL, rioxarray, or anything else.

## 2. Own the differential infrastructure

An ad-hoc agent can write one differential. What it will not do is maintain a **version
matrix**. That is the defensible ground:

- **Cross-implementation** — rio-tiler vs rasterio vs GDAL CLI vs rioxarray;
  pyogrio vs fiona vs ogr.
- **Cross-version** — run the same oracles against rio-tiler 9.4.0 … 9.4.3 and flag
  *changes*. Nobody spins this up ad hoc, and it converts geocase from a one-shot audit into
  a regression service. A silent numerical change between patch releases is exactly the
  failure a downstream user most fears and least detects.
- **Cross-GDAL/PROJ** — several negative results in the report are version-dependent (the
  polar `tile_exists` non-finite branch never fires under GDAL 3.10.3). A matrix surfaces
  that as signal rather than a footnote.

## 3. Replace shipped files with parameterized generators

```python
geocase.raster(
    shape=(4096, 4096),
    transform=sheared(angle=30),
    nodata=-9999,
    tiled=True, blocksize=512,
    overviews=[2, 4, 8],
    mask="per_dataset",
)
```

This fixes four problems at once:

- **Size** — 28 of the 30 rasters are 8x8–64x64, too small to reach tiling, windowing,
  overview-selection, or block-boundary bugs. Generators make a 4096² case free to distribute.
- **Tiled vs striped** — 28 of 30 are striped, so `async_geotiff` rejects them outright and
  rio-tiler's entire async/COG range-request surface (the part most likely to be buggy) is
  reachable by 2 cases. A `tiled=` flag turns this gap into a sweep.
- **False passes** — `hole_center_nodata` claims an interior void it does not have. If the
  hole is *produced by the generator*, the metadata is derived by construction and cannot
  drift from the pixels. Same for the 5 cases that declare a nodata value but contain zero
  nodata pixels.
- **Combinatorics** — dtype x nodata-kind x mask-kind x tiling x CRS is thousands of cases
  you cannot hand-curate but can enumerate.

Keep a small pinned file corpus for byte-level regressions (compression quirks, real-world
malformed headers) where generation is not faithful.

## 4. Case shapes you are missing that actually found bugs

Ranked by demonstrated yield in this exercise:

- **Per-band nodata** (requires a VRT) — defect E, 684% mean error on band 2. You have none.
- **Internal mask band / `.msk`, especially combined with a nodata value** — defect D,
  14.5% mean error. You have none.
- **Multiband with distinct band descriptions** — defect B. Multiband cases exist, but
  nothing asserts per-band metadata *ordering*.
- **More sheared transforms** — multiple angles, with and without nodata, large rasters.
  The single rotated case found the biggest bug; that is the vein to mine, not a one-off.
- **South-up (`e > 0`) and x-flipped (`a < 0`) transforms** — the control-arm agent tested
  these; you have none.
- **Overviews that disagree with full resolution** (deliberately wrong decimation) — catches
  overview selection silently reading the wrong level.
- **Adversarial nodata** — nodata equal to a legitimate data value; nodata outside the dtype
  range; nodata set on some bands only.
- **Alpha band + nodata together** — genuinely ambiguous semantics, worth pinning down what
  correct means.
- **Axis-order traps** — `EPSG:4326` vs `OGC:CRS84`, and `EPSG:4326` given
  authority-compliant lat/lon ordering.
- **Sparse COGs with missing blocks**, BigTIFF, band-interleave vs pixel-interleave.

## 5. Productize the taxonomy — but know what it is worth

The `risk_types` vocabulary is the part that genuinely earned its keep: it is what pointed
the investigation at sheared transforms. But the control arm showed an unaided agent
generates that checklist itself.

So the value is not *having* a taxonomy — it is **recall**: being demonstrably more complete
than what a competent engineer improvises in ten minutes.

That means shipping it as a first-class artifact: a machine-readable risk taxonomy with, per
entry, the property that detects it and the generator that triggers it. That is directly
consumable as an agent prompt pack, and it is measurable — you can score recall against
known CVEs and closed upstream issues in GDAL / rasterio / fiona.

## 6. What to drop or reframe

**The declared-assertion conformance mode.** It has now found zero bugs in two libraries. It
tests that your generator wrote what it said it wrote. Either retire it, or rename it to
what it is — a corpus self-check that runs in *your* CI, not a validation feature your users
run against their code.

## 7. Fix the trust problem first

`hole_center_nodata` false-passing is more damaging than any missing feature. A validation
tool that returns green for a property it cannot test is worse than no tool, because it
terminates the user's search.

Before adding anything: add a corpus self-validation pass that asserts every case's declared
properties against its actual pixels, and run it in CI. That single check would have caught
the hole case and the five phantom-nodata cases before release.

---

## Sequencing

1. **Corpus self-validation in CI**; fix `hole_center_nodata` and the 5 phantom-nodata
   cases. — *credibility*
2. **Ship 6–8 generic property oracles** (purity, permutation equivariance,
   translation/rotation equivariance, round-trip, tile-mosaic consistency). — *the new product*
3. **Add generators**; make size, tiling, and block layout parameters. — *unlocks the
   async/windowing surface*
4. **Cross-version differential runner.** — *the moat*
5. **Machine-readable risk taxonomy** with property + generator links. — *the agent-facing asset*

---

## Strategic framing

A corpus competes with an agent that can write fixtures in seconds and will only get better
at it. An oracle library plus a version matrix competes with nobody: it accumulates value
over time and requires infrastructure the agent does not have.

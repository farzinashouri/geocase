---
description: "Design brief for a developer-facing GeoCase presentation: audience, spine, beat order, and the load-bearing facts."
---

# Design brief — developer-facing GeoCase presentation

> **Status: brief, 2026-08-30.** Written to be handed to a design tool alongside
> [`README.md`](https://github.com/farzinashouri/geocase/blob/validation/README.md).
> Not a published page; it describes a deliverable, not the product.
>
> **Branch note:** written on `validation`, which is ahead of `main` and not yet
> merged. The GitHub links below therefore point at **`validation`**, not `main`,
> so they resolve to the content this brief actually describes. Once `validation`
> merges, repoint them to `main` — branch links break when the branch is deleted.

## The ask

Design a presentation of GeoCase for **working geospatial / Python developers**.
Format is your call — slide deck or a single scrolling page, whichever serves the
spine below. The audience does not know GeoCase. They do know their own test
suite, and they are quietly aware it is thin.

**The one action we want afterwards:** `pip install geocase`, then point one
existing test at one bundled case.

That target sets the bar for every slide: it must move a working developer one
step closer to typing that command. Anything that only makes GeoCase sound
impressive is cut.

## Spine

One argument, in this order. Do not hedge across several framings — the source
docs offer at least three ("curated failure modes", "metadata-driven selection",
"realistic but small") and only the first is the spine.

1. **Your geospatial tests pass because you wrote the fixtures.** The bug and the
   test data came from the same set of assumptions, so they agree.
2. **Here is a bug that survives review** — the NoData beat, below. Concrete,
   with real numbers.
3. **There are four such failure modes worth naming**, and 153 files built around
   them.
4. **Adoption costs one decorator.** Show the marker, show the test, show it fail.
5. **And there is a second mode that needs no oracle at all** — differential
   testing, with the pyogrio evidence. This is the credibility beat.
6. **Install line.**

## Beat 2 in detail — the hook, decomposed

This is the most important sequence in the presentation and the source README
renders it as continuous prose. Break it into staged reveals; the numbers are the
payload, not the code.

- **Reveal A — the function.** Four lines. It looks fine. It passes review.
  ```python
  def mean_elevation(array):
      return float(array.mean())
  ```
- **Reveal B — the test**, pointed at a bundled case (`geotiff_nodata_small`).
  Nothing exotic: a marker and a fixture.
- **Reveal C — the failure**, and this is the frame that should hold longest:

  | | |
  |---|---|
  | reported mean elevation | **−152.9 m** |
  | actual mean elevation | **48.1 m** |
  | cause | 2 of 100 pixels carry a `-9999` NoData sentinel |

- **Reveal D — the line that lands it:** nothing raised, nothing warned. The
  number is simply wrong, and it stays wrong all the way into the report.

Typographic weight goes on `−152.9` and `48.1`. The code is context; the gap
between those two numbers is the argument.

## Facts that are load-bearing

Use these exactly. They are verified against the repo as of 2026-09-05.

- **166** bundled cases, **5.1 MB** total. Vector, raster, and NetCDF.
- **1.0.0 on PyPI** (`pip install geocase`), after the `1.0.0rc1`–`rc3` candidates.
- Compatibility promise covers exactly **two surfaces**: the pytest workflow
  (fixtures `geocase`, `geocase_case`, `geocase_cases`, `geocase_registry`;
  markers `geocase_case`, `geocase_suite`, `geocase_select`) and `import geocase`.
- One runtime dependency: `geofacts`, itself zero-dependency. Everything else is
  an optional extra. **This matters to the audience** — adopting GeoCase does not
  drag GDAL into their environment.
- The four named failure modes, which should appear together as a set:
  **NoData** averaged into a statistic; geometry crossing the **antimeridian** and
  coming back as a ring around the globe; a **CRS mismatch** between two layers
  that overlay perfectly on screen; EPSG **axis order** flipping latitude and
  longitude.

## Beat 5 — the credibility slide

Do not skip this and do not soften it. It is the strongest claim the project can
make and it is currently buried in
[`docs/differential-testing.md`](https://github.com/farzinashouri/geocase/blob/validation/docs/differential-testing.md).

An independent validation run pointed the vector corpus at
[pyogrio](https://pyogrio.readthedocs.io/) and found **two real defects**: a crash
in `read_dataframe(fid_as_index=True, use_arrow=True)`, since patched upstream,
and a GPKG spatial-filter divergence traced into GDAL's `GetArrowStream` and filed
there.

The point that makes it interesting, and which the design must carry: **both came
from comparing pyogrio against itself.** Neither side was the oracle. Read the
same bytes two ways, and the finding is the disagreement — which is how it found
bugs in a mature, widely-used library where assert-against-declared-truth found
none.

Visually this wants a two-column figure: the same case file feeding two read
paths (`use_arrow=False` / `use_arrow=True`), the paths converging on a compare
step, and the output being a divergence rather than a pass/fail.

## Visual system

**Do not adopt an off-the-shelf design system.** Material, shadcn, Radix and
Carbon would all fight the logo. GeoCase already has a coherent visual position;
use it.

The lockup is **near-black ink plus one hot red**, and the red appears exactly
once — filling the NoData cell in a 4×4 raster grid. The mark is the pitch: a
uniform grid, one cell that is not like the others. That is the same argument as
the −152.9 / 48.1 beat. Anything that dilutes it throws away the project's
strongest asset.

### Ground

**Near-black**, not pure `#000` — an ink around `#16181A`–`#1A1A1A`, so the red
does not vibrate against it and code blocks can sit one step lighter without
needing a border. Dark ground throughout; this is a deliberate preference, not a
default.

### Red is a semaphore, never decoration

One rule, and it carries the whole system:

> **Red marks the thing that is wrong.**

The NoData cell. The `−152.9`. The divergence in the differential figure. That
is the complete list of what may be red.

Red is never a heading colour, never a button fill, never an accent bar added
because a slide looked empty. Its scarcity is what makes it read — spend it more
than about once per slide and it stops meaning anything.

**Legibility constraint:** hot red on near-black is the hardest case in this
palette. It holds for filled shapes and large numerals; it fails as small running
text. So red is for **fills and large numerals only**.

### Everything else is greyscale

Ink ground, off-white type, mid-grey for secondary text. If a slide seems to need
a third colour, it needs less content instead.

### Type

One grotesque, two weights. The wordmark is a geometric grotesque — **Inter**
matches it and is free on Google Fonts (Söhne is the paid equivalent if
available). Bold for the numbers, regular for everything else. Monospace only
inside code: **JetBrains Mono** or Berkeley Mono.

### Layout motif

The mark's 4×4 raster grid is a layout system the project already owns. Use it
for section dividers and for the differential figure, with the "wrong" cell in
red. This ties every slide back to the logo without repeating the logo.

### Assets and a caveat

Logo files are in
[`docs/assets/logo/`](https://github.com/farzinashouri/geocase/tree/validation/docs/assets/logo)
— lockup, wordmark, and mark, with `-on-ink`, `-on-accent` and `-transparent`
variants. Use `-on-ink` on the dark ground.

⚠️ **The hex values above were read off the rendered logo by eye, not from
source.** Replace them with the exact values from the logo design before handing
this to a designer, or they will drift.

⚠️ **The docs site does not currently match.** `mkdocs.yml` and
`docs/stylesheets/catalog.css` are teal + amber, which predates the logo and now
contradicts it. The presentation should follow **the logo**, not the site.
Reconciling the site is separate work.

## Handling the objection

The audience's real alternative is not "no tests". It is the `test_data/sample.tif`
someone exported once and the `numpy` arrays each test improvises. Name that
directly — it earns trust, because they know it is what they have.

The counter, in one line: those fixtures pass because they were chosen by the
same person who wrote the code, so they encode the same assumptions. GeoCase cases
were not, and they ship as a versioned dependency instead of a folder nobody
remembers the provenance of.

## Tone

The README's voice is the reference: flat, specific, unhedged. It states what
breaks and shows the number. No exclamation marks, no "revolutionize", no
"powerful". Confidence comes from the failure output being real.

## Out of scope

Leave these out; they serve different audiences and will dilute the adoption ask.

- The LLM benchmark subsystem (`geocase.benchmark`).
- Contributor procedure — how to add a case, the CI gate architecture, the
  generated-artifact rules.
- Roadmap and internal plans.
- The remote / private catalog tiers. Remote transport is deferred to v1.1;
  presenting it invites "so it's not finished".

## Source material

- [`README.md`](https://github.com/farzinashouri/geocase/blob/validation/README.md) —
  source of truth for facts, code samples, and voice. Attach it.
- [`docs/philosophy.md`](https://github.com/farzinashouri/geocase/blob/validation/docs/philosophy.md)
  — the "a case is more than a file" framing, if a supporting beat needs it.
- [`docs/differential-testing.md`](https://github.com/farzinashouri/geocase/blob/validation/docs/differential-testing.md)
  — full detail behind beat 5.

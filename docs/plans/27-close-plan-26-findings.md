---
description: "Close the three findings Plan 26 surfaced: the vocabulary gap behind two headline failure modes, docs defects nothing gates for, and the remaining 114 contributor-voiced case descriptions."
---

# Plan 27 — Close the findings Plan 26 surfaced

> **Proposed 2026-08-23; amended 2026-08-23** with three findings from
> [Plan 25](25-ship-geocase-as-a-package.md) steps 2–4 (see *Added 2026-08-23* below, §2.1a and
> §2.3). Still proposed — nothing here is implemented.
> Scope is this document; sequencing is owned by
> [`development-plan.md`](development-plan.md). Authorises no deployment, no domain, no upload —
> the constraints from [Plan 24](24-catalog-site-on-owned-domain.md) and
> [Plan 25](25-ship-geocase-as-a-package.md) are unchanged and this plan does not touch
> `site_url`, the `Documentation` URL, or the values baked into the 135 committed case pages.

## Context

[Plan 26](26-docs-truth-pass-and-seo-prep.md) executed completely, and three of its steps found
things it had not predicted. Two of those are cheap fixes. The third is not a docs problem at
all — it is a **catalog coverage problem wearing a docs problem's clothes**, and it is the only
item here worth real effort.

The through-line: Plan 26 made the docs tell the truth, but *truth about a gap is still a gap*.
The README now leads with four failure modes because Plan 24 pre-committed to measuring those
four in Search Console. Two of them have no case behind them. Correcting the prose without
closing the vocabulary gap means the site would rank for queries the catalog cannot answer —
which is worse than not ranking, because it spends a first impression on a miss.

### What was measured (2026-08-23, in this working tree)

| Finding | Measurement | Where it came from |
|---|---|---|
| No `axis_order` / `crs_mismatch` case | 111 distinct risk types across 135 cases; **zero** named `axis_order` or `crs_mismatch` | Plan 26 §3.3, while scoping which descriptions to rewrite |
| The vocabulary is fragmented | **75 of 111** risk types apply to exactly one case. `MIN_HUB_CASES = 2` means those 75 get no hub page — 36 hubs exist for 111 risks | This plan, confirming the above is systemic rather than a one-off |
| Stale numbers outside the enumerated set | 4 more `134`s and 3 stale "780 passing tests" (actual: 1701) in `getting-started.md`, `contributing/workflow.md`, `releasing.md` ×2, `structure-and-planning.md` | Plan 26's own verification grep, after Phase 1 was "done" |
| A page rendering as source | `docs/philosophy.md` had an **unclosed code fence**; the entire page rendered as literal markdown. A named landing candidate | Plan 26 §3.4, when adding `description:` front matter |
| Description debt is bounded | **114** cases still carry contributor-voiced descriptions; **30** of those exceed 155 chars and are silently truncated in `<meta name="description">` | This plan, sizing §3 below |

Both stale-number and broken-page findings were **fixed in Plan 26** — they appear here only
because nothing prevents their recurrence, which is the actual deliverable.

### Added 2026-08-23 from Plan 25 steps 2–4

Implementing [Plan 25](25-ship-geocase-as-a-package.md)'s truth-pass steps surfaced three more
instances of the **same two defect classes this plan already owns**, plus one new class. They are
recorded here rather than in Plan 25 because §2 is where the prevention work lives.

| Finding | Measurement | Class |
|---|---|---|
| A stale figure that was "corrected" in the **wrong direction** | Plan 25 asserted the bundled payload is 4.2 MB on the strength of `du -sh src/geocase/data`, and instructed reverting the 2.1 MB figure. `du` reports *apparent* usage: 572 files in 218 directories, each rounding to a 4 KB block ≈ **1.8 MB of padding that reaches no artifact**. Real payload byte sum **2.1 MB**; whole tree 2.4 MB; `geocase/data/**` in the built wheel **2.3 MB** uncompressed | §2.1 (extends it — see 2.1a) |
| Phantom infrastructure in `contributing/workflow.md` | Described CI as GitLab pipeline jobs defined in `ci/catalog-validation.yml`, `ci/core-tests.yml`, `ci/extended-tests.yml`. **No `ci/` directory exists or ever did**; CI is GitHub Actions with five jobs in `.github/workflows/ci.yml` | New class — see 2.3 |
| Release status read as shipped | `CHANGELOG.md`'s `## [1.0.0] — 2026-08-02` and the `Status: **1.0**` blocks in `README.md:5` / `docs/index.md:9` all presented a never-uploaded version as released; the correction existed only in a blockquote *below* the summary line | §2.1 (a claim, not a number) |

All three were fixed in the Plan 25 pass. As with the findings above, the deliverable here is
that **nothing prevents their recurrence**.

Two of them sharpen this plan's §2 rather than adding to it:

- The MB figure is **derivable and stable** — precisely the profile §2.1 says to *gate*, not
  delete, and it is currently ungated in three files.
- The `ci/*.yml` claim is neither a number nor broken markdown, so §2.1 and §2.2 both miss it.
  It is a **reference to a path that does not exist**, which is mechanically checkable in the
  same lint §2.2 already proposes.

---

## Phase 1 — The vocabulary gap (the only item with real leverage)

### 1.1 Add the two missing cases

`axis_order` and `crs_mismatch` are in Plan 24's pre-committed Search Console vocabulary and in
the README's opening prose. The catalog has neither.

The nearest existing cases exercise the *symptom* without naming the risk, and that distinction
matters because selectors, hub pages, and the risk facet all key on `risk_types`:

| Query the README invites | Nearest case today | Why it does not close the gap |
|---|---|---|
| axis order / lat-lon swap | `out_of_bounds_coordinates` (`lat_lon_swap`) | Latitude 100° is an *out-of-range* case. It catches the swap only when the swap produces an impossible value — which is the easy half. A swap of `(45, 10)` → `(10, 45)` is silently valid and is what actually ships to production. |
| CRS mismatch | `rasterize_match_wgs84_polygon`, `web_mercator_baseline` | Both are single-layer. A mismatch is a *relationship between two inputs*; neither case can express it, because no bundled case pairs two layers in disagreeing CRSs. |

**Two new cases, metadata-first per [`docs/adding-a-case.md`](../adding-a-case.md):**

> **Superseded for `axis_order_swapped_pair` by [Plan 34](34-close-reviewed-catalog-gaps.md) Phase 4.2 (2026-08-29).** The six `*_gml_baseline` cases already *contain* authority-order coordinates on disk — `urn:ogc:def:crs:EPSG::4326` forces `(lat, lon)` in `gml:pos` regardless of GDAL's traditional-order setting — and no `case.yaml` said so. Declaring the property on real bytes, plus a check that verifies it against those bytes, delivers this item's intent more directly than a synthetic pair would: the swap is silent for exactly the reason described below, and the fixtures needed no new payload. `crs_mismatch_overlay_pair` is **not** affected and remains owed.

1. **`axis_order_swapped_pair`** — a vector case holding the same feature twice: once in the
   authority's declared axis order (EPSG:4326 = lat, lon) and once in the GeoJSON/OGC:CRS84
   order (lon, lat), with coordinates chosen so **both are geographically plausible** (a
   mid-latitude, mid-longitude point where swapping lands you somewhere real rather than in the
   ocean off Antarctica). That is the whole point: the failure is silent. Declares
   `risk_types: [axis_order, lat_lon_swap, silent_invalid_geometry]`.
2. **`crs_mismatch_overlay_pair`** — two layers that overlay perfectly on screen and are
   metres apart in reality: the same footprint in EPSG:4326 and EPSG:32633, with the
   declared-but-wrong CRS on one. Declares `risk_types: [crs_mismatch, reprojection_error]`.

⚠️ Both are **new payloads**, so this triggers the full gated-artifact chain in `CLAUDE.md`:
`build_case_index.py`, `validate_catalog.py`, `generate_vector_fixtures.py`,
`generate_checksums.py`, `generate_catalog_pages.py`, and both coverage matrices. Budget for
that, and note that adding cases moves the count off 135 — which is now gated in **seven**
places by `_COUNT_CLAIMS` in `scripts/validate_catalog.py`. That gate will fail loudly and
correctly; update all seven.

**A question worth settling before building:** should the pair be one case with two files, or
two cases that reference each other? The catalog has no existing multi-layer case, so there is
no precedent to follow. Recommend **one case with a sidecar**, because a mismatch that is split
across two independently-selectable cases can be selected apart, and a selector that returns
half of a relationship is a footgun. Confirm against `CaseMetadata`'s `files.sidecars` before
committing to it.

### 1.2 Decide whether the fragmented vocabulary is a defect or a design

75 of 111 risk types apply to exactly one case. That is not obviously wrong — a catalog of edge
cases will have long-tail risks — but it has two measurable consequences:

- **Discovery.** `MIN_HUB_CASES = 2` gives 36 hub pages for 111 risks. A searcher looking for a
  singleton risk has no landing page; the term appears only inside one case page.
- **Selection.** `@pytest.mark.geocase_select(risk_types_any=[...])` is only as good as the
  vocabulary's consistency. `coordinate_order` (1 case) and `lat_lon_swap` (1 case) plausibly
  describe the same failure under two names, and a user who picks one silently misses the other.

**Do not mass-rename.** Risk types are user-facing selector input, and renaming them is a
breaking change to the pytest workflow — one of the two surfaces under the v1.0 compatibility
promise. Instead, **measure first**: produce a one-off report grouping the 75 singletons by
apparent synonymy, and decide per-cluster whether to (a) leave it, (b) add an alias, or (c)
consolidate in a v1.1 with a deprecation shim. Scope this phase to the *report*, not the
change.

### 1.3 Vocabulary entries arriving from other plans (added 2026-08-28)

This phase owns the `risk_types` vocabulary, so terms introduced elsewhere register here
rather than floating free. Each row must name the check that enforces it, per §1.2's rule that
a vocabulary entry nothing gates is indistinguishable from a typo.

| Term | Introduced by | Cases | Enforcing check |
|---|---|---|---|
| `ambiguous_zero` | [Plan 32](32-footprint-truth-and-ambiguous-zero.md) Phase 2 | `landcover_ambiguous_zero_small` | **Owed.** Today the term is carried by `nodata_ignored` on the same case, which `_check_footprint`'s sibling in `catalog/content.py` does gate (the raster must declare a nodata value and contain pixels at it). A check specific to `ambiguous_zero` — the declared sentinel must also be a *meaningful value elsewhere in the scene*, not merely present — belongs in this phase. |
| `axis_order` | [Plan 34](34-close-reviewed-catalog-gaps.md) Phase 4.2 | the six `*_gml_baseline` cases | `_check_authority_axis_order` in `catalog/content.py`, called from `check_vector_content` whenever the term is present. The file must use the `urn:ogc:def:crs` form, and the first `gml:pos` ordinate must fall inside the case's declared latitude band. |
| `integer_precision` | [Plan 34](34-close-reviewed-catalog-gaps.md) Phase 4.3 | `polygon_z_gpkg` | `_assert_id_value`, via `params.expected_id_value`. Exact equality, not approximate — the value is 2^53 + 1, so an approximate comparison would pass the bug the term names. |

`ambiguous_zero` is a singleton term, which §1.2 otherwise warns against adding. It is justified
because the term was **already referenced** in `landcover_small`'s `behavioral_goal` before any
case carried it, and because zero-as-sentinel is a common real failure mode rather than a
long-tail curiosity. Note it also names an existing generator axis,
`geocase.raster.axes.ambiguous_zero`, which frames the same collision for multiband reflectance
— worth deciding in §1.2 whether one term should cover both framings.

---

## Phase 2 — Gate the two defect classes that recurred

Both were fixed in Plan 26. Neither is prevented from happening again.

### 2.1 Stale hand-written numbers

`_COUNT_CLAIMS` now gates 7 case-count claims and is verified to fail on a regression. But the
same commit found **three stale "780 passing tests"** figures against an actual 1701, and
nothing gates those.

Test counts are a worse candidate for gating than case counts: the number changes on every test
added, so a hard gate would fail constantly and get disabled — the classic over-gating failure.
**Recommend removing the numbers instead of gating them.** "780 passing tests" in a contributing
doc carries no information a reader can act on; "the suite is green in CI" does. Sweep the
hand-written docs for hardcoded test counts, coverage percentages and wheel sizes, and either
delete them or point at the source of truth.

Keep the gate for genuinely stable, meaning-bearing numbers (case count, public-API surface
size), and prefer deletion for volatile ones.

### 2.1a Gate the bundled-payload size (added 2026-08-23)

The MB figure is the *stable, meaning-bearing* half of 2.1's rule, and it is ungated in three
files: `README.md:5`, `docs/index.md:9`, `docs/dataset-catalog.md:35`. It is also the figure
that already drifted **twice, in opposite directions** — which is the argument for gating rather
than trusting a fourth reader with a shell.

Add a `_SIZE_CLAIMS` check to `scripts/validate_catalog.py` alongside `_COUNT_CLAIMS`, computing
the payload from the same source the registry uses and comparing to one decimal place.

**The load-bearing detail — do not measure with `du`.** Sum `Path.stat().st_size` over the
payload files. `du` reports 4 KB-block apparent usage and over-reports this tree by ~2x; that is
exactly how the wrong figure got published. Which files count also needs settling, since three
defensible answers exist:

| Basis | Value | Verdict |
|---|---|---|
| Payload files only (excl. `case.yaml`, `notes.md`, `checksums.sha256`) | 2.1 MB | **Use this** — it is what the docs mean by "bundled payload" and what the current text says |
| Whole `data/` tree | 2.4 MB | Reasonable, but changes the published number for no reader benefit |
| `du -sh` | 4.2 MB | Wrong. Not bytes that ship |

Record the chosen basis in the checker's docstring. A future reader running `du` and finding
disagreement must be able to see, in the code, why the smaller number is the honest one — the
comment in `scripts/verify_dist.py:42-49` now carries the same explanation and should stay
consistent with it.

Note this bounds §2.1's "delete volatile numbers" sweep: wheel/sdist sizes stay in
`verify_dist.py` (where they are a gate's justification, next to the ceiling they explain), and
the 2 MB artifact ceiling itself is unaffected — it still has ~4x headroom at wheel 456 KB /
sdist 272 KB.

### 2.2 Structurally broken markdown

`mkdocs build --strict` did **not** catch `philosophy.md` — an unclosed fence produces valid
output, just wrong output, and strict mode only fails on broken links. A scan across all
non-generated docs found `philosophy.md` was the only offender, so the remediation is cheap and
the check is cheap:

- Add a lightweight docs lint to the `docs` CI job asserting, per non-generated page: balanced
  code fences, exactly one H1, and non-empty front matter `description:` on the pages that
  declare it. A ~40-line script, or an existing markdown linter pinned like `ruff` is.
- One judgement call: **do not** require an H1 on every page or a description on every page.
  Generated pages already have both, and mandating it on every contributing doc is churn with
  no reader benefit.

### 2.3 Repo paths named in prose that do not exist (added 2026-08-23)

`workflow.md` documented three `ci/*.yml` files, a GitLab pipeline, and a job split that never
existed in this repo. Nothing caught it: it is not a number (§2.1), the markdown is well-formed
(§2.2), and `mkdocs build --strict` only resolves *documentation* links — a backticked
`ci/core-tests.yml` is prose to it. So a contributor could follow that section, look for the
files, and find nothing.

Extend the §2.2 lint with a fourth assertion: **backticked tokens that look like repo paths
resolve.** Match inline-code spans against a path-shaped pattern (contains `/`, ends in a known
extension: `.py`, `.yml`, `.yaml`, `.toml`, `.md`, `.json`, or ends in `/`), and fail when the
path does not exist relative to the repo root.

This needs an allowlist, and getting it right is most of the work — false positives are what
kill a lint like this. Known categories to exempt:

- Paths inside fenced code blocks (shell examples legitimately name output paths, scratch dirs
  like `/tmp/gc/bin/activate`, and files created by the command being shown).
- Illustrative user-side paths — `tests/test_my_thing.py`, `test_data/sample.tif` — which
  describe the *reader's* repo, not this one.
- `docs/plans/**` and `docs/evidence/**`, which are historical records: a plan describing a file
  it proposed and never built is correct as a record. This is the same carve-out
  [Plan 25 §1](25-ship-geocase-as-a-package.md) already made for stale `geofacts` references.

If the allowlist grows past roughly a dozen entries, **drop the check** rather than maintaining
it — the defect it catches is real but rare (one instance in the repo's history), and a lint that
cries wolf gets disabled, which costs more than the bug. Prefer the narrow version: enforce only
outside fenced blocks, only under `docs/contributing/`, where "this is how the repo works"
claims actually live.

---

## Phase 3 — The remaining description debt

Plan 26 rewrote 21 of 135 descriptions, scoped to Plan 24's measured vocabulary. **114 remain**,
of which **30 exceed the 155-char cap** and are silently truncated with an ellipsis in their
`<meta name="description">` — those 30 are strictly worse than short ones, because the sentence
is cut mid-thought in the search result.

**Sequence by cost, not by count:**

1. **The 30 truncated ones first.** These are a defect, not a preference: the rendered meta
   description ends in `…` partway through a clause. Fixing them is bounded and mechanical.
2. **The rest opportunistically.** Not a batch task. Rewrite a case's description when touching
   that case for another reason. A 114-case sitting sprint produces uniform, low-energy prose —
   which is what the current descriptions already are.

**Do not** raise `MAX_META_DESCRIPTION`. 155 is the practical display limit, and truncation in
the tag is preferable to truncation by the search engine.

One generator note: `DESCRIPTION_FIELDS`' fallback chain (`description` → `behavioral_goal` →
`title`) is sound and should stay. The problem was never the chain.

---

## Out of scope

- Anything Plan 24 or 25 owns: the domain, the Astro target, the PyPI upload, the README rewrite.
  The Plan 25 findings folded in above are the *prevention* work only — Plan 25 already made
  those docs true; this plan keeps them from going stale again. The upload itself stays there.
- The `social` plugin. It is deferred in the roadmap with its own conditions (libcairo on the
  runner) and is not blocked on anything here.
- Renaming existing risk types. Phase 1.2 produces a report; any rename is a v1.1 decision with
  a deprecation path, because `risk_types` is selector input under the compatibility promise.

## Verification

```bash
conda activate geocase

# Phase 1 — the new cases exist, are selectable, and the gates agree
python -c "import geocase; print(len(geocase.list_cases()))"     # 137, and all 7 claims updated
python -c "import geocase; print([c.id for c in geocase.list_cases() if 'axis_order' in c.risk_types])"
python -c "import geocase; print([c.id for c in geocase.list_cases() if 'crs_mismatch' in c.risk_types])"
python scripts/build_case_index.py --check
python scripts/validate_catalog.py
python scripts/generate_vector_fixtures.py --check
python scripts/generate_checksums.py --check
python scripts/generate_catalog_pages.py --check
python scripts/generate_vector_coverage_matrix.py --output docs/_generated/vector-coverage-matrix.md
python scripts/generate_raster_coverage_matrix.py --output docs/_generated/raster-coverage-matrix.md

# Phase 2 — the new docs lint catches what strict mode does not
#   inject an unclosed fence into a scratch page; the lint must fail
grep -rn '780 passing tests' docs/ README.md        # must return nothing

# Phase 2.1a — the payload size is gated, and measured by bytes not blocks
python scripts/validate_catalog.py                  # must fail if a doc's MB figure drifts
python - <<'PY'                                     # the basis, spelled out: expect 2.1 MB
from pathlib import Path
root = Path("src/geocase/data")
skip = {"case.yaml", "notes.md", "checksums.sha256"}
total = sum(p.stat().st_size for p in root.rglob("*") if p.is_file() and p.name not in skip)
print(f"{total} bytes = {total / 1048576:.1f} MB")
PY
grep -rn -- '4\.2 MB' README.md docs/ src/ scripts/ | grep -v docs/plans/   # only the
                                                    # verify_dist.py comment explaining why

# Phase 2.3 — no prose names a repo path that does not exist
ls ci/ 2>&1 | head -1                               # must be "No such file or directory"
grep -rn 'ci/core-tests\|ci/catalog-validation\|ci/extended-tests' docs/ | grep -v docs/plans/
                                                    # must return nothing

# Phase 3 — no rendered meta description is truncated
grep -c '…"' docs/_generated/catalog/cases/*.md | grep -v ':0' | wc -l   # target: 0

# Unchanged constraints from Plan 24
grep -rn 'github.io' mkdocs.yml pyproject.toml | wc -l    # must be 2
git ls-remote --heads origin | grep gh-pages              # must return nothing
```

Plus the standing gates: `mkdocs build --strict`, `ruff format --check src tests && ruff check
src tests`, `mypy src`, `pytest tests -q`.

## Suggested commit split

1. The two new cases + full artifact regeneration + the seven count claims updated (Phase 1.1).
   Large, mechanical, isolated.
2. The risk-vocabulary report (Phase 1.2). Analysis only; changes no user-facing behaviour.
3. Docs lint + hardcoded-number sweep (Phase 2, incl. 2.3's path check). Small.
4. `_SIZE_CLAIMS` payload-size gate (Phase 2.1a). Small and independent of 3 — it touches
   `validate_catalog.py` only, where `_COUNT_CLAIMS` already establishes the pattern.
5. The 30 truncated descriptions + regeneration (Phase 3.1).

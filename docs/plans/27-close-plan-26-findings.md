---
description: "Close the three findings Plan 26 surfaced: the vocabulary gap behind two headline failure modes, docs defects nothing gates for, and the remaining 114 contributor-voiced case descriptions."
---

# Plan 27 — Close the findings Plan 26 surfaced

> **Proposed 2026-08-23.** Scope is this document; sequencing is owned by
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
3. Docs lint + hardcoded-number sweep (Phase 2). Small.
4. The 30 truncated descriptions + regeneration (Phase 3.1).

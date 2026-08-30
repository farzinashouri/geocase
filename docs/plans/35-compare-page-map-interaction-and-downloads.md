# Plan 35 — Compare Page: Map Interaction, Per-File Downloads, and the Browse Link

> **Status: proposed 2026-08-30.** Four scoped fixes to the published compare
> page and its two coverage maps, all arising from reading the shipped page
> rather than from a review. Three are defects; the fourth is a link.

## Context

[Plan 31](31-case-geography-and-world-maps.md) shipped the two equirectangular
coverage maps on `docs/_generated/catalog/compare.md`, and
[Plan 33](33-map-identity-geography-and-geometry.md) gave the footprints an
identity and wired hover and click into the compare table through the
dependency-free `docs/javascripts/catalog-compare.js`. Using the result surfaces
three defects and one gap.

**1. Every hover fires two tooltips.** `world_map()` emits an SVG `<title>` child
on each hoverable `<g>` — both the `gc-map-extent-group` footprints
(`scripts/catalog_svg.py:701-707`) and the `gc-map-marker` clusters
(`scripts/catalog_svg.py:717-723`) — as the no-JS fallback and the accessible
name. Plan 33 then added a styled `div.gc-map-tooltip` built in JS
(`catalog-compare.js:117-197`), whose whole justification is that the native
tooltip "waits about a second, cannot wrap, and truncates exactly the long
cluster lists that most need reading". Both are live: the browser still renders
the `<title>` after its delay, on top of the HTML tooltip that has been visible
since the pointer arrived. The white-background HTML one is the one to keep.

**2. A single-case marker does not filter.** `catalog-compare.js:238-262`
branches on `ids.length > 1` and early-returns for a one-case marker, on the
stated reasoning that it "has nothing to filter down to". In use this reads as a
broken marker rather than a considered omission: a reader who has just clicked a
cluster and filtered the table clicks its neighbour and nothing happens.
Filtering to one row is a real action — it is how you get from a dot on the map
to that case's row and link — and `apply()` is already an id-set filter that
handles a one-element set without change.

**3. Case pages name their data files but do not link them.** The Files section
(`scripts/generate_catalog_pages.py:632-640`) renders `case.files.primary` and
its sidecars as inline code. The only URL on the page is `source.url`, which
points at the *upstream* dataset, not at GeoCase's bytes. A reader who wants the
file has to guess a repo path — and the vector tree is nested by geometry type
(`data/core/vector/polygon/<id>/`), so guessing fails.

**4. The home page points at the weaker hub.** `docs/index.md:29` sends
"Browse all 153 cases" to `_generated/catalog/index.md`. The compare page is the
better landing point: the full corpus in one filterable, sortable table with the
coverage maps above it.

Outcome: one tooltip per hover, every marker filters, each case page links to
its actual bytes, and the home page's primary catalog link lands on the compare
page.

## Non-goals

**Bundled downloads (a zip per case, per category, or of the whole catalog) are
deliberately out of scope.** They would add ~7.4 MB of generated binaries that
`--check` must keep byte-identical, plus a new CI gate, to solve a problem
`git clone` already solves. Direct links to GitHub cost nothing to host, never
go stale, and need no artifact. Bundled transport is the same problem as the
remote dataset transport already deferred to v1.1 (`docs/index.md:9`), and
belongs with it.

## Phase 1 — One tooltip, not two

### 1.1 Failing test

`tests/unit/test_catalog_compare_js.py` is a source-text gate — see its module
docstring: the behaviour needs a browser, so what is gated is the contract.
Add `test_compare_js_suppresses_the_native_title()`, asserting the script both
removes the `<title>` element and transfers its text to `aria-label`. Watch it
fail against the current script.

### 1.2 Implementation

In `catalog-compare.js`, before the footprint and cluster loops, walk
`.gc-worldmap [data-case-id], .gc-worldmap [data-case-ids]`; for each node, take
its direct `<title>` child, copy the text to `node.setAttribute("aria-label", …)`,
and remove the `<title>`.

Doing it in JS rather than dropping `<title>` from the generator is the point:

- With JS off, the generator's `<title>` is the *only* tooltip. Removing it at
  the source would break the progressive-enhancement contract the script's own
  header comment states, to fix a problem that only exists when the script runs.
- `aria-label` preserves what a screen reader announces, so the tooltip div's
  existing `aria-hidden="true"` stays correct: the text is still exposed exactly
  once, from the `<g>` instead of from the `<title>`.
- No generator change means `compare.md` does not regenerate for this phase.

The root `<svg><title>` (`catalog_svg.py:681`) is left alone: it is the
accessible name for `role="img"`, is not a hover target, and does not double up.

`_MAX_LABELLED_IDS` in `catalog_svg.py:638` and `MAX_LISTED_IDS` in the script
must stay equal — the comments on both say so, and the `<title>` remains the
no-JS fallback even though it is removed at runtime.

## Phase 2 — Every marker filters

### 2.1 Failing tests

`test_only_clusters_are_clickable` encodes the policy being reversed, in its
name and its docstring. Split it:

- `test_footprints_are_not_clickable()` — keeps the still-correct half, that
  `gc-map-extent-group` stays outside the `CLICKABLE-START`/`CLICKABLE-END`
  region. Plan 33's finding stands: a `help` cursor plus `role="button"` on one
  element is what made footprints feel like a misfire.
- `test_every_marker_is_clickable()` — new, asserting the clickable region
  carries no `isCluster` early-return guard.

### 2.2 Implementation

In the `[data-case-ids]` loop:

- Set `tabIndex = 0` and `role="button"` on every marker; delete the
  `node.style.cursor = "default"` branch. `.gc-map-marker { cursor: pointer }`
  already covers all markers (`docs/stylesheets/catalog.css:269`), so removing
  the inline override is the whole visual fix.
- Set `hint` unconditionally, singular or plural: `"Click to filter the table to
  this case"` / `"… to these cases"`.
- Delete `if (!isCluster) { return; }` so focus, blur, click and keydown bind for
  every marker.
- Keep `isCluster` only where it still carries meaning: `tooltipText()` uses it
  to choose between the "N cases here" head and the bare id.

`renderChip()` already renders the singular ("Showing 1 case from the map") and
`apply()` is set-based, so nothing else changes.

### 2.3 Focus visibility

Single-case markers become focusable for the first time. Check
`docs/stylesheets/catalog.css:269-286` for an inherited `:focus-visible`
outline; add one scoped to `.gc-map-marker` if none applies. Keyboard reach to a
control with no visible focus ring is a defect, not a detail.

## Phase 3 — Per-file download links on case pages

### 3.1 Failing test

Add a test that renders one case page through the generator and asserts the
Files section contains a
`https://github.com/farzinashouri/geocase/raw/main/src/geocase/data/core/…` URL
for `case.files.primary`, rather than a bare code span.
`tests/unit/test_catalog_diagrams.py` is the nearest existing home; a sibling
module for the page generator is equally acceptable.

### 3.2 Implementation

In `scripts/generate_catalog_pages.py`:

- Add `DEFAULT_REPO_URL` mirroring the `DEFAULT_SITE_URL` pattern at lines
  34-38 — `GEOCASE_REPO_URL` env override, defaulting to
  `https://github.com/farzinashouri/geocase` — and a `--repo-url` argument
  beside `--site-url` (line ~1118).
- Add `_repo_relative(case_dir: Path) -> str`, built on
  `geocase.catalog.roots.package_root()` (already imported at line 44):
  `"src/geocase/" + case_dir.relative_to(package_root()).as_posix()`. Reusing
  the existing root resolution is what makes the nested vector layout work
  without a second lookup table.
- Rewrite lines 632-640 so each entry links the filename to
  `{repo}/raw/main/{relpath}/{name}`, likewise for sidecars and notes, followed
  by a `[Browse this case on GitHub]({repo}/tree/main/{relpath})` line.
- Guard on `case_dir is not None` — it is `Optional` in the signature at line
  555, and a manifest-backed case has no directory — falling back to today's
  plain-code rendering when it is `None`.
- Thread `repo_url` from `build_pages()` (line 1009) into `_render_case_page()`
  exactly as `site_url` is threaded today.

Link to `main`, not a pinned commit: the docs site tracks the released branch,
and a sha would rot on every data change.

### 3.3 Regeneration

Generated artifacts are gated, so all 187 case pages regenerate and are
committed. Under the conda `geocase` env:

```bash
python scripts/generate_catalog_pages.py
python scripts/generate_catalog_pages.py --check
```

## Phase 4 — The home-page Browse link

`docs/index.md:29` retargets to the compare page:

```markdown
- **[Browse all 153 cases](_generated/catalog/compare.md)** — the case catalog, filterable and sortable, with coverage maps
```

The catalog hub stays reachable from the `mkdocs.yml` nav ("Browse Cases") and
from the compare page itself, so nothing is orphaned.

## Verification

```bash
pytest tests/unit/test_catalog_compare_js.py tests/unit/test_catalog_diagrams.py -q
pytest tests -q
ruff format --check src tests scripts && ruff check src tests scripts
mypy src
python scripts/generate_catalog_pages.py --check   # conda env
mkdocs build --strict
```

Then in a browser (`mkdocs serve`, open `/_generated/catalog/compare/`):

1. Hover a cluster — exactly one tooltip, the white-background one. Hold for two
   seconds and confirm no native tooltip follows it.
2. Hover a footprint — one tooltip, its row highlights, the cursor stays
   default, and clicking does nothing.
3. Click a single-case marker (`antimeridian_crossing_line` sits alone at the
   right edge) — the table filters to one row, the chip reads "Showing 1 case
   from the map", and "clear" restores the full table.
4. Tab to that same marker and press Enter — same result, with a visible focus
   ring before the press.
5. Open any case page — the Files entries are links; follow one and confirm
   GitHub serves the file.
6. From the home page, "Browse all 153 cases" lands on the compare page.

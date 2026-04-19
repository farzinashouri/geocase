# Documentation Consolidation Plan

> Created: April 2026
> Status: ✅ COMPLETED

This document outlines the plan for restructuring and consolidating GeoCase documentation.

---

## Problem Statement

The `docs/` folder contains 19 markdown files mixing:
- **User guides** (how to use GeoCase)
- **Internal planning artifacts** (development workflow, feature plans)
- **Feature design specs** (future/optional features)

This creates confusion for both users and contributors.

---

## Proposed Structure

```
docs/
├── index.md                              # Landing page (keep)
├── philosophy.md                         # Design principles (keep)
├── getting-started.md                    # User guide (keep, complete)
├── adding-a-case.md                      # User guide (keep, update)
├── testing-your-function-with-geocase.md # User guide (keep)
├── using-parameterized-tests.md          # User guide (keep)
├── remote-datasets.md                    # User guide (keep)
│
├── contributing/                         # NEW: Maintainer docs
│   ├── workflow.md                       # Moved from docs/
│   ├── development-plan.md               # Moved from docs/
│   ├── structure-and-planning.md         # Moved from docs/
│   ├── testing-edge-cases.md             # NEW: Merged from 3 files
│   └── vector-dataset-generation.md      # Merged from 2 files
│
├── design/                               # NEW: Feature specs (future)
│   ├── case-recommendation-service.md    # Moved from docs/
│   ├── case-recommendation-api-spec.md   # Moved from docs/
│   ├── case-recommendation-user-flow.md  # Moved from docs/
│   └── database-design.md                # Moved from docs/
│
├── plans/                                # NEW: Planning artifacts
│   ├── 01-actionable-next-steps.md       # This series
│   ├── 02-documentation-consolidation.md
│   └── 03-consolidation-roadmap.md
│
└── _generated/                           # Keep as-is
    └── vector-coverage-matrix.md
```

---

## Actions

### Step 1: Create subfolders

```bash
mkdir -p docs/contributing docs/design docs/plans
```

### Step 2: Move planning docs to `contributing/`

| Current location | New location |
|---|---|
| `docs/workflow.md` | `docs/contributing/workflow.md` |
| `docs/development-plan.md` | `docs/contributing/development-plan.md` |
| `docs/structure-and-planning.md` | `docs/contributing/structure-and-planning.md` |

### Step 3: Move design specs to `design/`

| Current location | New location |
|---|---|
| `docs/case-recommendation-service.md` | `docs/design/case-recommendation-service.md` |
| `docs/case-recommendation-api-spec.md` | `docs/design/case-recommendation-api-spec.md` |
| `docs/case-recommendation-user-flow.md` | `docs/design/case-recommendation-user-flow.md` |
| `docs/database-design.md` | `docs/design/database-design.md` |

### Step 4: Merge related docs

**Merge into `docs/contributing/testing-edge-cases.md`:**
- `docs/invalid-geometry-testing-strategy.md`
- `docs/adding-invalid-geometry-edge-cases.md`
- `docs/test-parametrization-filtering.md`

**Merge into `docs/contributing/vector-dataset-generation.md`:**
- `docs/vector-dataset-generation-plan.md`
- `docs/building-comprehensive-vector-dataset.md`

### Step 5: Update outdated docs

| Document | Issue | Action |
|---|---|---|
| `structure-and-planning.md` | Says "next job is Wave 2/3" but those are done | Update status section |
| `getting-started.md` | Stub/incomplete | Complete with install + usage |
| `adding-a-case.md` | References stub modules | Update to reflect current state |

### Step 6: Handle miscellaneous files

| File | Action |
|---|---|
| `auto-approve-commands.md` | Delete or move to `.github/` |

### Step 7: Update `mkdocs.yml` nav

After restructuring, update navigation to reflect new structure with sections:
- **Getting Started** (user guides)
- **Contributing** (maintainer docs)
- **Design** (feature specs)

---

## Follow-Up Improvements

These items are not part of the folder reorganization itself, but they are the highest-value documentation improvements to make next.

### 1. Fix stale internal links

Several files may still reference the pre-consolidation paths. Prioritize:

- `README.md`
- `docs/getting-started.md`
- `docs/contributing/workflow.md`
- `docs/contributing/development-plan.md`
- any remaining references to old root-level `docs/*.md` files that were moved to `docs/contributing/` or `docs/design/`

Goal: eliminate broken or outdated cross-links after the docs move.

### 2. Strengthen `docs/index.md`

Expand the docs landing page so it acts as a real entry point rather than a short description.

Add:

- a short “Start here” section,
- links to `getting-started.md`, `testing-your-function-with-geocase.md`, and `adding-a-case.md`,
- a contributor section linking to `docs/contributing/`,
- a brief explanation of the difference between user guides, contributor docs, and design docs.

### 3. Align `README.md` with the new docs structure

Update the README “Learn More” or equivalent sections so they point to:

- `docs/contributing/development-plan.md`
- `docs/contributing/workflow.md`
- `docs/design/case-recommendation-service.md`

Goal: keep the repository landing page consistent with the consolidated docs layout.

### 4. Add a case discovery guide

Create or expand a doc section explaining how to discover and select cases by:

- `tags`,
- `risk_types`,
- `geometry_type`,
- `format`,
- suites.

This can live as a new guide or as an extension of `docs/using-parameterized-tests.md`.

### 5. Add an assertions reference

Create a compact reference page for the public helpers in `src/geocase/assertions/`.

Suggested structure:

- geometry assertions,
- CRS assertions,
- raster assertions,
- topology assertions,
- metadata assertions.

This would make GeoCase easier to adopt beyond basic case loading.

### 6. Add an examples index

Create a short documentation page that points users to the most useful files under `examples/`, grouped by workflow such as:

- plugin usage,
- vector tests,
- raster tests,
- CRS and dateline cases,
- realistic geospatial function tests.

### 7. Standardize terminology

Audit `README.md`, `docs/index.md`, and `docs/philosophy.md` for inconsistent wording such as:

- “case catalog”
- “dataset catalog”
- “testing toolkit”

Pick a primary phrasing and use it consistently across entry-point docs.

### 8. Add a visible alpha-status note

Use a small status note in `README.md` and `docs/index.md` to clarify:

- the project is alpha,
- the core workflow is usable,
- current work is focused on coverage, docs, and release polish.

---

## Open Questions

1. **Archive vs subfolder?** Keep planning docs in `docs/contributing/` (accessible) or `docs/_archive/` (hidden)?
   - **Recommendation:** Use `contributing/` for active maintainer reference

2. **Delete merged files?** After merging, delete originals or keep as redirects?
   - **Recommendation:** Delete after confirming merged content is complete

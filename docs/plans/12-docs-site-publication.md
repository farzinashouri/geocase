# Plan 12 — Publish the docs site to GitHub Pages

> **Status: proposed.** Scope is this document; order is owned by
> [`execution-order.md`](execution-order.md) and scope disputes by
> [`development-plan.md`](development-plan.md).

## Context

The catalog schematics render correctly through mkdocs, but they are not visible on
GitLab. The cause is not the diagrams: **the docs site is never published anywhere.**
`ci/docs.yml` runs `mkdocs build --strict` purely as a validation
check and discards the output, so the only viewable artifact is the raw `.md` file in
GitLab's repository browser — and GitLab's Markdown renderer strips `<svg>` for security
while keeping the text inside `<title>` and `<figcaption>`. That produces the reported
symptom exactly: two lines of caption text, no shape.

Two further facts make this more than a CI addition:

- `site_url` in `mkdocs.yml` and `Documentation` in `pyproject.toml` both point at
  `farzinashouri.github.io/geocase` — a host nothing deploys to. Batch 5 corrected
  `repo_url` to GitLab but missed these two.
- That wrong URL is **baked into all 134 generated case pages** as the JSON-LD `url` and
  `isPartOf.url`, which is the Google Dataset Search surface the generator exists to feed.

Target: `https://fashouri1.github.io/geocase`, deployed by GitHub Actions from a mirror of
the GitLab repo. GitLab CI keeps its `--strict` check; GitHub does the publishing.

## Prerequisites (manual, outside this repo)

The CI work is inert until these are done, and they are deliberately left to a human:

1. Create `github.com/fashouri1/geocase`.
2. In GitLab: **Settings → Repository → Mirroring repositories**, add a push mirror to the
   GitHub repo (needs a GitHub PAT with `repo` scope).
3. In GitHub: **Settings → Pages → Source: GitHub Actions**.

## Steps

### 12.1 Point the canonical URL at the real host

Three places, all currently `farzinashouri.github.io` → `fashouri1.github.io`:

- `mkdocs.yml` — `site_url`
- `pyproject.toml` — `Documentation`
- `scripts/generate_catalog_pages.py` — `DEFAULT_SITE_URL`

Then regenerate so the JSON-LD matches:

```
python scripts/generate_catalog_pages.py
```

This rewrites `url` / `isPartOf.url` in 134 case pages. Because `--check` reads the same
`DEFAULT_SITE_URL`, the existing gate stays consistent automatically — no gate change is
needed. The regenerated pages must be committed alongside the source change, or
`catalog_validation` goes red.

### 12.2 Add the GitHub Actions deploy workflow

New file `.github/workflows/docs.yml`, using the official Pages actions — no third-party
dependencies. The build step mirrors `ci/docs.yml` so the two cannot
drift:

- trigger: `push` to `main`, plus `workflow_dispatch` for manual redeploys
- `permissions: { pages: write, id-token: write, contents: read }`
- Python 3.11, matching `requires-python = ">=3.11"`
- `pip install -e .[docs]` — the `docs` extra is self-contained
  (`mkdocs>=1.5`, `mkdocs-material>=9.0`) and needs no project dependencies
- `mkdocs build --strict` → `actions/upload-pages-artifact` → `actions/deploy-pages`
- `concurrency: { group: pages, cancel-in-progress: false }` so overlapping pushes do not
  race

Keeping `--strict` on the GitHub side as well is deliberate: the mirror can carry a commit
whose GitLab pipeline was never green, and a broken-link failure should stop the deploy
rather than publish it.

### 12.3 Gate the GitLab check

Publication is gated on the existing checks. The deploy now lives on GitHub, so the
GitLab-side expression of that is to make the `docs` job depend on the catalog gate, so a
stale catalog surfaces before a mirrored commit reaches GitHub:

- add `needs: [catalog_validation]` to the `docs` job in `ci/docs.yml`

On the GitHub side, `--strict` in the workflow is the equivalent guard.

`.gitignore` already contains `site/`; no change needed there.

## Files

| File | Change |
|---|---|
| `.github/workflows/docs.yml` | new — build + deploy to Pages |
| `mkdocs.yml` | `site_url` → `fashouri1.github.io` |
| `pyproject.toml` | `Documentation` URL |
| `scripts/generate_catalog_pages.py` | `DEFAULT_SITE_URL` |
| `ci/docs.yml` | `needs: [catalog_validation]` |
| `docs/_generated/catalog/cases/*.md` | 134 files, JSON-LD URL only (regenerated) |

## Verification

Local, before pushing:

```
python scripts/generate_catalog_pages.py          # regenerate
python scripts/generate_catalog_pages.py --check  # gate agrees
python -m mkdocs build --strict                   # zero warnings
python -m pytest tests -q                         # 786 passed, 1 skipped
python -m ruff check src tests && python -m mypy src
```

Confirm no stale host remains:

```
grep -rl "farzinashouri.github.io" docs/ mkdocs.yml pyproject.toml scripts/
# expected: no output
grep -c "fashouri1.github.io" docs/_generated/catalog/cases/dem_small.md
# expected: 2  (url + isPartOf.url)
```

Render the built site locally — this is the check that would have caught the original
report, and the reason a `--strict` build alone was not enough:

```
python -m mkdocs serve
# open /_generated/catalog/cases/dateline_crossing_polygon/
# expect: badges, a teal polygon schematic, caption; not bare text
```

After the mirror and Pages source are configured, push to `main`, confirm the Actions run
is green, and confirm `https://fashouri1.github.io/geocase` serves the Case Catalog with
schematics visible.

## Note on reversibility

Enabling Pages publishes the docs at a public URL. That is the intent, but it is the
outward-facing step in this plan, which is why the three prerequisites above are left for
a human to perform rather than automated here.

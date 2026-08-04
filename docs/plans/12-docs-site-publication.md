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
  `farzinashouri.github.io/geocase` — a host nothing deploys to *yet*. With the GitHub
  account `github.com/farzinashouri` now created, this URL is correct and no longer needs
  changing; only the deployment is missing.
- The same URL is baked into all 134 generated case pages as the JSON-LD `url` and
  `isPartOf.url`, which is the Google Dataset Search surface the generator exists to feed.
  Those are correct as written — no regeneration is required.

Target: `https://farzinashouri.github.io/geocase`, deployed by GitHub Actions from a mirror
of the GitLab repo. GitLab CI keeps its `--strict` check; GitHub does the publishing.

## Prerequisites (manual, outside this repo)

The CI work is inert until these are done, and they are deliberately left to a human:

1. Create `github.com/farzinashouri/geocase` — **empty**, with no README, `.gitignore`, or
   license, so the first mirror push does not conflict. (The account
   `github.com/farzinashouri` already exists; the repository does not yet.) Description:
   the `pyproject.toml` `description` verbatim — "A curated library of geospatial test
   cases for automated and parameterized testing."
2. In GitLab: **Settings → Repository → Mirroring repositories**. Mirroring is configured
   only on the GitLab side — GitHub has no corresponding setting, because the direction is
   GitLab → GitHub. Add a push mirror to `https://github.com/farzinashouri/geocase.git`,
   mirror direction **Push**, authentication **Username and Password**, username
   `farzinashouri`, password a GitHub PAT with `repo` scope. Both checkboxes stay
   **unchecked**:
   - *Keep divergent refs* — off, so GitLab force-pushes and GitHub always matches GitLab
     exactly. On, any diverged branch silently stops mirroring. This one is **immutable
     after creation** except via the API, so it must be right the first time.
   - *Mirror only protected branches* — off, so every branch and tag mirrors, not just
     `main`.

   Then use **Update now** on the new mirror row to trigger the first sync.
3. In GitHub: **Settings → Pages → Source: GitHub Actions**.

GitLab push mirroring pushes the full repository — every commit, branch, and tag — not a
squashed snapshot. So the GitHub copy carries the complete commit history, and it stays in
sync on each subsequent push. (Only the initial mirror sync must be allowed to finish; use
**Update now** on the mirror row to trigger it.)

## Steps

### 12.1 Canonical URL — no change required

With the account `github.com/farzinashouri`, the existing value
`https://farzinashouri.github.io/geocase` is already the correct published host in all
three places (`mkdocs.yml` `site_url`, `pyproject.toml` `Documentation`,
`scripts/generate_catalog_pages.py` `DEFAULT_SITE_URL`), and therefore in the JSON-LD of
all 134 generated case pages. No edit, no regeneration, no gate churn.

Only confirm the gate still agrees:

```
python scripts/generate_catalog_pages.py --check
```

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
| `ci/docs.yml` | `needs: [catalog_validation]` |

`mkdocs.yml`, `pyproject.toml`, `scripts/generate_catalog_pages.py`, and the 134 generated
case pages are unchanged — their `farzinashouri.github.io` URL is already correct.

## Verification

Local, before pushing:

```
python scripts/generate_catalog_pages.py --check  # gate agrees
python -m mkdocs build --strict                   # zero warnings
python -m pytest tests -q                         # 786 passed, 1 skipped
python -m ruff check src tests && python -m mypy src
```

Confirm the canonical host is the one that will be served:

```
grep -c "farzinashouri.github.io" docs/_generated/catalog/cases/dem_small.md
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
is green, and confirm `https://farzinashouri.github.io/geocase` serves the Case Catalog with
schematics visible.

## Note on reversibility

Enabling Pages publishes the docs at a public URL. That is the intent, but it is the
outward-facing step in this plan, which is why the three prerequisites above are left for
a human to perform rather than automated here.

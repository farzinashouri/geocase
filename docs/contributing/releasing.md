---
description: How a GeoCase version reaches PyPI and conda-forge, and the reasoning behind each release step.
---

# Releasing

How a GeoCase version reaches PyPI and conda-forge. For the general reasoning
behind these steps — portable to any Python package — see
[PyPI publishing practices](pypi-publishing-practices.md).
For the short step-by-step checklist, see
[PyPI release steps](pypi-release-steps.md).

The governing constraint is that **PyPI artifacts are immutable**. A version
number, once uploaded, can never be reused — not after a deletion, not after a
yank. A wheel that installs cleanly but ships without `geocase/data/**` would be
a permanently broken `1.0.0`. Every gate below exists because of that.

## One-time setup

### Trusted publishing (OIDC)

Uploads authenticate with a short-lived token minted from a GitHub Actions
OIDC JWT — the workflow requests it via `id-token: write`.
Nothing long-lived is stored in CI variables, so there is no credential to leak
or rotate.

On **both** [test.pypi.org](https://test.pypi.org) and
[pypi.org](https://pypi.org) → *Publishing* → *Add a pending publisher* →
**GitHub**:

| Field | Value (pypi.org) | Value (test.pypi.org) |
|---|---|---|
| PyPI Project Name | `geocase` | `geocase` |
| Owner | `farzinashouri` | `farzinashouri` |
| Repository name | `geocase` | `geocase` |
| Workflow name | `release.yml` | `release.yml` |
| Environment name | `pypi` | `testpypi` |

The environment names are **not** optional here and must match exactly: the
publish jobs in `.github/workflows/release.yml` declare `environment: pypi` and
`environment: testpypi`, and a mismatch fails the token mint with a 403 — after
the tag is already cut.

Create the two environments under the repository's *Settings → Environments*.
Adding a required reviewer to each is what makes publishing a deliberate,
approved step rather than an automatic consequence of pushing a tag.

!!! warning "Only `pypi` has a reviewer"

    Until 2026-09-27 neither environment had a required reviewer, so a tag push
    uploaded to TestPyPI and PyPI at once. Now `pypi` requires the owner's
    approval and `testpypi` deliberately has none: the TestPyPI upload is the
    rehearsal the pipeline smoke-tests before asking for that approval.

A *pending* publisher works before the project exists on PyPI, which is exactly
the first-release case; it converts to a normal publisher on first upload.

TestPyPI is a separate account and registry from PyPI. Both are needed: the dry
run below is not optional.

## Before tagging

Run the artifact gate locally. CI runs the same commands, but a failure here
costs nothing while a failure after a tag is cut costs a version number.

```bash
rm -rf dist/
python -m build
python scripts/verify_dist.py dist/ --expected-version v1.0.0
twine check dist/*
```

`verify_dist.py` fails loudly if:

- any of the 174 cases in `case-index.yaml` is missing from the wheel, or ships
  metadata with no data payload (`verify_dist.py` reads the count from the index;
  this figure is gated against the registry by `scripts/validate_catalog.py`);
- the sdist is missing `src/geocase/data`, `src/geocase/metadata`, or `tests`;
- either artifact contains `__pycache__`, `*.pyc`, or `.DS_Store`;
- either artifact exceeds 2 MB (measured at 1.0.0: wheel 456 KB, sdist 272 KB);
- the tag, the artifact filenames, and `project.version` in `pyproject.toml`
  disagree.

!!! note "The version gate reads `pyproject.toml`, not `geocase.__version__`"

    `verify_dist.py` parses `project.version` out of `pyproject.toml`
    deliberately. `geocase.__version__` resolves through `importlib.metadata`,
    so it reports whatever is *installed* — a stale editable install would fail
    the gate with a confusing mismatch, and on a clean CI runner the import
    fails outright. `pyproject.toml` is the source of truth, so bumping the
    version there is all a release needs.

The sdist matters as much as the wheel: **conda-forge builds from the sdist**,
and it carries `tests/` so the recipe can run the suite against the installed
package.

## Release sequence

Since Plan 50 the sequence is automated: **Prepare release** opens a release PR,
merging it starts **Release**, which tags, builds, uploads to TestPyPI, smoke-tests
the TestPyPI package in clean runners, and waits for approval before PyPI. After
the upload it smoke-tests PyPI, creates the GitHub release and closes the release
issue. The steps, and the two actions left to a person, are in
[PyPI release steps](pypi-release-steps.md).

The manual TestPyPI rehearsal that 1.0.0 needed (an rc version bump and back) is
gone: TestPyPI is a separate registry, so the pipeline uploads the real version
there first, with `skip-existing` so a version rehearsed by hand does not fail.

To check a published version by hand, the same things the smoke test checks:

```bash
python -m venv /tmp/gc && . /tmp/gc/bin/activate
pip install geocase==1.1.0
python -c "import geocase; print(geocase.__version__, len(geocase.__all__))"   # 1.1.0 29
python -c "import geocase; print(len(geocase.list_cases()))"   # 174
```

## conda-forge

conda-forge builds from the published PyPI sdist and needs its sha256, so this
can only start **after** the upload above. That ordering is inherent.

```bash
curl -sL https://pypi.org/pypi/geocase/1.0.0/json \
  | python -c 'import json,sys; print([u["digests"]["sha256"] for u in json.load(sys.stdin)["urls"] if u["packagetype"]=="sdist"][0])'
```

Then fork [conda-forge/staged-recipes](https://github.com/conda-forge/staged-recipes),
add `recipes/geocase/meta.yaml` (see `recipe/meta.yaml` in this repository),
open a PR, and respond to the linter bot.

The recipe keeps the optional extras **out** of `run` requirements: geopandas
and rasterio are optional in `pyproject.toml`, and pulling GDAL into the base
package would make the conda package far heavier than the PyPI equivalent.

Once the feedstock is created, its autotick bot opens a version-bump PR
automatically on each later PyPI release, so subsequent releases only need the
PyPI upload.

## Subsequent releases

1. Keep `CHANGELOG.md`'s `[Unreleased]` section current as work lands.
2. Run **Prepare release** with the new version; merge its PR.
3. Approve `publish-pypi` after reading the smoke-test summary.
4. Merge the autotick bot's conda-forge PR.

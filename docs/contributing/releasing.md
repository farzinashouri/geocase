# Releasing

How a GeoCase version reaches PyPI and conda-forge. For the general reasoning
behind these steps — portable to any Python package — see
[PyPI publishing practices](pypi-publishing-practices.md).

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

- any of the 150 cases in `case-index.yaml` is missing from the wheel, or ships
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

### 1. Land the work

Merge to `main` with a green pipeline. Tags are cut from `main`.

### 2. Dry run against TestPyPI

Never spend the real version number on a rehearsal. The rc needs a real version
bump, not just an rc tag — `verify_dist.py` enforces that the tag and
`pyproject.toml` agree:

```bash
# set version = "1.0.0rc1" in pyproject.toml, commit
git tag -a v1.0.0rc1 -m "GeoCase 1.0.0rc1"
git push origin v1.0.0rc1
```

Pushing the tag runs the `build` job automatically. The `publish-testpypi` job
then waits on the `testpypi` environment — **approve it** from the run's page in
the Actions tab to upload.

`release.yml` also accepts `workflow_dispatch`, so a rehearsal can be run from
the Actions tab against any ref without cutting a tag. The trade-off: with no
tag there is nothing to check the artifact version against, so the run verifies
the wheel and sdist against `pyproject.toml` only. Prefer the tag for anything
reaching real PyPI — a PyPI release is immutable, and the tag is what records
which commit it was built from.

Verify the result in a clean environment:

```bash
python -m venv /tmp/gc && . /tmp/gc/bin/activate
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ geocase==1.0.0rc1
python -c "import geocase; print(geocase.__version__, len(geocase.__all__))"  # 1.0.0rc1 27
# bundled data really materialised, not just importable
python -c "import geocase; c = geocase.load_case('cog_multispectral_small'); print(c.primary_path.exists())"
python -c "import geocase; print(len(geocase.list_cases()))"   # 150
pytest --collect-only 2>&1 | head   # plugin registers
```

The `--extra-index-url` is required: TestPyPI does not mirror `pydantic` or
`pyyaml`.

This step is what catches an OIDC misconfiguration, which otherwise surfaces as
a 403 at upload time on the real registry.

### 3. Publish to PyPI

Bump back to `1.0.0`, commit, then:

```bash
git tag -a v1.0.0 -m "GeoCase 1.0.0"
git push origin v1.0.0
```

**Approve `publish-pypi`** on the `pypi` environment. Both publish jobs sit
behind an environment gate because cutting a tag and uploading should not be the
same action.

Verify:

```bash
python -m venv /tmp/gc2 && . /tmp/gc2/bin/activate
pip install geocase==1.0.0
python -c "import geocase; print(len(geocase.__all__))"   # 27
```

Confirm the project page lists **both** a wheel and an sdist — conda-forge needs
the sdist in the next step.

### 4. Update the changelog date

`CHANGELOG.md` records the release date. If the upload slipped past the date in
the entry, correct it rather than leaving a false one.

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

1. Bump `version` in `pyproject.toml`; update `CHANGELOG.md`.
2. Local gate, merge to `main`.
3. Tag `vX.Y.Z`, push, approve `publish-pypi`.
4. Merge the autotick bot's conda-forge PR.

The TestPyPI rehearsal is worth repeating for anything touching packaging —
`pyproject.toml` build targets, new data directories, a Python version bump.

# PyPI release, step by step

The short checklist for putting a version on pypi.org. The reasons behind each
step are in [Releasing](releasing.md); conda-forge is covered there too, not here.

The examples use `1.1.0`. Replace it with the version you release.

**Rule to remember:** a version uploaded to PyPI can never be uploaded again, even
after you delete it. Every step before step 6 exists so that step 6 happens once.

## 0. One-time: make uploads wait for your approval

Do this once per repository. Check it before every release.

1. GitHub → repository → *Settings* → *Environments*.
2. Open `pypi`. Under *Deployment protection rules*, tick **Required reviewers**
   and add yourself. Save.
3. Do the same for `testpypi`.

Without this, the publish jobs in `release.yml` do not pause: pushing a tag, or
running the workflow by hand, uploads to TestPyPI **and** PyPI at once.

Check it from a terminal (both lines must show `reviewers=1`):

```bash
gh api repos/farzinashouri/geocase/environments \
  -q '.environments[]|select(.name|test("pypi"))|"\(.name) reviewers=\([.protection_rules[]?|select(.type=="required_reviewers")]|length)"'
```

Trusted publishing (OIDC) must also be set up on pypi.org and test.pypi.org; see
[Releasing → One-time setup](releasing.md#one-time-setup). It is already done for
`geocase`.

## 1. Check that `main` is ready

- `version` in `pyproject.toml` is `1.1.0`.
- `CHANGELOG.md` has a `## [1.1.0] — <date>` section, and `docs/changelog.md` is
  regenerated (`python scripts/generate_changelog_page.py --check`).
- CI is green on the latest `main` commit.
- The version is not on PyPI yet:

```bash
curl -s https://pypi.org/pypi/geocase/json \
  | python -c 'import json,sys; print(sorted(json.load(sys.stdin)["releases"]))'
```

## 2. Build and check locally

```bash
git switch main && git pull
rm -rf dist/
python -m build
python scripts/verify_dist.py dist/ --expected-version v1.1.0
twine check dist/*
```

All three must pass. If one fails, fix it on a branch and merge first. Nothing is
spent yet.

## 3. Rehearse on TestPyPI

Run the release workflow by hand, without a tag:

1. GitHub → *Actions* → **Release** → *Run workflow* → branch `main` → *Run*.
2. Wait for the `build` job to pass.
3. The run now waits on two approvals. **Approve `publish-testpypi`.**
   **Reject `publish-pypi`.**

This uploads `1.1.0` to TestPyPI only. TestPyPI is a separate registry, so this
does not use up the real `1.1.0`.

## 4. Test the TestPyPI package in a clean environment

```bash
python -m venv /tmp/gc && . /tmp/gc/bin/activate
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ geocase==1.1.0
python -c "import geocase; print(geocase.__version__, len(geocase.list_cases()))"   # 1.1.0 174
python -c "import geocase; print(geocase.load_case('cog_multispectral_small').primary_path.exists())"   # True
pytest --collect-only 2>&1 | head   # the plugin registers
deactivate
```

The `--extra-index-url` is needed because TestPyPI does not have `pydantic` or
`pyyaml`.

If the release adds or changes an extra, install it too. For `1.1.0`, the `array`
extra:

```bash
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ "geocase[array]==1.1.0"
python -c "from geocase.raster import raster_fixture; print('ok')"
```

If anything fails here, stop. Fix it, bump to a new version, and start again from
step 1. Do not tag.

## 5. Tag the release

```bash
git switch main && git pull
git tag -a v1.1.0 -m "GeoCase 1.1.0"
git push origin v1.1.0
```

The tag starts the release workflow again, and `build` checks that the tag, the
artifact names and `pyproject.toml` agree.

## 6. Approve the PyPI upload

1. GitHub → *Actions* → the **Release** run for `v1.1.0`.
2. Wait for `build` to pass.
3. **Approve `publish-pypi`.**
4. **Reject `publish-testpypi`.** `1.1.0` is already on TestPyPI from step 3, and
   a second upload of it would fail.

This is the step that cannot be undone.

## 7. Verify on PyPI

```bash
python -m venv /tmp/gc2 && . /tmp/gc2/bin/activate
pip install geocase==1.1.0
python -c "import geocase; print(geocase.__version__, len(geocase.__all__))"   # 1.1.0 29
deactivate
```

Open <https://pypi.org/project/geocase/1.1.0/#files> and check that it lists
**both** a wheel (`.whl`) and an sdist (`.tar.gz`). conda-forge builds from the
sdist.

## 8. Finish

- If the upload date differs from the date in `CHANGELOG.md`, correct the date
  and regenerate `docs/changelog.md`.
- Create the GitHub release from the tag:
  `gh release create v1.1.0 --title "GeoCase 1.1.0" --notes-from-tag`, or paste
  the changelog section as notes.
- Close the release issue.

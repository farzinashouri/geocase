# PyPI release, step by step

The short checklist for putting a version on pypi.org. The reasons behind each
step are in [Releasing](releasing.md); conda-forge is covered there too, not here.

Since Plan 50 the release is one pipeline with **two human actions**: merge the
release PR, and approve the PyPI upload. Everything else runs in
`.github/workflows/prepare-release.yml` and `.github/workflows/release.yml`.

**Rule to remember:** a version uploaded to PyPI can never be uploaded again, even
after you delete it. The approval in step 4 is the point of no return.

## 0. One-time setup (check before a release)

- *Settings → Environments → `pypi`*: **Required reviewers** includes you.
  `testpypi` has no reviewer: it is the rehearsal and runs by itself.
- *Settings → Actions → General → Workflow permissions*: **Allow GitHub Actions
  to create and approve pull requests** is ticked (needed by step 1).
- Trusted publishing is set up on pypi.org and test.pypi.org
  ([Releasing → One-time setup](releasing.md#one-time-setup)).

Check the reviewers from a terminal (`pypi` must show `reviewers=1`):

```bash
gh api repos/farzinashouri/geocase/environments \
  -q '.environments[]|select(.name|test("pypi"))|"\(.name) reviewers=\([.protection_rules[]?|select(.type=="required_reviewers")]|length)"'
```

## 1. Start the release (automatic)

Make sure `CHANGELOG.md` has a non-empty `## [Unreleased]` section on `main`.
Then: *Actions → **Prepare release** → Run workflow* → version, e.g. `1.2.0`.
Or from a terminal:

```bash
gh workflow run prepare-release.yml -f version=1.2.0
```

It bumps `pyproject.toml`, renames `[Unreleased]` to `[1.2.0] — <today>`,
regenerates `docs/changelog.md`, and opens the PR **"Release 1.2.0"** with CI
running on it. It refuses a version that is not greater than the current one,
and an empty `[Unreleased]` section.

## 2. Merge the release PR (you)

Read the PR: the version and the changelog text are what will be published.
Merge it when CI is green.

## 3. Tag, build, TestPyPI, smoke test (automatic)

Merging starts **Release** on `main`. It:

1. tags `v1.2.0`;
2. builds the wheel and sdist and runs `verify_dist.py` and `twine check`;
3. uploads to TestPyPI;
4. installs from TestPyPI in clean runners — plain `geocase` and
   `geocase[array]` — and runs `scripts/smoke_release.py` plus one pytest-fixture
   test. The results are in the run's **Summary** tab.

If any of this fails, nothing reached PyPI. Fix it and release a new version:
the version number is not spent, but the tag is, so delete the tag first
(`git push origin :refs/tags/v1.2.0`) or bump.

## 4. Approve the PyPI upload (you)

Open the run (*Actions → Release*), read the smoke-test tables in the
**Summary**, then *Review deployments → `pypi` → Approve and deploy*.

## 5. Verify and publish the release (automatic)

After the upload the pipeline installs from real PyPI and runs the same smoke
test, creates the GitHub release `v1.2.0` with the changelog section as notes,
and closes the open `release` issue whose title names the version.

Check <https://pypi.org/project/geocase/1.2.0/#files> lists a wheel and an sdist
if you want to see it yourself.

## Without the pipeline

A hand-pushed tag (`git tag -a v1.2.0 -m "GeoCase 1.2.0" && git push origin v1.2.0`)
runs the same pipeline from step 3. A manual *Run workflow* on **Release** builds
whatever ref you pick and has no tag, so it skips the GitHub release.

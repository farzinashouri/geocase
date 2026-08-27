---
description: "Transferable practice for publishing a Python package to PyPI: why immutability drives every gate, how to rehearse on TestPyPI, and the failure modes that only appear at upload time."
---

# PyPI publishing practices

General practice for shipping a Python package to PyPI, written to be portable to
any project. For the GeoCase-specific procedure — the exact commands, the trusted
publisher fields, the conda-forge follow-up — see [Releasing](releasing.md).

Everything here was learned by doing it, mostly from the `geofacts 0.1.2` and
`geocase 1.0.0rc2` releases in August 2026. Where a rule exists because something
actually broke, the failure is named.

## The one rule everything else follows from

**A version number on PyPI is spent forever.** Upload `1.0.0`, and that number is
permanently bound to those exact bytes. Deleting the files does not free it.
Yanking does not free it. There is no support ticket that frees it.

So the cost of a mistake is asymmetric in a way most software work is not. A bad
commit is amended; a bad release is a new version number and a public record of
the bad one. Every practice below buys down the chance of discovering a problem
*after* the number is spent.

The corollary that matters day to day: **make failures happen early and cheaply.**
A local build that fails costs nothing. A CI failure costs a re-run. An upload
failure costs a version number.

## Rehearse on TestPyPI, with a real release candidate

[test.pypi.org](https://test.pypi.org) is a separate registry with separate
accounts. Publish there first, always, using a pre-release version — `1.0.0rc1`,
`1.0.0rc2` — rather than the number you intend to ship.

Pre-release versions are the right instrument because `pip` ignores them by
default (they need `--pre`), and they sort before the final release, so
`1.0.0rc2 < 1.0.0`. You get a real upload against a real index without spending
the number that matters.

Rehearse the mechanism you will actually use for the real release. If production
publishes on a tag, tag the rehearsal — a rehearsal that exercises a manual
button tests a path you will not use when it counts.

**Do not treat TestPyPI as a dependency source.** It is periodically pruned and
has no availability promise. If your package depends on another package you also
control, that dependency belongs on real PyPI before the rehearsal, and the
rehearsal install needs both indexes:

```bash
pip install -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ yourpackage
```

The `--extra-index-url` is what lets ordinary dependencies resolve from real
PyPI while your package comes from TestPyPI.

## Verify from a clean environment, not your working tree

The most dangerous class of packaging bug is the one your development machine
cannot see, because your machine has the source tree, an editable install, and a
sibling checkout on the path. Any of those can satisfy an import that a real user's
install would not.

GeoCase hit exactly this shape: `geocase` depends on `geofacts`, which for months
resolved only from a sibling `../geofacts` checkout. Locally everything imported.
Nothing proved a real user could install it. The question was only genuinely
answered by a clean-venv install from an index, with no sibling on the path.

So verification means a fresh virtualenv, installing from the index, asserting on
behaviour rather than importability:

- the package imports, and `__file__` points inside `site-packages`
- the **public API** is the shape you promised (a name count, a symbol list)
- **bundled data actually materialises** — a wheel can install cleanly and ship
  none of its data files
- any **entry points** register (plugins, console scripts) in a directory holding
  no project config
- **dependencies resolve from the index**, not from your disk

That last one is only ever tested by the clean install. Everything before it can
pass on a machine where the answer is being faked.

## Pin the build backend, not just the tools

This one cost a release run. `release.yml` pinned `build` and `twine`, which
looked like careful practice — but the *backend* came from
`[build-system] requires = ["hatchling"]` in `pyproject.toml`, unpinned. CI
resolved a newer hatchling, which emitted `Metadata-Version: 2.5`, which the
pinned `twine==6.1.0` rejected outright:

```
InvalidDistribution: Invalid distribution metadata: '2.5' is not a valid metadata version
```

The artifact was never wrong. Only the validator was too old to recognise it.

Two lessons, both general:

**The build backend decides your metadata version, so pin it with the tools that
validate that metadata.** A pinned validator and an unpinned producer will drift
apart, and the drift surfaces at upload time.

**A green local check is not evidence unless your local tool matches the CI pin.**
The same wheel passed locally on `twine 7.0.0` and failed in CI on `6.1.0`. When a
gate disagrees between local and CI, compare tool versions before you suspect the
artifact.

## Separate cutting a release from publishing it

Tagging and uploading should be two actions, because only one of them is
reversible. The standard mechanism on GitHub is an [environment][envs] with a
required reviewer: the build runs automatically, then the publish job *pauses*
for approval.

[envs]: https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment

This gives you a real window to inspect what was built before it becomes
permanent, and it means an accidental tag push cannot publish anything on its own.

Where a workflow has both a TestPyPI and a real-PyPI job triggered by the same
tag, the approval step is also the moment to confirm **which** you are approving.

## Use trusted publishing (OIDC) instead of API tokens

Trusted publishing has the CI provider mint a short-lived identity token that the
index exchanges for a ~15-minute upload token. No long-lived credential is stored
in CI secrets, so there is nothing to leak, rotate, or accidentally print.

Register the publisher on **both** indexes before the first upload — the
"pending publisher" flow exists precisely for projects that do not exist yet, and
converts to a normal publisher on first upload.

The field that most often gets it wrong is the **workflow name**: it is the
*filename* (`release.yml`), not the `name:` value inside the file. The
environment name must also match the workflow's `environment:` exactly.
A mismatch fails as a `403` at upload — after the tag is cut.

## Gate the artifact's contents, not just that it built

`twine check` validates metadata rendering. It does not tell you whether your
package's data files are present, and a wheel missing them installs perfectly
happily.

Worth a project-specific script, run locally *and* in CI, asserting whatever
would make a release permanently broken. For GeoCase that is
[`scripts/verify_dist.py`](https://github.com/farzinashouri/geocase/blob/main/scripts/verify_dist.py),
which checks every indexed case is present in the wheel, that the version matches
the tag, and that no `__pycache__`/`.pyc`/`.DS_Store` slipped in.

The general principle: enumerate what a broken-but-installable release would look
like for your package, and assert against it.

## Watch what the sdist includes

Wheels and sdists have different inclusion rules, and it is easy to ship an sdist
that cannot do what people build from it. Downstream packagers — conda-forge
especially — build from the **sdist** and often run your test suite from it.

`geofacts` had to widen its sdist beyond the obvious `src/` + `tests/` to carry
`scripts/` and `vendored/`, because a test regenerates a vendored file via a
script and diffs it. Dropping either turned a drift gate into a collection error
exactly where it mattered most.

Check by unpacking the built sdist into a clean environment and running the suite
from *there*, not from your repo.

## Version numbers live in more places than you think

`geofacts` hardcodes its version in three independent places — `pyproject.toml`,
`__init__.py`, and a template literal in a build script — and **nothing gates them
against each other**. They can silently disagree.

Either derive the version from one source, or add a test asserting the copies
agree. A release where the metadata and the runtime `__version__` disagree is
confusing in a way that outlives the release.

## On moving a tag

Moving a published tag is normally bad practice: anyone who already fetched it
keeps the old one, and a later `git fetch` will not correct it without
`--prune-tags`.

It is defensible in one narrow case — **nothing consumed it**. When
`v1.0.0rc2`'s first run failed at `twine check`, nothing was uploaded, so the
version was still unspent on the index and the tag could be deleted and re-cut:

```bash
git push origin --delete v1.0.0rc2   # or: git push origin :refs/tags/v1.0.0rc2
git tag -d v1.0.0rc2
```

If anything *did* get uploaded, the tag is spent along with the version. Burn a
new release-candidate number instead — they are cheap, and that is what they are
for.

## A checklist

1. Land the work; the release is cut from the default branch.
2. Bump the version to a release candidate.
3. Build and gate **locally** — build, verify contents, `twine check`.
4. Tag the rc, push, approve the **TestPyPI** publish.
5. Install from TestPyPI into a **clean venv** and assert on behaviour.
6. Only then bump to the real version, tag, and approve the **PyPI** publish.
7. Update the changelog with the real release date.

Steps 3 through 5 are the ones people skip, and they are the ones that protect the
number you cannot get back.

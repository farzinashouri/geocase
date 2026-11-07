# The `geocase` Claude Code plugin

A Claude Code plugin for people who test their geospatial code with GeoCase.
Skills (Plan 55):

- `cases`: given a function or file, picks fitting catalog cases and ends with
  the `geocase_select(...)` marker that selects them. Claude may load it on its
  own when a request fits.
- `test`: given a function, picks cases the same way, writes one pytest file
  (a `geocase_select` marker, the `geocase` fixture, the call, and
  `geocase.assertions` checks where one fits), runs it and reports which cases
  pass and fail. It never edits the function under test.
- `explain`: given failing test output, takes the case id from the test id
  (`test_x[<case_id>]`), reads the case with `catalog.py case <id>`, and
  explains the data, correct handling and the likely bug. A catalogued
  `known_divergences` entry is reported as known. It proposes a fix and
  applies it only if asked.

## Environment detector

`scripts/env.py detect [--version V] [--project DIR]` prints, as JSON, which
manager owns the project's environment (checked in order: pixi, uv, poetry,
conda, venv) and the install command pinned to `V`. For pixi, uv and poetry the
command edits the project's manifest (`edits_manifest: true`). Conda `base` and
`EXTERNALLY-MANAGED` Pythons come back with `installable: false` and a reason.
It only reads env vars and files and never installs.

## Sandbox builder

`scripts/sandbox.py status` and `sandbox.py create [--upgrade]` print, as JSON,
`exists`, `python` and `geocase_version` of a private venv at
`$CLAUDE_PLUGIN_DATA/sandbox` (fallback `~/.cache/geocase-claude-plugin/sandbox`).
`create` runs `python -m venv`, then `pip install geocase` from PyPI; a second run
does nothing. The sandbox is for reading (`cases`, `explain`), not for `test`.
`status` creates nothing.

## Catalog helper

`scripts/catalog.py` prints the catalog as JSON, read through the installed
`geocase` package. The skills run it with the user's own Python:

```text
python scripts/catalog.py cases --category vector --risk crs/axis_order
python scripts/catalog.py case <case_id>      # metadata plus the notes.md text
python scripts/catalog.py risks               # risk type -> case ids
```

`--risk` and `--tag` repeat for any-of, and a risk family (`crs`) selects all
its terms. Exit codes: 2 for an unknown case id or a bad filter, 3 when
`geocase` is not importable. It uses only `geocase.__all__`; its tests
(`tests/test_catalog_helper.py`) pin that and run in the CI `tests` job.

## Install (once per machine)

From the repo root, in Claude Code:

```text
/plugin marketplace add ./
/plugin install geocase@geocase
```

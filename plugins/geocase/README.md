# The `geocase` Claude Code plugin

A Claude Code plugin for people who test their geospatial code with GeoCase.
Skills (Plan 55):

- `cases`: given a function or file, picks fitting catalog cases and ends with
  the `geocase_select(...)` marker that selects them. Claude may load it on its
  own when a request fits.

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

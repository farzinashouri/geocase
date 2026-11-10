---
description: "Use GeoCase from Claude Code: three skills that pick catalog cases for your function, write the pytest file, and explain a failing case."
---

# Claude Code plugin

The `geocase` plugin lets Claude Code test your geospatial code against the
GeoCase catalog. It has three skills and needs **both** parts installed: the
plugin holds the skills, the `geocase` package holds the cases, the data and
the pytest fixtures, and must be importable in the environment your tests run in.

## When `geocase` is not installed

The skills read the catalog through the installed package. If it is missing
(the helper exits with code 3), they do not stop at "install geocase":

- `/geocase:cases` and `/geocase:explain` offer a **sandbox**: a private venv
  with `geocase` from PyPI. It does not touch your project, is created only
  after you say yes, and the skill then reads the catalog with the sandbox Python.
- `/geocase:cases` then offers to install `geocase` into your project, using
  the manager that owns the environment (pixi, uv, poetry, conda or venv). It
  shows the command and says whether it edits your manifest (pixi, uv and
  poetry add a dev dependency), and runs it only after a yes.
- `/geocase:test` skips the sandbox, because your tests import your code and
  its dependencies, and goes straight to the install offer.
- If the environment cannot take an install (conda `base`, an
  `EXTERNALLY-MANAGED` Python), the skill gives the reason and installs nothing.

## Install

In this order:

1. `pip install geocase` in the project's environment (the one your tests run in);
2. `/plugin marketplace add farzinashouri/geocase` (once, in Claude Code);
3. `/plugin install geocase@geocase`.

## The skills

| Skill | What it does |
|---|---|
| `/geocase:cases` | Given a function or file, picks fitting catalog cases and ends with the `geocase_select(...)` marker that selects them. |
| `/geocase:test` | Picks cases the same way, writes one pytest file, runs it and reports which cases pass and fail. It never edits your function. |
| `/geocase:explain` | Given failing test output, reads the case from the test id, explains the data, the correct handling and the likely bug. A catalogued `known_divergences` entry is reported as known. It applies a fix only if you ask. |

Claude may also load them on its own when a request fits, such as "check my
dateline handling".

## Worked example

You have `geotiff_footprint_to_geojson` in `gdal_footprint.py` and ask:

> Test `geotiff_footprint_to_geojson` against the GeoCase raster cases.

`/geocase:test` selects the raster cases that fit a footprint function and
writes a file like this:

```python
import pytest

from gdal_footprint import geotiff_footprint_to_geojson


@pytest.mark.geocase_select(category="raster")
def test_footprint(geocase, tmp_path):
    out = geotiff_footprint_to_geojson(geocase.primary_path, tmp_path / "out.geojson")
    assert out.exists()
```

It runs the file and lists the passing and failing case ids. For a failure
shown as `test_footprint[<case_id>]`, ask `/geocase:explain` and it reads that
case's notes and says what the data holds and why the function likely failed.

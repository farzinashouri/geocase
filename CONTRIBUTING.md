# Contributing to GeoCase

The full workflow lives in [docs/contributing/workflow.md](docs/contributing/workflow.md). This page is the short version.

## Environments

Two are maintained deliberately and are not interchangeable:

- **conda `geocase` (Python 3.14)** — `conda env create -f environment.yml && conda activate geocase`. The only environment with GDAL (`osgeo`). Use it for anything touching `examples/` or fixture generation.
- **`.venv` (CI mirror, Python 3.11)** — `python3.11 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"`. Use it to reproduce a CI failure at the supported floor.

## Rules

- **Test first.** Write the failing test, watch it fail, then write the code that makes it pass.
- **Docs follow code** in the same change. Generated files (`docs/_generated/*`, catalog pages, checksums) are regenerated, never hand-edited.
- **Corpus changes are named** in `CHANGELOG.md` by case id and by what changed.
- Adding a case: see [docs/adding-a-case.md](docs/adding-a-case.md).

## Gates

```bash
pytest tests -q
ruff format --check src tests && ruff check src tests
mypy src
mkdocs build --strict
```

Catalog gates are listed in [CLAUDE.md](CLAUDE.md) and need the conda environment.

## Found a bug?

Open an issue with the bug report template. Include the case id and a minimal repro.

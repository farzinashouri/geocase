---
description: "Turn a pytest JUnit report into a Markdown summary that names each failing GeoCase case, what it tests and its risk types."
---

# GeoCase in CI: a readable summary

`geocase.ci` turns a pytest JUnit XML report into a Markdown summary that names each
failing GeoCase case, what the case tests, and its risk types, so a reviewer
understands the failure without knowing GeoCase.

```bash
pytest tests --junitxml=junit.xml
python -m geocase.ci report junit.xml --out summary.md
```

Without `--out` the summary goes to stdout. The command always exits 0; decide
pass or fail from pytest itself.

The first line is a verdict (`N of M GeoCase cases pass`). If any case fails, a table
follows with the case id, its title, its `risk_types`, the test name and the first
line of the failure. Tests that use no GeoCase case are left out.

A test counts as a GeoCase test when its parameter id is a registered case id, which
is how the pytest plugin names parametrized tests (`test_x[<case_id>]`).

`geocase.ci` is a submodule, not part of `geocase.__all__`.

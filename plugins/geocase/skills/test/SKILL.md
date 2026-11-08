---
name: test
description: Write and run GeoCase tests for the user's geospatial function. Use when the user asks to test, check or harden a function against edge cases such as CRS, dateline, topology or NoData problems.
---

# Write and run GeoCase tests for a function

The user names a function. You write one pytest file that runs it against
catalog cases, run it, and report. You never edit the function under test:
if a case fails, say so and stop; fixing it is a separate request.

1. **Pick the cases** the way the `cases` skill does. Read the function, then run,
   with the user's own Python:

   ```text
   python ${CLAUDE_PLUGIN_ROOT}/scripts/catalog.py risks
   python ${CLAUDE_PLUGIN_ROOT}/scripts/catalog.py cases --category vector --risk crs/axis_order
   ```

   If the helper exits 3, `geocase` is not installed there. Do not read
   `case.yaml` files yourself. Skip the sandbox: the tests import the user's
   code and its dependencies, so `geocase` must be in the user's environment.
   Go straight to the install offer:

   ```text
   python ${CLAUDE_PLUGIN_ROOT}/scripts/env.py detect --version <version>
   ```

   (use the version the user already explored; omit `--version` if none). The JSON
   has `installable`, `command`, `reason` and `edits_manifest`. Show the
   `command`, say whether it edits the project's manifest, and run it only
   after a yes. If `installable` is false, give the `reason`, install nothing
   and stop.
2. **Write one file** in the user's test folder (`tests/test_<function>_geocase.py`),
   from this template. The selector uses only the filters you passed to the
   helper (`category`, `geometry_type`, `format`, `tags_any`, `risk_types_any`):

   ```python
   from __future__ import annotations

   import pytest

   from <module> import <function>


   @pytest.mark.geocase_select(<selector>)
   def test_<function>_on_geocase(geocase, tmp_path):
       result = <function>(geocase.primary_path, tmp_path / "out")
       assert result is not None
   ```

   Replace the placeholder call with the function's real signature. Add an
   assertion from `geocase.assertions` where one fits the output, for example
   `assert_footprint_no_holes` for a footprint, `assert_epsg` or `assert_has_crs`
   for a CRS, `assert_bounds` for an extent, `assert_no_self_intersections` for
   topology. Use only these fixtures and markers: `geocase`, `geocase_case`,
   `geocase_cases`, `geocase_registry`; `geocase_case`, `geocase_suite`,
   `geocase_select`, `remote`. To name cases directly use
   `@pytest.mark.geocase_case("id", ...)`.
3. **Run it**: `python -m pytest <the new file> -q` with the user's Python.
4. **Report** which cases pass and which fail, with the failing assertion's
   message for each. Do not change the function; offer to investigate as a
   separate step.

---
name: cases
description: Pick GeoCase test cases for a geospatial function. Use when the user asks which edge cases to test a function or file against, or what could break their reprojection, clipping, rasterizing or NoData handling.
---

# Pick GeoCase cases for a function

The user gives a function name or a file. Choose catalog cases that fit what it
actually does.

1. **Read the code** and decide what it does: reprojects, clips, rasterizes,
   reads NoData, crosses the dateline, reads a file format, and so on.
2. **List the risk terms.** Run, with the user's own Python (the one their tests use):

   ```text
   python ${CLAUDE_PLUGIN_ROOT}/scripts/catalog.py risks
   ```

   If it exits 3, `geocase` is not installed there. Do not read `case.yaml`
   files yourself. Offer a sandbox: a private copy of `geocase` kept in the
   plugin's data folder that does not touch the project. Only after a yes, run:

   ```text
   python ${CLAUDE_PLUGIN_ROOT}/scripts/sandbox.py create
   ```

   It prints JSON with `python` (the sandbox Python) and `geocase_version`.
   Rerun the `catalog.py` commands below with the sandbox Python instead of the
   user's. If the user says no, give `pip install geocase` and stop.
3. **Filter.** Pick the terms or families that match step 1, then:

   ```text
   python ${CLAUDE_PLUGIN_ROOT}/scripts/catalog.py cases --category vector --risk crs/axis_order --risk extent
   ```

   `--risk` repeats for any-of and a family name (`extent`) selects all its
   terms. Other filters: `--geometry-type`, `--format`, `--tag`. For a case you
   want to explain, run `catalog.py case <case_id>` to read its notes.
4. **Answer with a short table**: case id, the edge it exercises, why it fits
   this function. Keep it to the cases that matter, not the whole result.
5. **End with the selector** that selects the same set, for example:

   ```python
   @pytest.mark.geocase_select(category="vector", risk_types_any=["crs/axis_order", "extent"])
   def test_my_function(geocase):
       ...
   ```

   Use only the filters you passed to the helper (`category`, `geometry_type`,
   `format`, `tags_any`, `risk_types_any`), so the markers and the table agree.
6. **If you answered from the sandbox and found fitting cases, offer the
   install**, because the user's tests need `geocase` in their own environment:

   ```text
   python ${CLAUDE_PLUGIN_ROOT}/scripts/env.py detect --version <sandbox version>
   ```

   The JSON has `installable`, `command`, `reason` and `edits_manifest`. Show
   the `command`, say whether it edits the project's manifest
   (`edits_manifest`), and run it only after a yes. One yes covers one action.
   If `installable` is false, give the `reason` and install nothing.

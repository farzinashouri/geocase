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

   If it exits 3, `geocase` is not installed there: say so and give
   `pip install geocase`. Do not read `case.yaml` files yourself.
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

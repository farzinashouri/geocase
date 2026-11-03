---
name: explain
description: Explain why a GeoCase test case fails. Use when the user pastes or points to failing pytest output from a geocase test and asks what went wrong, why a case fails, or what the data is doing.
---

# Explain a failing GeoCase case

The user has a failing test that ran against a catalog case. You explain the
case and the likely bug. You propose a fix but apply it only if asked.

1. **Find the case id** in the failing test id. GeoCase parametrizes by case
   id, so `test_x[<case_id>]` carries it, for example
   `test_footprint[raster_dateline_crossing]` gives `raster_dateline_crossing`.
   If the id is not in the output, ask the user for the test id. Do not guess.
2. **Read the case** through the helper, with the user's own Python. Do not
   read `case.yaml` or `notes.md` files yourself:

   ```text
   python ${CLAUDE_PLUGIN_ROOT}/scripts/catalog.py case <case_id>
   ```

   The JSON holds the metadata, `risk_types`, `known_divergences` and the
   `notes` text. If the helper exits 2, the id is unknown: say so. If it exits
   3, `geocase` is not installed there: give `pip install geocase`.
3. **Check `known_divergences` first.** If it lists the library or behaviour
   the failure points at, say this is a **known** divergence catalogued by
   GeoCase, quote its entry, and say it is not necessarily the user's bug.
4. **Explain in plain words**, from `notes` and `risk_types`:
   - what is unusual about this data;
   - what correct handling looks like;
   - the likely bug in the user's function, after reading it and the
     assertion message.
5. **Propose a fix** as a short diff in the reply. Apply it only if the user
   asks. Never edit the function or the case data unprompted.

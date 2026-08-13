You are writing one small self-contained Python module. Work exclusively inside /private/tmp/claude-501/-Users-farzinashouri-projects-GeoCase-geocase/1cff4f84-ccad-4982-b62f-93cdd0d100d5/scratchpad/agentlab — do not read or modify anything outside that directory.

Task: Implement a function `area_m2(geom)` that takes a shapely `Polygon` or `MultiPolygon` whose coordinates are longitude/latitude in EPSG:4326 (WGS84) and returns its area in square meters as a `float`. Results should be accurate for polygons anywhere on Earth.

Requirements:
- Save the module as /private/tmp/claude-501/-Users-farzinashouri-projects-GeoCase-geocase/1cff4f84-ccad-4982-b62f-93cdd0d100d5/scratchpad/agentlab/generated/gen_area_m2.py. Importing the module must have no side effects.
- Interpreter: /private/tmp/claude-501/-Users-farzinashouri-projects-GeoCase-geocase/1cff4f84-ccad-4982-b62f-93cdd0d100d5/scratchpad/agentlab/venv/bin/python (Python 3 with shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, and scikit-learn installed). Use only the standard library plus whichever of these packages you need.
- Verify that your code actually runs before finishing; put any scratch test files under /private/tmp/claude-501/-Users-farzinashouri-projects-GeoCase-geocase/1cff4f84-ccad-4982-b62f-93cdd0d100d5/scratchpad/agentlab/scratch_area_m2/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.

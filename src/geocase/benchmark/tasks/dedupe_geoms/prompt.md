You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `dedupe_geoms(geoms)` that takes a list of shapely geometries and returns a new list with duplicates removed, keeping the first occurrence of each and preserving order. Two geometries are duplicates when they describe exactly the same set of points in the plane, even if their coordinate sequences differ — for example the same ring written from a different starting vertex or in the opposite direction.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, and scikit-learn installed). Use only the standard library plus whichever of these packages you need.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.

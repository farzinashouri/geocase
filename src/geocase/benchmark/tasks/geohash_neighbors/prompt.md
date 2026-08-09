You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `geohash_neighbors(gh)` that takes a geohash string and returns the geohashes (at the same precision) of the 8 cells surrounding that cell, as a list in any order. East and west neighbours wrap across the antimeridian; cells beyond the poles do not exist and are omitted, so a cell touching a pole has fewer than 8 neighbours.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, and scikit-learn installed). Use only the standard library plus whichever of these packages you need.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.

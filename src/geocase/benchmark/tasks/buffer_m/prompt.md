You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `buffer_m(geom, distance_m)` that takes a shapely geometry whose coordinates are longitude/latitude in EPSG:4326 (WGS84) and a distance in meters, and returns the geometry buffered (expanded) by that distance, again with coordinates in EPSG:4326. Results should be accurate anywhere on Earth.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, and scikit-learn installed). Use only the standard library plus whichever of these packages you need.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.

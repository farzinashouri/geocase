You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `geojson_bounds(path)` that takes the path to a GeoJSON file whose coordinates are longitude/latitude in EPSG:4326 (WGS84) and returns the bounding box of all its features as a 4-tuple of floats `(min_lon, min_lat, max_lon, max_lat)`. The bounding box should describe the actual extent of the geometry on Earth. Longitudes in the output must stay within `[-180, 180]`.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, and scikit-learn installed). Use only the standard library plus whichever of these packages you need.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.

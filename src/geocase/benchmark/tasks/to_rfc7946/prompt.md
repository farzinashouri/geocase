You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `to_rfc7946(geom, epsg)` that takes a shapely geometry and the integer EPSG code of the coordinate reference system its coordinates are in (any code, e.g. 4326 or 3857), and returns the geometry as a Python `dict` that is a valid GeoJSON geometry object strictly conforming to RFC 7946. Return only the geometry object (with `type` and `coordinates` members).

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, and scikit-learn installed). Use only the standard library plus whichever of these packages you need.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.

You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `split_antimeridian(polygon)` that takes a shapely `Polygon` whose coordinates are longitude/latitude in EPSG:4326 with longitudes in [-180, 180]. The polygon may cross the antimeridian, in which case consecutive vertices jump between values near +180 and values near -180. Return a list of valid shapely polygons that together cover exactly the same region of the Earth's surface and of which none crosses or touches the antimeridian except at its edge; a polygon that does not cross the antimeridian is returned as a single-element list, unchanged.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, and scikit-learn installed). Use only the standard library plus whichever of these packages you need.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.

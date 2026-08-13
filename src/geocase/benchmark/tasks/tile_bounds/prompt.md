You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `tile_bounds(z, x, y)` that returns the geographic extent, as a tuple `(west, south, east, north)` of WGS84 degrees, of the Web Mercator map tile with zoom `z`, column `x`, and row `y`, where tiles are addressed using the TMS tiling scheme. Return a tuple of four floats.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, and scikit-learn installed). Use only the standard library plus whichever of these packages you need.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.

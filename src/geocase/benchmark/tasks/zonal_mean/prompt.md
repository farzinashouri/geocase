You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `zonal_mean(raster_path, polygon)` that opens a single-band GeoTIFF with rasterio and returns, as a `float`, the mean of the values of all pixels whose centres fall inside the given shapely polygon, which is expressed in the raster's own coordinate reference system. Pixels equal to the raster's nodata value are excluded from the mean. Return `None` if no pixel with a valid value has its centre inside the polygon.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, and scikit-learn installed). Use only the standard library plus whichever of these packages you need.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.

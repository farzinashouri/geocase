You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `position_at(fixes, t)` where `fixes` is a chronologically sorted list of `(timestamp, lon, lat)` GPS fixes from a ship (timestamps are Unix seconds, positions are WGS84), and `t` is a timestamp between the first and last fix. Return the ship's estimated position at time `t` as a `(lon, lat)` tuple. Results should be accurate anywhere on the ocean.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, and scikit-learn installed). Use only the standard library plus whichever of these packages you need.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.

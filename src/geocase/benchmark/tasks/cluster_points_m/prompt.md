You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `cluster_points_m(points, max_distance_m)` where `points` is a list of `(lon, lat)` tuples in WGS84 and `max_distance_m` is a distance threshold in meters. Group the points into clusters such that two points belong to the same cluster whenever they are within `max_distance_m` meters of each other, either directly or through a chain of intermediate points (single-linkage; an isolated point forms its own cluster). Return a list of integer cluster labels, one per input point, numbered 0, 1, 2, ... in order of first appearance.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, and scikit-learn installed). Use only the standard library plus whichever of these packages you need.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.

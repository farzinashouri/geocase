You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `tag_points(points, polygons)` where `points` is a list of `(x, y)` tuples and `polygons` is a list of shapely `Polygon`s, all in the same planar coordinate system. The polygons may share boundaries but their interiors do not overlap. Return a list with exactly one entry per input point, in input order: the index of the polygon containing that point, where a point lying exactly on a polygon's boundary counts as contained, or `None` if the point is in no polygon. If a point lies on a boundary shared by several polygons, return the smallest such index.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, and scikit-learn installed). Use only the standard library plus whichever of these packages you need.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.

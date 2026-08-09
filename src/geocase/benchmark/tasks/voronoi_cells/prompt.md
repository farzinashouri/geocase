You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `voronoi_cells(points, bounds)` where `points` is a list of N distinct `(x, y)` tuples in a projected (planar) coordinate system and `bounds` is a rectangle `(minx, miny, maxx, maxy)` containing all the points. Return a list of N shapely `Polygon`s in which the i-th polygon is exactly the part of the rectangle consisting of the locations that are closer to the i-th input point than to any other input point.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, and scikit-learn installed). Use only the standard library plus whichever of these packages you need.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.

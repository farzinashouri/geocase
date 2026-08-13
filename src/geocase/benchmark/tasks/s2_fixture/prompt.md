You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `s2_fixture(path, size=32)` that writes a small synthetic Sentinel-2 L2A product to `path` as a GeoTIFF, suitable for use as a unit-test fixture. The product covers the four 10 m bands (B2, B3, B4, B8), in that band order, at processing baseline 04.00, and is `size` pixels square. It should be a faithful stand-in for a real granule: code that reads a genuine L2A product must be able to read this file and get the same kind of answer. The function returns `None`.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, and scikit-learn installed). Use only the standard library plus whichever of these packages you need.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.

You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `utm_epsg_for(lon, lat)` that takes a WGS84 longitude and latitude and returns, as an `int`, the EPSG code of the WGS 84 / UTM coordinate reference system for the grid zone containing that location, where grid zones are assigned as by the Military Grid Reference System, whose zone numbering includes the published grid exceptions. Codes are 326xx for the northern hemisphere and 327xx for the southern, with xx the zone number.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, and scikit-learn installed). Use only the standard library plus whichever of these packages you need.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.

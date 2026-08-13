"""Oracle for wkt_from_latlon (VEC-0002): the API hands over lat, lon; WKT is
x y, i.e. lon lat. Swapped axes parse fine and look plausible."""

from shapely import wkt as shapely_wkt


def build_checks(f):
    def control():
        got = shapely_wkt.loads(f(52.5, 13.4))
        return got.geom_type == "Point", f"parsed {got.wkt}"

    def axis_order():
        got = shapely_wkt.loads(f(52.5, 13.4))
        ok = abs(got.x - 13.4) < 1e-9 and abs(got.y - 52.5) < 1e-9
        return ok, (f"got x={got.x}, y={got.y}; expected x=13.4 (lon), y=52.5 (lat)")

    return [
        ("parses_as_point", "control", control),
        ("axis_order", "edge", axis_order),
    ]

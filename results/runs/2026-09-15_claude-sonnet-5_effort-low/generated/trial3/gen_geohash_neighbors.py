"""Compute geohash neighbor cells."""

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"

_NEIGHBORS = {
    "n": {
        "even": "p0r21436x8zb9dcf5h7kjnmqesgutwvy",
        "odd": "bc01fg45238967deuvhjyznpkmstqrwx",
    },
    "s": {
        "even": "14365h7k9dcfesgujnmqp0r2twvyx8zb",
        "odd": "238967debc01fg45kmstqrwxuvhjyznp",
    },
    "e": {
        "even": "bc01fg45238967deuvhjyznpkmstqrwx",
        "odd": "p0r21436x8zb9dcf5h7kjnmqesgutwvy",
    },
    "w": {
        "even": "238967debc01fg45kmstqrwxuvhjyznp",
        "odd": "14365h7k9dcfesgujnmqp0r2twvyx8zb",
    },
}

_BORDERS = {
    "n": {"even": "prxz", "odd": "bcfguvyz"},
    "s": {"even": "028b", "odd": "0145hjnp"},
    "e": {"even": "bcfguvyz", "odd": "prxz"},
    "w": {"even": "0145hjnp", "odd": "028b"},
}


def _adjacent(gh, direction):
    gh = gh.lower()
    last = gh[-1]
    parent = gh[:-1]
    kind = "even" if len(gh) % 2 == 0 else "odd"

    if last in _BORDERS[direction][kind] and parent:
        parent = _adjacent(parent, direction)

    return parent + _BASE32[_NEIGHBORS[direction][kind].index(last)]


def geohash_neighbors(gh):
    """Return the geohashes of the (up to) 8 cells surrounding gh."""
    n = _adjacent(gh, "n")
    s = _adjacent(gh, "s")

    results = []

    has_n = not gh.lower().startswith(("z", "b")) or True  # placeholder, replaced below
    results = []

    # Determine pole clipping: latitude bounds of the cell.
    # A cell touches the north pole if all-'z'-like top rows collapse; detect via
    # checking whether moving north changes latitude bits at all.
    n_valid = _crosses_pole(gh, "n") is False
    s_valid = _crosses_pole(gh, "s") is False

    if n_valid:
        results.append(n)
        results.append(_adjacent(n, "e"))
        results.append(_adjacent(n, "w"))
    if s_valid:
        results.append(s)
        results.append(_adjacent(s, "e"))
        results.append(_adjacent(s, "w"))

    results.append(_adjacent(gh, "e"))
    results.append(_adjacent(gh, "w"))

    return results


def _decode_lat_range(gh):
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    even = True
    for c in gh.lower():
        idx = _BASE32.index(c)
        for shift in (16, 8, 4, 2, 1):
            bit = 1 if idx & shift else 0
            if even:
                mid = (lon_range[0] + lon_range[1]) / 2
                if bit:
                    lon_range[0] = mid
                else:
                    lon_range[1] = mid
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                if bit:
                    lat_range[0] = mid
                else:
                    lat_range[1] = mid
            even = not even
    return lat_range


def _crosses_pole(gh, direction):
    lat_range = _decode_lat_range(gh)
    if direction == "n":
        return lat_range[1] >= 90.0
    return lat_range[0] <= -90.0
"""Oracle for geohash_neighbors (ALG-0021): cells touching the equator or the
prime meridian share no prefix with their neighbours across it. The oracle
encodes offset cell centres from first principles (bit interleaving), owing
nothing to lookup-table implementations."""

from geocase.benchmark._oracle_utils import geohash_encode, geohash_neighbors_oracle


def build_checks(f):
    def check_cell(gh):
        exp = geohash_neighbors_oracle(gh)
        got = set(f(gh))
        return got == exp, f"got {sorted(got)}, expected {sorted(exp)}"

    def control():
        return check_cell("u33d")  # interior cell, no border in any direction

    def corner():
        # The precision-4 cell just north-east of (lon=0, lat=0): its south,
        # west and south-west neighbours cross the equator / prime meridian.
        gh = geohash_encode(0.05, 0.05, 4)
        return check_cell(gh)

    return [
        ("interior_cell", "control", control),
        ("equator_meridian_corner", "edge", corner),
    ]

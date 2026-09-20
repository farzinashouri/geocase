def geohash_neighbors(gh):
    """Return the 8 geohash neighbors at the same precision.
    
    Cells at poles have fewer than 8 neighbors (top/bottom neighbors omitted).
    East-west neighbors wrap across the antimeridian.
    """
    if not gh:
        return []
    
    NEIGHBORS = {
        'right': {
            'even': "p0r21436x8zb9dcf5h7kjnmqesgutwvy",
            'odd': "bc01fg45238967deuvhjyznpkmstqrwx"
        },
        'left': {
            'even': "14365h7k9dcfesgujnmqp0r2twvyx8zb",
            'odd': "238967debc01fg45kmstqrwxuvhjyznp"
        },
        'top': {
            'even': "bc01fg45238967deuvhjyznpkmstqrwx",
            'odd': "p0r21436x8zb9dcf5h7kjnmqesgutwvy"
        },
        'bottom': {
            'even': "238967debc01fg45kmstqrwxuvhjyznp",
            'odd': "14365h7k9dcfesgujnmqp0r2twvyx8zb"
        }
    }
    
    BORDERS = {
        'right': {'even': "bcfguvyz", 'odd': "prxz"},
        'left': {'even': "0145hjnp", 'odd': "028b"},
        'top': {'even': "prxz", 'odd': "bcfguvyz"},
        'bottom': {'even': "028b", 'odd': "0145hjnp"}
    }
    
    BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    
    def get_neighbor(geohash, direction):
        if not geohash:
            return None
        
        last_char = geohash[-1]
        parent = geohash[:-1]
        parity = 'even' if len(geohash) % 2 == 0 else 'odd'
        
        if last_char in BORDERS[direction][parity]:
            parent = get_neighbor(parent, direction)
            if parent is None:
                return None
        
        return parent + NEIGHBORS[direction][parity][BASE32.index(last_char)]
    
    neighbors = []
    for direction in ['top', 'bottom', 'left', 'right']:
        neighbor = get_neighbor(gh, direction)
        if neighbor is not None:
            neighbors.append(neighbor)
    
    for d1, d2 in [('top', 'left'), ('top', 'right'), ('bottom', 'left'), ('bottom', 'right')]:
        n1 = get_neighbor(gh, d1)
        if n1 is not None:
            n2 = get_neighbor(n1, d2)
            if n2 is not None:
                neighbors.append(n2)
    
    return neighbors
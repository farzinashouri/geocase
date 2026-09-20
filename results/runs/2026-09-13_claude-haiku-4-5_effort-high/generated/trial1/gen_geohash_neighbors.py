def geohash_neighbors(gh):
    """
    Return the 8 neighboring geohashes at the same precision.
    East-west neighbors wrap across the antimeridian.
    Cells at the poles have fewer neighbors.
    """
    
    # Standard geohash lookup tables for neighbor transformation
    NEIGHBORS = {
        'right': {
            'even': "bc01fg45238967deuvhjyznpkmstqrwx",
            'odd': "p0r21436x8zb9dcf5h7kjnmqesgutwvy"
        },
        'left': {
            'even': "238967debc01fg45kmstqrwxuvhjyznp",
            'odd': "14365h7k9dcfesgujnmqp0r2twvyx8zb"
        },
        'top': {
            'even': "p0r21436x8zb9dcf5h7kjnmqesgutwvy",
            'odd': "bc01fg45238967deuvhjyznpkmstqrwx"
        },
        'bottom': {
            'even': "14365h7k9dcfesgujnmqp0r2twvyx8zb",
            'odd': "238967debc01fg45kmstqrwxuvhjyznp"
        }
    }
    
    BORDERS = {
        'right': {
            'even': "bcfguvyz",
            'odd': "prxz"
        },
        'left': {
            'even': "0145hjnp",
            'odd': "028b"
        },
        'top': {
            'even': "prxz",
            'odd': "bcfguvyz"
        },
        'bottom': {
            'even': "028b",
            'odd': "0145hjnp"
        }
    }
    
    BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    
    def get_neighbor(hash_str, direction):
        if not hash_str:
            return None
        
        last_char = hash_str[-1]
        parent = hash_str[:-1]
        parity = 'even' if len(hash_str) % 2 == 0 else 'odd'
        
        # If on border, transform parent recursively
        if last_char in BORDERS[direction][parity]:
            parent = get_neighbor(parent, direction)
            if parent is None:
                return None
        
        # Transform last character using lookup table
        idx = BASE32.index(last_char)
        neighbor_char = NEIGHBORS[direction][parity][idx]
        return parent + neighbor_char
    
    result = []
    
    # Cardinal neighbors
    for direction in ['right', 'left', 'top', 'bottom']:
        neighbor = get_neighbor(gh, direction)
        if neighbor:
            result.append(neighbor)
    
    # Diagonal neighbors (composition of two cardinal directions)
    diagonals = [
        ('top', 'right'),
        ('top', 'left'),
        ('bottom', 'right'),
        ('bottom', 'left')
    ]
    
    for d1, d2 in diagonals:
        n1 = get_neighbor(gh, d1)
        if n1:
            n2 = get_neighbor(n1, d2)
            if n2:
                result.append(n2)
    
    return result
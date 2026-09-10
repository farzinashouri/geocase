```python
def geohash_neighbors(gh):
    """
    Returns the geohashes of the 8 cells surrounding the given geohash.
    East-west neighbors wrap across the antimeridian.
    Cells beyond the poles do not exist and are omitted.
    """
    BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    
    NEIGHBORS = {
        'right': {'even': "p0r21436x8zb9dcf5h7kjnmqesgutwvy", 'odd': "bc01fg45238967deuvhjyznpkmstqrwx"},
        'left': {'even': "238967debc01fg45kmstqrwxuvhjyznp", 'odd': "p0r21436x8zb9dcf5h7kjnmqesgutwvy"},
        'top': {'even': "bc01fg45238967deuvhjyznpkmstqrwx", 'odd': "p0r21436x8zb9dcf5h7kjnmqesgutwvy"},
        'bottom': {'even': "14365h7k9dcfesgujnmqp0r2twvyx8zb", 'odd': "238967debc01fg45kmstqrwxuvhjyznp"}
    }
    
    BORDERS = {
        'right': {'even': "bcfguvyz", 'odd': "prxz"},
        'left': {'even': "0145hjnp", 'odd': "028b"},
        'top': {'even': "prxz", 'odd': "bcfguvyz"},
        'bottom': {'even': "028b", 'odd': "0145hjnp"}
    }
    
    def neighbor(geohash, direction):
        if not geohash:
            return None
        last_char = geohash[-1]
        parent = geohash[:-1]
        type_ = 'even' if len(geohash) % 2 == 0 else 'odd'
        
        if last_char in BORDERS[direction][type_] and parent:
            parent = neighbor(parent, direction)
        
        return None if parent is None else parent + BASE32[NEIGHBORS[direction][type_].index(last_char)]
    
    neighbors_list = []
    
    # Cardinal neighbors
    for direction in ['top', 'bottom', 'left', 'right']:
        n = neighbor(gh, direction)
        if n:
            neighbors_list.append(n)
    
    # Diagonal neighbors
    top = neighbor(gh, 'top')
    bottom = neighbor(gh, 'bottom')
    left = neighbor(gh, 'left')
    right = neighbor(gh, 'right')
    
    for horiz in [left, right]:
        if horiz:
            for vert_dir in ['top', 'bottom']:
                diag = neighbor(horiz, vert_dir)
                if diag:
                    neighbors_list.append(diag)
    
    return neighbors_list
```
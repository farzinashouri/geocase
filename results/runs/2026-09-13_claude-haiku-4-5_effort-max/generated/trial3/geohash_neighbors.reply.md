```python
def geohash_neighbors(gh):
    neighbors = {
        'even': {
            'n': 'p0r21436x8zb9dcf5h7kjnmqesgutwvy',
            's': '14365h7k9dcfesgujnmqp0r2twvyx8zb',
            'e': 'bc01fg45238967deuvhjyznpkmstqrwx',
            'w': '238967debc01fg45kmstqrwxuvhjyznp'
        },
        'odd': {
            'n': 'bc01fg45238967deuvhjyznpkmstqrwx',
            's': '238967debc01fg45kmstqrwxuvhjyznp',
            'e': 'p0r21436x8zb9dcf5h7kjnmqesgutwvy',
            'w': '14365h7k9dcfesgujnmqp0r2twvyx8zb'
        }
    }
    
    borders = {
        'even': {'n': 'prxz', 's': '028b', 'e': 'bcfguvyz', 'w': '0145hjnp'},
        'odd': {'n': 'bcfguvyz', 's': '0145hjnp', 'e': 'prxz', 'w': '028b'}
    }
    
    base32 = '0123456789bcdefghjkmnpqrstuvwxyz'
    
    def get_neighbor(gh, direction):
        if not gh:
            return None
        last = gh[-1]
        parent = gh[:-1]
        parity = 'even' if len(gh) % 2 == 0 else 'odd'
        
        if last in borders[parity][direction]:
            if not parent:
                return None
            parent = get_neighbor(parent, direction)
            if parent is None:
                return None
        
        idx = base32.index(last)
        return parent + neighbors[parity][direction][idx]
    
    result = set()
    
    for d in ['n', 's', 'e', 'w']:
        n = get_neighbor(gh, d)
        if n:
            result.add(n)
    
    for d1, d2 in [('n', 'e'), ('n', 'w'), ('s', 'e'), ('s', 'w')]:
        for d_first, d_second in [(d1, d2), (d2, d1)]:
            n = get_neighbor(gh, d_first)
            if n:
                n2 = get_neighbor(n, d_second)
                if n2:
                    result.add(n2)
    
    return list(result)
```
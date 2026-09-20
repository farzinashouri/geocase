def geohash_neighbors(gh):
    """Return the 8 geohashes of cells surrounding the given geohash.
    
    East-west neighbours wrap across the antimeridian. Cells beyond
    the poles are omitted, so polar cells have fewer than 8 neighbours.
    """
    BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    
    def decode(geohash):
        """Decode geohash to lat/lon bounds and dimensions."""
        lat_range = [-90.0, 90.0]
        lon_range = [-180.0, 180.0]
        is_lon = True
        
        for c in geohash:
            idx = BASE32.index(c)
            for mask in [16, 8, 4, 2, 1]:
                if is_lon:
                    mid = (lon_range[0] + lon_range[1]) / 2
                    if idx & mask:
                        lon_range[0] = mid
                    else:
                        lon_range[1] = mid
                else:
                    mid = (lat_range[0] + lat_range[1]) / 2
                    if idx & mask:
                        lat_range[0] = mid
                    else:
                        lat_range[1] = mid
                is_lon = not is_lon
        
        lat_center = (lat_range[0] + lat_range[1]) / 2
        lon_center = (lon_range[0] + lon_range[1]) / 2
        lat_height = lat_range[1] - lat_range[0]
        lon_width = lon_range[1] - lon_range[0]
        
        return lat_center, lon_center, lat_height, lon_width
    
    def encode(lat_center, lon_center, precision):
        """Encode lat/lon center to geohash."""
        lat_range = [-90.0, 90.0]
        lon_range = [-180.0, 180.0]
        geohash = []
        is_lon = True
        bits = 0
        ch = 0
        
        while len(geohash) < precision:
            if is_lon:
                mid = (lon_range[0] + lon_range[1]) / 2
                if lon_center > mid:
                    ch |= (1 << (4 - bits))
                    lon_range[0] = mid
                else:
                    lon_range[1] = mid
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                if lat_center > mid:
                    ch |= (1 << (4 - bits))
                    lat_range[0] = mid
                else:
                    lat_range[1] = mid
            
            is_lon = not is_lon
            bits += 1
            if bits == 5:
                geohash.append(BASE32[ch])
                bits = 0
                ch = 0
        
        return ''.join(geohash)
    
    lat_center, lon_center, lat_height, lon_width = decode(gh)
    precision = len(gh)
    neighbors = []
    
    for dlat in [-1, 0, 1]:
        for dlon in [-1, 0, 1]:
            if dlat == 0 and dlon == 0:
                continue
            
            new_lat = lat_center + dlat * lat_height
            new_lon = lon_center + dlon * lon_width
            
            # Wrap longitude across antimeridian
            new_lon = ((new_lon + 180) % 360) - 180
            
            # Skip if beyond poles
            if -90 <= new_lat <= 90:
                neighbors.append(encode(new_lat, new_lon, precision))
    
    return neighbors
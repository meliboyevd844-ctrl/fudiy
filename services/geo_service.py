import math
from typing import Tuple

def calculate_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) using Haversine formula.
    Returns distance in meters.
    """
    # Convert decimal degrees to radians
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Haversine formula
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    # Radius of Earth in meters
    r = 6371000.0
    return round(r * c, 2)


def is_within_radius(user_lat: float, user_lon: float, shop_lat: float, shop_lon: float, radius_meters: float = 50.0) -> Tuple[bool, float]:
    """
    Check if user's coordinates fall within the allowed shop radius.
    Returns (is_valid: bool, actual_distance: float)
    """
    dist = calculate_distance_meters(user_lat, user_lon, shop_lat, shop_lon)
    return (dist <= radius_meters), dist

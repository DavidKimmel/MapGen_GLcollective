"""
MapGen — Geocoding utilities.

Provides Nominatim geocoding with caching and rate limiting.
"""

import re
import time

from geopy.geocoders import Nominatim

from utils.cache import cache_get, cache_set, CacheError
from utils.logging import safe_print


def get_coordinates(city: str, country: str) -> tuple[float, float]:
    """Geocode a city/country pair to (lat, lon) using Nominatim.

    Uses caching to avoid redundant API calls.
    """
    coords_key = f"coords_{city.lower().replace(' ', '_')}_{country.lower().replace(' ', '_')}"
    cached = cache_get(coords_key)
    if cached is not None:
        safe_print(f"[OK] Using cached coordinates for {city}, {country}")
        return cached

    safe_print(f"  Geocoding '{city}, {country}'...")
    geolocator = Nominatim(user_agent="mapgen_poster", timeout=10)
    time.sleep(1)

    try:
        location = geolocator.geocode(f"{city}, {country}")
    except Exception as e:
        raise ValueError(f"Geocoding failed for {city}, {country}: {e}") from e

    if location:
        safe_print(f"[OK] Found: {location.address}")
        result = (location.latitude, location.longitude)
        try:
            cache_set(coords_key, result)
        except CacheError as e:
            safe_print(str(e))
        return result

    raise ValueError(f"Could not find coordinates for {city}, {country}")


def geocode_search(query: str, limit: int = 5) -> list[dict]:
    """Search for locations via Nominatim. Returns top results with details."""
    if not query or len(query) < 2:
        return []

    geolocator = Nominatim(user_agent="mapgen_poster", timeout=10)
    time.sleep(1)

    try:
        results = geolocator.geocode(query, exactly_one=False, limit=limit, addressdetails=True)
    except Exception:
        return []

    if not results:
        return []

    out = []
    for r in results:
        addr = r.raw.get("address", {})
        out.append({
            "display_name": r.address,
            "lat": float(r.latitude),
            "lon": float(r.longitude),
            "city": addr.get("city") or addr.get("town") or addr.get("village") or query,
            "country": addr.get("country", ""),
        })
    return out


def parse_location(location: str) -> tuple[float, float, object | None]:
    """Parse a location string into (lat, lon, geocode_result).

    Accepts:
      - "Chicago, IL" -> geocode to lat/lon
      - "41.8827,-87.6233" -> parse as lat/lon directly
    """
    latlon_match = re.match(
        r'^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$', location.strip()
    )
    if latlon_match:
        lat = float(latlon_match.group(1))
        lon = float(latlon_match.group(2))
        safe_print(f"  Parsed lat/lon: {lat}, {lon}")
        return lat, lon, None

    safe_print(f"  Geocoding '{location}'...")
    geolocator = Nominatim(user_agent="mapgen_poster", timeout=10)
    time.sleep(1)
    result = geolocator.geocode(location, addressdetails=True)
    if result is None:
        raise ValueError(f"Could not geocode location: {location}")

    safe_print(f"[OK] Found: {result.address}")
    return result.latitude, result.longitude, result


def extract_city_state(geocode_result) -> tuple[str | None, str | None]:
    """Extract city name and state/country from a Nominatim result."""
    if geocode_result is None:
        return None, None

    addr = geocode_result.raw.get("address", {})
    display = geocode_result.raw.get("display_name", "")
    first_part = display.split(",")[0].strip() if display else ""

    if first_part and not first_part[0].isdigit():
        city = first_part
    else:
        city = (
            addr.get("city")
            or addr.get("town")
            or addr.get("village")
            or addr.get("borough")
            or addr.get("suburb")
            or addr.get("county")
            or addr.get("municipality")
            or first_part
            or "Unknown"
        )

    country_code = addr.get("country_code", "").upper()
    if country_code == "US":
        state = addr.get("state", "")
    else:
        state = addr.get("country", "")

    return city, state

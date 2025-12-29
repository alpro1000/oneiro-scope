"""
GeoNames API resolver for geocoding with multilingual support.

Provides async geocoding using the official GeoNames API with:
- Support for Russian and Latin names
- Automatic transliteration fallback
- LRU caching to reduce API calls
- Language detection for smart query handling
- Fallback to built-in popular cities database
"""

import os
import asyncio
from functools import lru_cache
from typing import Dict, Optional
import logging

import httpx

logger = logging.getLogger(__name__)

# GeoNames API configuration
GEONAMES_USER = os.getenv("GEONAMES_USERNAME", "demo")  # 'demo' for testing only
GEONAMES_LANG = os.getenv("GEONAMES_LANG", "ru")
BASE_URL = "http://api.geonames.org/searchJSON"

# Built-in popular cities database (fallback when GeoNames API fails)
# Format: {"city_name_lower": {"name": "DisplayName", "country": "CountryName", "lat": 55.0, "lon": 37.0, "timezone": "Europe/Moscow"}}
# Expanded to include major Russian, Ukrainian, European, Asian, American cities for offline support
POPULAR_CITIES = {
    # Russia
    "москва": {"name": "Moscow", "country": "Russia", "lat": 55.75222, "lon": 37.61556, "timezone": "Europe/Moscow"},
    "moscow": {"name": "Moscow", "country": "Russia", "lat": 55.75222, "lon": 37.61556, "timezone": "Europe/Moscow"},
    "санкт-петербург": {"name": "Saint Petersburg", "country": "Russia", "lat": 59.93863, "lon": 30.31413, "timezone": "Europe/Moscow"},
    "saint petersburg": {"name": "Saint Petersburg", "country": "Russia", "lat": 59.93863, "lon": 30.31413, "timezone": "Europe/Moscow"},
    "st petersburg": {"name": "Saint Petersburg", "country": "Russia", "lat": 59.93863, "lon": 30.31413, "timezone": "Europe/Moscow"},
    "novosibirsk": {"name": "Novosibirsk", "country": "Russia", "lat": 55.0415, "lon": 82.9346, "timezone": "Asia/Novosibirsk"},
    "новосибирск": {"name": "Novosibirsk", "country": "Russia", "lat": 55.0415, "lon": 82.9346, "timezone": "Asia/Novosibirsk"},
    "екатеринбург": {"name": "Yekaterinburg", "country": "Russia", "lat": 56.8389, "lon": 60.6057, "timezone": "Asia/Yekaterinburg"},
    "yekaterinburg": {"name": "Yekaterinburg", "country": "Russia", "lat": 56.8389, "lon": 60.6057, "timezone": "Asia/Yekaterinburg"},
    "казань": {"name": "Kazan", "country": "Russia", "lat": 55.7894, "lon": 49.1204, "timezone": "Europe/Moscow"},
    "kazan": {"name": "Kazan", "country": "Russia", "lat": 55.7894, "lon": 49.1204, "timezone": "Europe/Moscow"},

    # Ukraine
    "киев": {"name": "Kyiv", "country": "Ukraine", "lat": 50.4501, "lon": 30.5234, "timezone": "Europe/Kyiv"},
    "kyiv": {"name": "Kyiv", "country": "Ukraine", "lat": 50.4501, "lon": 30.5234, "timezone": "Europe/Kyiv"},
    "kiev": {"name": "Kyiv", "country": "Ukraine", "lat": 50.4501, "lon": 30.5234, "timezone": "Europe/Kyiv"},
    "запорожье": {"name": "Zaporizhia", "country": "Ukraine", "lat": 47.8389, "lon": 35.1969, "timezone": "Europe/Kyiv"},
    "zaporizhia": {"name": "Zaporizhia", "country": "Ukraine", "lat": 47.8389, "lon": 35.1969, "timezone": "Europe/Kyiv"},
    "харків": {"name": "Kharkiv", "country": "Ukraine", "lat": 50.0038, "lon": 36.2304, "timezone": "Europe/Kyiv"},
    "kharkiv": {"name": "Kharkiv", "country": "Ukraine", "lat": 50.0038, "lon": 36.2304, "timezone": "Europe/Kyiv"},
    "львів": {"name": "Lviv", "country": "Ukraine", "lat": 49.8397, "lon": 24.0297, "timezone": "Europe/Kyiv"},
    "lviv": {"name": "Lviv", "country": "Ukraine", "lat": 49.8397, "lon": 24.0297, "timezone": "Europe/Kyiv"},
    "одеса": {"name": "Odesa", "country": "Ukraine", "lat": 46.4858, "lon": 30.7326, "timezone": "Europe/Kyiv"},
    "odesa": {"name": "Odesa", "country": "Ukraine", "lat": 46.4858, "lon": 30.7326, "timezone": "Europe/Kyiv"},

    # Europe
    "london": {"name": "London", "country": "United Kingdom", "lat": 51.5085, "lon": -0.1257, "timezone": "Europe/London"},
    "лондон": {"name": "London", "country": "United Kingdom", "lat": 51.5085, "lon": -0.1257, "timezone": "Europe/London"},
    "paris": {"name": "Paris", "country": "France", "lat": 48.8566, "lon": 2.3522, "timezone": "Europe/Paris"},
    "париж": {"name": "Paris", "country": "France", "lat": 48.8566, "lon": 2.3522, "timezone": "Europe/Paris"},
    "берлин": {"name": "Berlin", "country": "Germany", "lat": 52.5200, "lon": 13.4050, "timezone": "Europe/Berlin"},
    "berlin": {"name": "Berlin", "country": "Germany", "lat": 52.5200, "lon": 13.4050, "timezone": "Europe/Berlin"},
    "madrid": {"name": "Madrid", "country": "Spain", "lat": 40.4168, "lon": -3.7038, "timezone": "Europe/Madrid"},
    "rome": {"name": "Rome", "country": "Italy", "lat": 41.9028, "lon": 12.4964, "timezone": "Europe/Rome"},
    "roma": {"name": "Rome", "country": "Italy", "lat": 41.9028, "lon": 12.4964, "timezone": "Europe/Rome"},
    "amsterdam": {"name": "Amsterdam", "country": "Netherlands", "lat": 52.3676, "lon": 4.9041, "timezone": "Europe/Amsterdam"},
    "barcelona": {"name": "Barcelona", "country": "Spain", "lat": 41.3874, "lon": 2.1686, "timezone": "Europe/Madrid"},
    "vienna": {"name": "Vienna", "country": "Austria", "lat": 48.2082, "lon": 16.3738, "timezone": "Europe/Vienna"},
    "wien": {"name": "Vienna", "country": "Austria", "lat": 48.2082, "lon": 16.3738, "timezone": "Europe/Vienna"},
    "prague": {"name": "Prague", "country": "Czech Republic", "lat": 50.0755, "lon": 14.4378, "timezone": "Europe/Prague"},

    # Asia
    "tokyo": {"name": "Tokyo", "country": "Japan", "lat": 35.6762, "lon": 139.6503, "timezone": "Asia/Tokyo"},
    "bangkok": {"name": "Bangkok", "country": "Thailand", "lat": 13.7563, "lon": 100.5018, "timezone": "Asia/Bangkok"},
    "singapore": {"name": "Singapore", "country": "Singapore", "lat": 1.3521, "lon": 103.8198, "timezone": "Asia/Singapore"},
    "hong kong": {"name": "Hong Kong", "country": "Hong Kong", "lat": 22.2793, "lon": 114.1694, "timezone": "Asia/Hong_Kong"},
    "dubai": {"name": "Dubai", "country": "United Arab Emirates", "lat": 25.2048, "lon": 55.2708, "timezone": "Asia/Dubai"},
    "mumbai": {"name": "Mumbai", "country": "India", "lat": 19.0760, "lon": 72.8777, "timezone": "Asia/Kolkata"},
    "delhi": {"name": "New Delhi", "country": "India", "lat": 28.6139, "lon": 77.2090, "timezone": "Asia/Kolkata"},

    # Americas
    "new york": {"name": "New York", "country": "United States", "lat": 40.7128, "lon": -74.0060, "timezone": "America/New_York"},
    "ny": {"name": "New York", "country": "United States", "lat": 40.7128, "lon": -74.0060, "timezone": "America/New_York"},
    "los angeles": {"name": "Los Angeles", "country": "United States", "lat": 34.0522, "lon": -118.2437, "timezone": "America/Los_Angeles"},
    "la": {"name": "Los Angeles", "country": "United States", "lat": 34.0522, "lon": -118.2437, "timezone": "America/Los_Angeles"},
    "chicago": {"name": "Chicago", "country": "United States", "lat": 41.8781, "lon": -87.6298, "timezone": "America/Chicago"},
    "toronto": {"name": "Toronto", "country": "Canada", "lat": 43.6532, "lon": -79.3832, "timezone": "America/Toronto"},
    "mexico city": {"name": "Mexico City", "country": "Mexico", "lat": 19.4326, "lon": -99.1332, "timezone": "America/Mexico_City"},
    "buenos aires": {"name": "Buenos Aires", "country": "Argentina", "lat": -34.6037, "lon": -58.3816, "timezone": "America/Argentina/Buenos_Aires"},
    "sao paulo": {"name": "São Paulo", "country": "Brazil", "lat": -23.5505, "lon": -46.6333, "timezone": "America/Sao_Paulo"},

    # Oceania
    "sydney": {"name": "Sydney", "country": "Australia", "lat": -33.8688, "lon": 151.2093, "timezone": "Australia/Sydney"},
    "melbourne": {"name": "Melbourne", "country": "Australia", "lat": -37.8136, "lon": 144.9631, "timezone": "Australia/Melbourne"},
    "auckland": {"name": "Auckland", "country": "New Zealand", "lat": -37.0082, "lon": 174.7850, "timezone": "Pacific/Auckland"},
}

# HTTP client with connection pooling
_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """Get or create async HTTP client."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


async def close_http_client():
    """Close HTTP client connection pool."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


def detect_language(text: str) -> str:
    """
    Detect language of text.

    Simple heuristic: if text contains Cyrillic characters, it's Russian.
    Otherwise, assume Latin/English.
    """
    if any('\u0400' <= char <= '\u04FF' for char in text):
        return "ru"
    return "en"


def transliterate_russian(text: str) -> str:
    """
    Transliterate Russian text to Latin.

    Simple mapping for common characters. For production, consider using
    the 'transliterate' library for more accurate conversion.
    """
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch',
        'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }

    result = []
    for char in text:
        result.append(translit_map.get(char, char))
    return ''.join(result)


@lru_cache(maxsize=512)
def _cache_key(place_name: str) -> str:
    """Generate cache key for place name."""
    return place_name.lower().strip()


# In-memory cache for resolved locations
_location_cache: Dict[str, Dict] = {}


async def geonames_lookup(place_name: str) -> Dict:
    """
    Lookup location using GeoNames API with multilingual support.

    Tries GeoNames API first, then transliteration fallback (for Russian),
    then falls back to built-in popular cities database.

    Args:
        place_name: City or place name in Russian or Latin

    Returns:
        Dictionary with location data:
        {
            "input": "Москва",
            "resolved_name": "Moscow",
            "country": "Russia",
            "lat": 55.75222,
            "lon": 37.61556,
            "geonameId": 524901 or None (if from built-in database)
        }

    Raises:
        ValueError: If place not found in all sources
        httpx.HTTPError: If API request fails
    """
    # Check cache first
    cache_key = _cache_key(place_name)
    if cache_key in _location_cache:
        logger.debug(f"GeoNames cache hit: {place_name}")
        return _location_cache[cache_key]

    client = get_http_client()
    query = place_name.strip()

    # Warn if using demo account
    if GEONAMES_USER == "demo":
        logger.warning(f"[GeoNames] ⚠️  Using DEMO account - API access limited. Set GEONAMES_USERNAME env var for production!")

    # Try original query first
    params = {
        "q": query,
        "maxRows": 10,  # Get top 10 results to choose best match
        "lang": GEONAMES_LANG,
        "username": GEONAMES_USER,
        "featureClass": "P",  # Populated places (cities, towns, villages)
        "isNameRequired": "true",  # Only exact name matches
        "style": "FULL",  # Include timezone info in response
    }

    logger.info(f"[GeoNames] Starting lookup for: '{place_name}'")
    logger.debug(f"[GeoNames] API params: {params}")
    logger.debug(f"[GeoNames] Using provider: {GEONAMES_USER}, language: {GEONAMES_LANG}")

    data = {}
    try:
        response = await client.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        logger.debug(f"[GeoNames] API response status: {response.status_code}")
        logger.debug(f"[GeoNames] Total results found: {len(data.get('geonames', []))}")
        if data.get("geonames"):
            logger.debug(f"[GeoNames] Top result: {data['geonames'][0].get('name')} ({data['geonames'][0].get('countryName')})")
    except Exception as api_error:
        logger.warning(f"[GeoNames] API request failed: {type(api_error).__name__}: {api_error}")
        data = {}

    # If not found and text is Russian, try transliteration
    if not data.get("geonames"):
        lang = detect_language(place_name)
        logger.info(f"[GeoNames] No results for '{place_name}', detected language: {lang}")

        if lang == "ru":
            translit_query = transliterate_russian(place_name)
            logger.info(f"[GeoNames] Trying transliteration fallback: '{place_name}' → '{translit_query}'")
            params["q"] = translit_query
            try:
                response = await client.get(BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
                logger.debug(f"[GeoNames] Transliterated response: {data}")
            except Exception as api_error:
                logger.warning(f"[GeoNames] Transliteration API request failed: {type(api_error).__name__}: {api_error}")
                data = {}

    # Check if we got results
    if not data.get("geonames"):
        error_msg = f"Place not found: {place_name}"
        logger.warning(f"[GeoNames] ERROR: {error_msg}")
        logger.warning(f"[GeoNames] Total results received: {len(data.get('geonames', []))}")

        # Try fallback to built-in popular cities database
        logger.info(f"[GeoNames] Trying fallback to popular cities database...")
        city_key = query.lower().strip()
        if city_key in POPULAR_CITIES:
            city_data = POPULAR_CITIES[city_key]
            result = {
                "input": place_name,
                "resolved_name": city_data["name"],
                "country": city_data["country"],
                "lat": city_data["lat"],
                "lon": city_data["lon"],
                "geonameId": None,  # No GeoNames ID for built-in database
                "timezone": city_data["timezone"],
            }
            # Cache successful result
            _location_cache[cache_key] = result
            logger.info(f"[GeoNames] ✓ FALLBACK SUCCESS: '{place_name}' → '{result['resolved_name']}' ({result['country']})")
            logger.debug(f"[GeoNames] Using built-in popular cities database")
            return result

        logger.error(f"[GeoNames] ✗ Fallback also failed - city '{place_name}' not found in built-in database")
        raise ValueError(error_msg)

    place = data["geonames"][0]
    result = {
        "input": place_name,
        "resolved_name": place.get("name", ""),
        "country": place.get("countryName", ""),
        "lat": float(place["lat"]),
        "lon": float(place["lng"]),
        "geonameId": place.get("geonameId"),
        "timezone": place.get("timezone", {}).get("timeZoneId") if "timezone" in place else None,
    }

    # Cache successful result
    _location_cache[cache_key] = result
    logger.info(f"[GeoNames] ✓ SUCCESS: '{place_name}' → '{result['resolved_name']}' ({result['country']})")
    logger.debug(f"[GeoNames] Coordinates: {result['lat']}, {result['lon']}, TZ: {result['timezone']}")

    return result


async def geonames_lookup_batch(place_names: list[str]) -> list[Dict]:
    """
    Lookup multiple locations concurrently.

    Args:
        place_names: List of city/place names

    Returns:
        List of location dictionaries (same format as geonames_lookup)
    """
    tasks = [geonames_lookup(name) for name in place_names]
    return await asyncio.gather(*tasks, return_exceptions=True)


def clear_cache():
    """Clear the location cache."""
    global _location_cache
    _location_cache.clear()
    logger.info("GeoNames cache cleared")


async def geonames_search_cities(query: str, max_results: int = 10) -> list[Dict]:
    """
    Search for cities by name for autocomplete.

    Returns a list of cities with their details for display in autocomplete UI.

    Args:
        query: City name to search
        max_results: Maximum number of results to return

    Returns:
        List of city dictionaries with keys:
        - name: City name
        - country: Country name
        - admin_name: Admin division (state/region)
        - lat: Latitude
        - lon: Longitude
        - display: Formatted display string
        - geoname_id: GeoNames ID (optional)

    Raises:
        ValueError: If query is too short or invalid
    """
    if not query or len(query.strip()) < 2:
        raise ValueError("Query must be at least 2 characters")

    client = get_http_client()
    search_query = query.strip()

    # Warn if using demo account
    if GEONAMES_USER == "demo":
        logger.warning(f"[GeoNames Search] ⚠️  Using DEMO account - limited API access")

    params = {
        "q": search_query,
        "maxRows": max_results,
        "lang": GEONAMES_LANG,
        "username": GEONAMES_USER,
        "featureClass": "P",  # Populated places
        "orderby": "population",  # Sort by population (largest first)
        "style": "FULL",
    }

    logger.info(f"[GeoNames Search] Searching for cities: '{query}'")
    logger.debug(f"[GeoNames Search] API params: {params}")

    results = []
    data = {}

    try:
        response = await client.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        logger.debug(f"[GeoNames Search] Got {len(data.get('geonames', []))} results")
    except Exception as api_error:
        logger.warning(f"[GeoNames Search] API request failed: {type(api_error).__name__}: {api_error}")
        data = {}

    # If not found and query is Russian, try transliteration
    if not data.get("geonames"):
        lang = detect_language(query)
        if lang == "ru":
            translit_query = transliterate_russian(query)
            logger.info(f"[GeoNames Search] Trying transliteration: '{query}' → '{translit_query}'")
            params["q"] = translit_query
            try:
                response = await client.get(BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
                logger.debug(f"[GeoNames Search] Transliterated search: {len(data.get('geonames', []))} results")
            except Exception as api_error:
                logger.warning(f"[GeoNames Search] Transliteration failed: {api_error}")
                data = {}

    # If still no results from API, try popular cities database
    if not data.get("geonames"):
        logger.info(f"[GeoNames Search] No API results, searching popular cities database...")
        query_lower = search_query.lower()

        # Search in popular cities (case-insensitive prefix match)
        matching_cities = []
        for city_key, city_data in POPULAR_CITIES.items():
            if city_key.startswith(query_lower) or query_lower in city_key:
                matching_cities.append({
                    "name": city_data["name"],
                    "country": city_data["country"],
                    "admin_name": "",
                    "lat": city_data["lat"],
                    "lon": city_data["lon"],
                    "display": f"{city_data['name']}, {city_data['country']}",
                    "geoname_id": None,
                })

        # Sort by relevance (starts with query first)
        matching_cities.sort(key=lambda c: (
            not c["name"].lower().startswith(query_lower),
            c["name"]
        ))

        results = matching_cities[:max_results]
        logger.info(f"[GeoNames Search] Found {len(results)} matches in popular cities database")
        return results

    # Parse GeoNames API results
    for place in data.get("geonames", [])[:max_results]:
        admin_name = place.get("adminName1", "")
        display_parts = [place.get("name", "")]
        if admin_name:
            display_parts.append(admin_name)
        display_parts.append(place.get("countryName", ""))

        results.append({
            "name": place.get("name", ""),
            "country": place.get("countryName", ""),
            "admin_name": admin_name,
            "lat": float(place["lat"]),
            "lon": float(place["lng"]),
            "display": ", ".join(display_parts),
            "geoname_id": place.get("geonameId"),
        })

    logger.info(f"[GeoNames Search] ✓ Returning {len(results)} cities for '{query}'")
    return results

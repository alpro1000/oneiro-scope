"""
GeoNames API resolver for geocoding with multilingual support.

Provides async geocoding using the official GeoNames API with:
- Support for Russian and Latin names
- Automatic transliteration fallback
- LRU caching to reduce API calls
- Language detection for smart query handling
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
            "geonameId": 524901
        }

    Raises:
        ValueError: If place not found
        httpx.HTTPError: If API request fails
    """
    # Check cache first
    cache_key = _cache_key(place_name)
    if cache_key in _location_cache:
        logger.debug(f"GeoNames cache hit: {place_name}")
        return _location_cache[cache_key]

    client = get_http_client()
    query = place_name.strip()

    # Try original query first
    params = {
        "q": query,
        "maxRows": 1,
        "lang": GEONAMES_LANG,
        "username": GEONAMES_USER,
        "featureClass": "P",  # Populated places (cities, towns)
    }

    logger.info(f"GeoNames API query: {query} (lang={GEONAMES_LANG})")
    response = await client.get(BASE_URL, params=params)
    response.raise_for_status()
    data = response.json()

    # If not found and text is Russian, try transliteration
    if not data.get("geonames"):
        lang = detect_language(place_name)
        if lang == "ru":
            translit_query = transliterate_russian(place_name)
            logger.info(f"GeoNames fallback with transliteration: {translit_query}")
            params["q"] = translit_query
            response = await client.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

    # Check if we got results
    if not data.get("geonames"):
        error_msg = f"Place not found: {place_name}"
        logger.warning(error_msg)
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
    logger.info(f"GeoNames resolved: {place_name} → {result['resolved_name']}, {result['country']}")

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

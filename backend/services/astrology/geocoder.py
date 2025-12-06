"""Geocoding service for birth place resolution."""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class GeoLocation:
    """Geocoded location with coordinates and timezone."""
    name: str
    latitude: float
    longitude: float
    timezone: str
    country: Optional[str] = None
    admin_area: Optional[str] = None  # State/Region


class Geocoder:
    """
    Geocoding service for resolving place names to coordinates.

    Uses multiple providers with fallback:
    1. Nominatim (OpenStreetMap) - free, rate limited
    2. Google Geocoding API - paid, more accurate

    Also determines timezone from coordinates.
    """

    def __init__(
        self,
        google_api_key: Optional[str] = None,
        use_cache: bool = True,
    ):
        self.google_api_key = google_api_key
        self.use_cache = use_cache
        self._cache: dict[str, GeoLocation] = {}

        # Try to import geopy
        try:
            from geopy.geocoders import Nominatim
            self._nominatim = Nominatim(
                user_agent="oneiroscope-astrology/1.0",
                timeout=10,
            )
        except ImportError:
            logger.warning("geopy not installed. Geocoding will use fallback.")
            self._nominatim = None

        # Try to import timezonefinder
        try:
            from timezonefinder import TimezoneFinder
            self._tzfinder = TimezoneFinder()
        except ImportError:
            logger.warning("timezonefinder not installed. Using UTC as fallback.")
            self._tzfinder = None

    async def geocode(self, place: str) -> Optional[GeoLocation]:
        """
        Geocode a place name to coordinates.

        Args:
            place: Place name (e.g., "Moscow, Russia")

        Returns:
            GeoLocation with coordinates and timezone, or None if not found
        """
        # Check cache
        cache_key = place.lower().strip()
        if self.use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        location = await self._geocode_nominatim(place)

        if location and self.use_cache:
            self._cache[cache_key] = location

        return location

    async def _geocode_nominatim(self, place: str) -> Optional[GeoLocation]:
        """Geocode using Nominatim (OpenStreetMap)."""
        if self._nominatim is None:
            return self._fallback_geocode(place)

        try:
            # geopy is sync, so we run it directly
            # In production, consider using asyncio.to_thread()
            result = self._nominatim.geocode(
                place,
                addressdetails=True,
                language="en",
            )

            if not result:
                logger.warning(f"Nominatim: Place not found: {place}")
                return self._fallback_geocode(place)

            # Get timezone
            timezone = self._get_timezone(result.latitude, result.longitude)

            # Extract address components
            address = result.raw.get("address", {})
            country = address.get("country")
            admin_area = address.get("state") or address.get("region")

            return GeoLocation(
                name=result.address,
                latitude=result.latitude,
                longitude=result.longitude,
                timezone=timezone,
                country=country,
                admin_area=admin_area,
            )

        except Exception as e:
            logger.error(f"Nominatim geocoding error: {e}")
            return self._fallback_geocode(place)

    def _get_timezone(self, lat: float, lon: float) -> str:
        """Get timezone from coordinates."""
        if self._tzfinder:
            try:
                tz = self._tzfinder.timezone_at(lat=lat, lng=lon)
                if tz:
                    return tz
            except Exception as e:
                logger.warning(f"Timezone lookup failed: {e}")

        # Fallback: estimate timezone from longitude
        offset_hours = round(lon / 15)
        if offset_hours >= 0:
            return f"Etc/GMT-{offset_hours}"
        else:
            return f"Etc/GMT+{abs(offset_hours)}"

    def _fallback_geocode(self, place: str) -> Optional[GeoLocation]:
        """
        Fallback geocoding using a small built-in database.
        Only covers major cities.
        """
        # Common cities database
        cities = {
            "moscow": GeoLocation(
                name="Moscow, Russia",
                latitude=55.7558,
                longitude=37.6173,
                timezone="Europe/Moscow",
                country="Russia",
            ),
            "saint petersburg": GeoLocation(
                name="Saint Petersburg, Russia",
                latitude=59.9343,
                longitude=30.3351,
                timezone="Europe/Moscow",
                country="Russia",
            ),
            "st. petersburg": GeoLocation(
                name="Saint Petersburg, Russia",
                latitude=59.9343,
                longitude=30.3351,
                timezone="Europe/Moscow",
                country="Russia",
            ),
            "new york": GeoLocation(
                name="New York, USA",
                latitude=40.7128,
                longitude=-74.0060,
                timezone="America/New_York",
                country="USA",
            ),
            "los angeles": GeoLocation(
                name="Los Angeles, USA",
                latitude=34.0522,
                longitude=-118.2437,
                timezone="America/Los_Angeles",
                country="USA",
            ),
            "london": GeoLocation(
                name="London, UK",
                latitude=51.5074,
                longitude=-0.1278,
                timezone="Europe/London",
                country="UK",
            ),
            "paris": GeoLocation(
                name="Paris, France",
                latitude=48.8566,
                longitude=2.3522,
                timezone="Europe/Paris",
                country="France",
            ),
            "berlin": GeoLocation(
                name="Berlin, Germany",
                latitude=52.5200,
                longitude=13.4050,
                timezone="Europe/Berlin",
                country="Germany",
            ),
            "tokyo": GeoLocation(
                name="Tokyo, Japan",
                latitude=35.6762,
                longitude=139.6503,
                timezone="Asia/Tokyo",
                country="Japan",
            ),
            "beijing": GeoLocation(
                name="Beijing, China",
                latitude=39.9042,
                longitude=116.4074,
                timezone="Asia/Shanghai",
                country="China",
            ),
            "dubai": GeoLocation(
                name="Dubai, UAE",
                latitude=25.2048,
                longitude=55.2708,
                timezone="Asia/Dubai",
                country="UAE",
            ),
            "sydney": GeoLocation(
                name="Sydney, Australia",
                latitude=-33.8688,
                longitude=151.2093,
                timezone="Australia/Sydney",
                country="Australia",
            ),
            "kyiv": GeoLocation(
                name="Kyiv, Ukraine",
                latitude=50.4501,
                longitude=30.5234,
                timezone="Europe/Kiev",
                country="Ukraine",
            ),
            "minsk": GeoLocation(
                name="Minsk, Belarus",
                latitude=53.9006,
                longitude=27.5590,
                timezone="Europe/Minsk",
                country="Belarus",
            ),
            "almaty": GeoLocation(
                name="Almaty, Kazakhstan",
                latitude=43.2220,
                longitude=76.8512,
                timezone="Asia/Almaty",
                country="Kazakhstan",
            ),
        }

        # Normalize search
        search = place.lower().strip()
        for city, location in cities.items():
            if city in search:
                return location

        logger.warning(f"Fallback geocode: City not found in database: {place}")
        return None

    def clear_cache(self):
        """Clear geocoding cache."""
        self._cache.clear()

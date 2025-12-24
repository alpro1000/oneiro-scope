"""Strict geocoding without heuristic fallbacks."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from timezonefinder import TimezoneFinder

from backend.utils.geonames_resolver import geonames_lookup

logger = logging.getLogger(__name__)


class GeocodingError(Exception):
    """Raised when strict geocoding requirements are not met."""


@dataclass
class GeoLocation:
    """Geocoded location with provenance data."""

    name: str
    latitude: float
    longitude: float
    timezone: str
    provider: str
    query: str
    raw_response_id: str
    timestamp: datetime
    country: Optional[str] = None
    admin_area: Optional[str] = None


class Geocoder:
    """Strict geocoder that refuses to guess coordinates or timezone."""

    def __init__(self, provider: Optional[str] = None, username: Optional[str] = None):
        self.provider = provider or "geonames"
        self.username = username
        self.tzfinder = TimezoneFinder()

    async def geocode(self, query: str) -> GeoLocation:
        """
        Geocode a place name using GeoNames API.

        Args:
            query: City or place name (supports Russian and Latin)

        Returns:
            GeoLocation with coordinates, timezone, and provenance

        Raises:
            GeocodingError: If place not found or geocoding fails
        """
        logger.info(f"[Geocoder] Starting geocoding for: '{query}'")

        if not query or not query.strip():
            logger.error(f"[Geocoder] Query is empty or invalid")
            raise GeocodingError("PLACE_QUERY_REQUIRED")

        try:
            # Use GeoNames API for geocoding
            logger.debug(f"[Geocoder] Calling geonames_lookup...")
            result = await geonames_lookup(query)
            logger.debug(f"[Geocoder] geonames_lookup returned: {result}")

            # Get timezone: prefer GeoNames response, fallback to TimezoneFinder
            timezone_name = result.get("timezone")
            logger.debug(f"[Geocoder] GeoNames timezone: {timezone_name}")

            if not timezone_name:
                logger.info(f"[Geocoder] Timezone not in response, using TimezoneFinder...")
                timezone_name = self._timezone_for(result["lat"], result["lon"])
                logger.debug(f"[Geocoder] TimezoneFinder returned: {timezone_name}")

            # Create response hash for provenance
            payload = json.dumps(result, sort_keys=True).encode("utf-8")
            raw_response_id = hashlib.sha256(payload).hexdigest()

            geo_location = GeoLocation(
                name=result["resolved_name"],
                latitude=result["lat"],
                longitude=result["lon"],
                timezone=timezone_name,
                provider="geonames",
                query=query,
                raw_response_id=raw_response_id,
                timestamp=datetime.now(tz=timezone.utc),
                country=result.get("country"),
                admin_area=None,  # GeoNames basic API doesn't provide admin area
            )

            logger.info(f"[Geocoder] ✓ SUCCESS: Geocoded '{query}' to {geo_location.name}, {geo_location.country}")
            logger.debug(f"[Geocoder] Location: {geo_location.latitude}, {geo_location.longitude}, TZ: {geo_location.timezone}")

            return geo_location

        except ValueError as exc:
            # GeoNames raised "Place not found"
            logger.warning(f"[Geocoder] ✗ FAILED: Place not found for '{query}': {exc}")
            raise GeocodingError("PLACE_NOT_FOUND") from exc
        except Exception as exc:
            logger.error(f"[Geocoder] ✗ CRITICAL ERROR: Geocoding error for '{query}': {type(exc).__name__}: {exc}", exc_info=True)
            raise GeocodingError("GEOCODER_ERROR") from exc

    def _timezone_for(self, lat: float, lon: float) -> str:
        tz = self.tzfinder.timezone_at(lat=lat, lng=lon)
        if tz is None:
            raise GeocodingError("TIMEZONE_NOT_FOUND")
        return tz

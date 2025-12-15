"""Strict geocoding without heuristic fallbacks."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from timezonefinder import TimezoneFinder

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
        self.provider = provider or "nominatim"
        self.username = username
        self.tzfinder = TimezoneFinder()
        self._nominatim = None
        self._load_provider()

    def _load_provider(self) -> None:
        if self.provider == "nominatim":
            try:
                from geopy.geocoders import Nominatim

                self._nominatim = Nominatim(user_agent="oneiro-scope/astrology", timeout=10)
            except Exception as exc:  # pragma: no cover - library level
                logger.error("Failed to initialize Nominatim: %s", exc)
                self._nominatim = None
        else:
            self._nominatim = None

    def geocode(self, query: str) -> GeoLocation:
        if not query or not query.strip():
            raise GeocodingError("PLACE_QUERY_REQUIRED")

        if self._nominatim is None:
            raise GeocodingError("GEOCODER_NOT_AVAILABLE")

        result = self._nominatim.geocode(query, addressdetails=True, language="en")
        if result is None:
            raise GeocodingError("PLACE_NOT_FOUND")

        timezone_name = self._timezone_for(result.latitude, result.longitude)
        address = result.raw.get("address", {})
        payload = json.dumps(result.raw, sort_keys=True).encode("utf-8")
        raw_response_id = hashlib.sha256(payload).hexdigest()

        return GeoLocation(
            name=result.address,
            latitude=float(result.latitude),
            longitude=float(result.longitude),
            timezone=timezone_name,
            provider=self.provider,
            query=query,
            raw_response_id=raw_response_id,
            timestamp=datetime.now(tz=timezone.utc),
            country=address.get("country"),
            admin_area=address.get("state") or address.get("region"),
        )

    def _timezone_for(self, lat: float, lon: float) -> str:
        tz = self.tzfinder.timezone_at(lat=lat, lng=lon)
        if tz is None:
            raise GeocodingError("TIMEZONE_NOT_FOUND")
        return tz

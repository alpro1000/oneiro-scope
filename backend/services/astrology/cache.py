"""Caching service for astrology calculations."""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Any

logger = logging.getLogger(__name__)


class ChartCache:
    """
    Cache for natal charts and horoscopes.

    Supports:
    - In-memory cache (default)
    - Redis cache (if configured)

    Cache keys:
    - natal:{birth_date}:{birth_time}:{lat}:{lon} → natal chart
    - horoscope:{chart_hash}:{period}:{date} → horoscope
    - transit:{date}:{lat}:{lon} → current transits
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 3600,  # 1 hour
        natal_chart_ttl: int = 86400 * 30,  # 30 days (natal charts don't change)
        horoscope_ttl: int = 3600,  # 1 hour
    ):
        """
        Initialize cache.

        Args:
            redis_url: Redis connection URL (optional)
            default_ttl: Default TTL in seconds
            natal_chart_ttl: TTL for natal charts
            horoscope_ttl: TTL for horoscopes
        """
        self.default_ttl = default_ttl
        self.natal_chart_ttl = natal_chart_ttl
        self.horoscope_ttl = horoscope_ttl

        # In-memory cache fallback
        self._memory_cache: dict[str, tuple[Any, datetime]] = {}

        # Redis client
        self._redis = None
        if redis_url:
            try:
                import redis
                self._redis = redis.from_url(redis_url)
                self._redis.ping()
                logger.info("Redis cache connected")
            except Exception as e:
                logger.warning(f"Redis unavailable, using memory cache: {e}")

    def _generate_key(self, prefix: str, *args) -> str:
        """Generate cache key from prefix and arguments."""
        key_parts = [str(arg) for arg in args]
        key_data = ":".join(key_parts)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
        return f"astro:{prefix}:{key_hash}"

    async def get_natal_chart(
        self,
        birth_date: str,
        birth_time: Optional[str],
        lat: float,
        lon: float,
    ) -> Optional[dict]:
        """Get cached natal chart."""
        key = self._generate_key("natal", birth_date, birth_time or "noon", lat, lon)
        return await self._get(key)

    async def set_natal_chart(
        self,
        birth_date: str,
        birth_time: Optional[str],
        lat: float,
        lon: float,
        data: dict,
    ) -> None:
        """Cache natal chart."""
        key = self._generate_key("natal", birth_date, birth_time or "noon", lat, lon)
        await self._set(key, data, self.natal_chart_ttl)

    async def get_horoscope(
        self,
        chart_hash: str,
        period: str,
        date: str,
    ) -> Optional[dict]:
        """Get cached horoscope."""
        key = self._generate_key("horoscope", chart_hash, period, date)
        return await self._get(key)

    async def set_horoscope(
        self,
        chart_hash: str,
        period: str,
        date: str,
        data: dict,
    ) -> None:
        """Cache horoscope."""
        key = self._generate_key("horoscope", chart_hash, period, date)
        await self._set(key, data, self.horoscope_ttl)

    async def get_transits(self, date: str) -> Optional[dict]:
        """Get cached transits for a date."""
        key = self._generate_key("transits", date)
        return await self._get(key)

    async def set_transits(self, date: str, data: dict) -> None:
        """Cache transits."""
        key = self._generate_key("transits", date)
        # Transits valid for 1 hour
        await self._set(key, data, 3600)

    async def get_geocoding(self, place: str) -> Optional[dict]:
        """Get cached geocoding result."""
        key = self._generate_key("geo", place.lower().strip())
        return await self._get(key)

    async def set_geocoding(self, place: str, data: dict) -> None:
        """Cache geocoding result (long TTL - locations don't change)."""
        key = self._generate_key("geo", place.lower().strip())
        await self._set(key, data, 86400 * 365)  # 1 year

    async def _get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if self._redis:
            try:
                data = self._redis.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.error(f"Redis get error: {e}")

        # Fallback to memory cache
        if key in self._memory_cache:
            value, expires_at = self._memory_cache[key]
            if datetime.utcnow() < expires_at:
                return value
            else:
                del self._memory_cache[key]

        return None

    async def _set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in cache."""
        if self._redis:
            try:
                self._redis.setex(key, ttl, json.dumps(value, default=str))
                return
            except Exception as e:
                logger.error(f"Redis set error: {e}")

        # Fallback to memory cache
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        self._memory_cache[key] = (value, expires_at)

        # Clean old entries periodically
        if len(self._memory_cache) > 1000:
            self._cleanup_memory_cache()

    def _cleanup_memory_cache(self) -> None:
        """Remove expired entries from memory cache."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, (_, expires_at) in self._memory_cache.items()
            if now >= expires_at
        ]
        for key in expired_keys:
            del self._memory_cache[key]

    def generate_chart_hash(self, natal_chart: dict) -> str:
        """Generate unique hash for natal chart (for horoscope caching)."""
        # Use planets positions as unique identifier
        planets = natal_chart.get("planets", [])
        planets_str = json.dumps(
            [(p["name"], round(p["degree"], 1)) for p in planets],
            sort_keys=True
        )
        return hashlib.md5(planets_str.encode()).hexdigest()[:16]

    async def clear_all(self) -> None:
        """Clear all cache entries (for testing)."""
        self._memory_cache.clear()
        if self._redis:
            try:
                # Only clear astro:* keys
                keys = self._redis.keys("astro:*")
                if keys:
                    self._redis.delete(*keys)
            except Exception as e:
                logger.error(f"Redis clear error: {e}")

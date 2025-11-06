# Lunar Module — Техническая спецификация

## 1. Обзор

Lunar модуль рассчитывает лунные дни, фазы Луны и определяет значимость снов на основе лунного календаря.

---

## 2. Требования

### 2.1 Функциональные требования

| ID | Требование | Приоритет |
|----|------------|-----------|
| LUNAR-F-001 | Расчет текущего лунного дня (1-30) | P0 |
| LUNAR-F-002 | Определение фазы Луны (новолуние, растущая, полнолуние, убывающая) | P0 |
| LUNAR-F-003 | Возврат значимости сна по лунному дню | P0 |
| LUNAR-F-004 | Поддержка временных зон | P0 |
| LUNAR-F-005 | Исторические расчеты (любая дата) | P1 |
| LUNAR-F-006 | Прогноз лунных дней на месяц | P1 |
| LUNAR-F-007 | Локализация RU/EN | P0 |
| LUNAR-F-008 | Кэширование результатов | P1 |

### 2.2 Нефункциональные требования

| ID | Метрика | Значение |
|----|---------|----------|
| LUNAR-NF-001 | Latency (p95) | ≤ 50ms |
| LUNAR-NF-002 | Accuracy | 100% (astronomical) |
| LUNAR-NF-003 | Cache hit rate | ≥ 95% |
| LUNAR-NF-004 | Uptime | 99.9% |

---

## 3. Лунный календарь снов

### 3.1 Таблица значений лунных дней

```yaml
lunar_days:
  1:
    name_ru: "Новые начинания"
    name_en: "New Beginnings"
    significance: "positive"
    dream_type: "prophetic"
    interpretation: "Сны символизируют новые возможности и начало циклов"
    confidence: 0.85

  2:
    name_ru: "Материализация желаний"
    name_en: "Wish Manifestation"
    significance: "positive"
    dream_type: "revealing"
    interpretation: "Сны показывают, чего действительно желает душа"
    confidence: 0.80

  3:
    name_ru: "День действий"
    name_en: "Day of Action"
    significance: "neutral"
    dream_type: "guiding"
    interpretation: "Сны подсказывают конкретные шаги к цели"
    confidence: 0.75

  4:
    name_ru: "Выбор пути"
    name_en: "Path Selection"
    significance: "diagnostic"
    dream_type: "warning"
    interpretation: "Сны предупреждают о развилках судьбы"
    confidence: 0.80

  # ... (до 30 дня)

  15:
    name_ru: "Полнолуние - день силы"
    name_en: "Full Moon - Power Day"
    significance: "highly_positive"
    dream_type: "prophetic"
    interpretation: "Максимально вероятные вещие сны"
    confidence: 0.95

  29:
    name_ru: "Темная луна"
    name_en: "Dark Moon"
    significance: "warning"
    dream_type: "shadow_work"
    interpretation: "Сны раскрывают подсознательные страхи"
    confidence: 0.90
```

### 3.2 Фазы Луны

```yaml
moon_phases:
  new_moon:
    name_ru: "Новолуние"
    name_en: "New Moon"
    days: [1, 2]
    dream_quality: "prophetic"
    interpretation: "Начало нового лунного цикла, вещие сны"

  waxing_crescent:
    name_ru: "Растущая луна"
    name_en: "Waxing Crescent"
    days: [3-7]
    dream_quality: "constructive"
    interpretation: "Сны о росте, развитии, новых проектах"

  first_quarter:
    name_ru: "Первая четверть"
    name_en: "First Quarter"
    days: [8-10]
    dream_quality: "action-oriented"
    interpretation: "Сны призывают к действиям"

  waxing_gibbous:
    name_ru: "Прибывающая луна"
    name_en: "Waxing Gibbous"
    days: [11-14]
    dream_quality: "analytical"
    interpretation: "Сны помогают анализировать ситуации"

  full_moon:
    name_ru: "Полнолуние"
    name_en: "Full Moon"
    days: [15, 16]
    dream_quality: "highly_prophetic"
    interpretation: "Пик лунной энергии, максимально значимые сны"

  waning_gibbous:
    name_ru: "Убывающая луна"
    name_en: "Waning Gibbous"
    days: [17-21]
    dream_quality: "reflective"
    interpretation: "Сны для рефлексии и осознания"

  last_quarter:
    name_ru: "Последняя четверть"
    name_en: "Last Quarter"
    days: [22-24]
    dream_quality: "releasing"
    interpretation: "Сны о завершении циклов"

  waning_crescent:
    name_ru: "Темнеющая луна"
    name_en: "Waning Crescent"
    days: [25-30]
    dream_quality: "introspective"
    interpretation: "Глубокие внутренние процессы"
```

---

## 4. Архитектура

### 4.1 System Context

```
┌──────────┐
│  Client  │
└─────┬────┘
      │
      ▼
┌─────────────────────────────────┐
│    Lunar Service (FastAPI)      │
│                                 │
│  ┌───────────────────────────┐ │
│  │ Date/Time Input + TZ      │ │
│  └────────────┬──────────────┘ │
│               ▼                 │
│  ┌───────────────────────────┐ │
│  │   Astronomical Engine     │ │
│  │     (ephem/astral)        │ │
│  └────────────┬──────────────┘ │
│               ▼                 │
│  ┌───────────────────────────┐ │
│  │  Lunar Day Calculator     │ │
│  └────────────┬──────────────┘ │
│               ▼                 │
│  ┌───────────────────────────┐ │
│  │ Interpretation Lookup     │ │
│  │   (lunar_days.json)       │ │
│  └────────────┬──────────────┘ │
│               ▼                 │
│  ┌───────────────────────────┐ │
│  │    Cache Layer (Redis)    │ │
│  └───────────────────────────┘ │
└─────────────────────────────────┘
```

### 4.2 Component Diagram

```
backend/
├── services/
│   └── lunar/
│       ├── __init__.py
│       ├── service.py              # Main lunar orchestration
│       ├── calculator.py           # Lunar calculations
│       ├── interpreter.py          # Dream interpretation by day
│       ├── cache.py                # Redis caching
│       └── schemas.py              # Pydantic models
├── api/
│   └── v1/
│       └── lunar.py                # FastAPI endpoints
└── data/
    └── lunar_days.json             # Lunar day metadata
```

---

## 5. API Specification

### 5.1 Get Current Lunar Day

#### GET /api/v1/lunar/current

**Query Parameters**:
- `timezone` (optional): IANA timezone (default: UTC)
- `locale` (optional): ru|en (default: en)

**Response**:
```json
{
  "date": "2025-11-01",
  "lunar_day": 24,
  "moon_phase": "waning_gibbous",
  "moon_phase_name": "Убывающая луна",
  "illumination": 0.68,
  "significance": {
    "name": "День прозрения",
    "type": "diagnostic",
    "dream_quality": "reflective",
    "interpretation": "Сны раскрывают скрытые истины и помогают понять себя",
    "confidence": 0.88
  },
  "recommendations": [
    "Обратите внимание на повторяющиеся символы",
    "Записывайте сон сразу после пробуждения",
    "Медитируйте перед сном"
  ]
}
```

### 5.2 Get Lunar Day for Specific Date

#### GET /api/v1/lunar/date/{date}

**Path Parameters**:
- `date`: YYYY-MM-DD

**Query Parameters**:
- `timezone`: IANA timezone
- `locale`: ru|en

**Response**: Same as `/current`

### 5.3 Get Monthly Lunar Calendar

#### GET /api/v1/lunar/month?year=2025&month=11

**Response**:
```json
{
  "year": 2025,
  "month": 11,
  "days": [
    {
      "date": "2025-11-01",
      "lunar_day": 24,
      "moon_phase": "waning_gibbous",
      "illumination": 0.68,
      "significance_level": "medium"
    },
    // ... 29 more days
  ],
  "special_days": [
    {
      "date": "2025-11-15",
      "lunar_day": 15,
      "type": "full_moon",
      "significance": "highly_positive"
    }
  ]
}
```

### 5.4 Get Dream Significance

#### POST /api/v1/lunar/significance

**Request**:
```json
{
  "dream_date": "2025-11-01T03:30:00Z",
  "timezone": "Europe/Moscow"
}
```

**Response**:
```json
{
  "dream_date": "2025-11-01T06:30:00+03:00",
  "lunar_day": 24,
  "significance": {
    "level": "medium",
    "type": "diagnostic",
    "prophetic_probability": 0.65,
    "interpretation": "Сон имеет диагностическое значение..."
  }
}
```

---

## 6. Implementation Details

### 6.1 Lunar Calculator

```python
# backend/services/lunar/calculator.py

import ephem
from datetime import datetime, timezone
from typing import Tuple
import math

class LunarCalculator:
    """Calculate lunar day and moon phase"""

    def __init__(self):
        self.moon = ephem.Moon()
        self.observer = ephem.Observer()

    def get_lunar_day(
        self,
        dt: datetime,
        tz: timezone = timezone.utc
    ) -> Tuple[int, float]:
        """
        Calculate lunar day (1-30) and illumination

        Returns:
            (lunar_day, illumination)
        """

        # Convert to UTC
        dt_utc = dt.astimezone(timezone.utc)

        # Set observer time
        self.observer.date = dt_utc

        # Calculate moon phase
        self.moon.compute(self.observer)

        # Get moon phase (0-1, where 0 and 1 are new moon)
        illumination = self.moon.phase / 100.0

        # Calculate days since last new moon
        # Method: find previous new moon
        previous_new_moon = ephem.previous_new_moon(self.observer.date)

        # Calculate elapsed time in days
        elapsed_days = float(self.observer.date - previous_new_moon)

        # Lunar day is floor(elapsed_days) + 1
        # Range: 1-30 (synodic month ~29.53 days)
        lunar_day = int(elapsed_days) + 1

        # Clamp to 1-30
        if lunar_day > 30:
            lunar_day = 30

        return lunar_day, illumination

    def get_moon_phase_name(self, illumination: float, lunar_day: int) -> str:
        """
        Determine moon phase name based on illumination and day

        Phases:
        - New Moon: days 1-2
        - Waxing Crescent: days 3-7
        - First Quarter: days 8-10
        - Waxing Gibbous: days 11-14
        - Full Moon: days 15-16
        - Waning Gibbous: days 17-21
        - Last Quarter: days 22-24
        - Waning Crescent: days 25-30
        """

        if lunar_day <= 2:
            return "new_moon"
        elif 3 <= lunar_day <= 7:
            return "waxing_crescent"
        elif 8 <= lunar_day <= 10:
            return "first_quarter"
        elif 11 <= lunar_day <= 14:
            return "waxing_gibbous"
        elif 15 <= lunar_day <= 16:
            return "full_moon"
        elif 17 <= lunar_day <= 21:
            return "waning_gibbous"
        elif 22 <= lunar_day <= 24:
            return "last_quarter"
        else:  # 25-30
            return "waning_crescent"

    def get_next_full_moon(self, dt: datetime) -> datetime:
        """Get next full moon date"""
        self.observer.date = dt.astimezone(timezone.utc)
        next_fm = ephem.next_full_moon(self.observer.date)
        return ephem.Date(next_fm).datetime().replace(tzinfo=timezone.utc)

    def get_next_new_moon(self, dt: datetime) -> datetime:
        """Get next new moon date"""
        self.observer.date = dt.astimezone(timezone.utc)
        next_nm = ephem.next_new_moon(self.observer.date)
        return ephem.Date(next_nm).datetime().replace(tzinfo=timezone.utc)
```

### 6.2 Interpreter

```python
# backend/services/lunar/interpreter.py

import json
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class LunarInterpreter:
    """Interpret dream significance based on lunar day"""

    def __init__(self, data_path: Path):
        self.data = self._load_lunar_data(data_path)

    def _load_lunar_data(self, path: Path) -> Dict[int, Dict[str, Any]]:
        """Load lunar day metadata from JSON"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['lunar_days']

    def get_significance(
        self,
        lunar_day: int,
        moon_phase: str,
        locale: str = "en"
    ) -> Dict[str, Any]:
        """
        Get dream significance for given lunar day

        Returns:
            {
                "name": str,
                "type": str,
                "dream_quality": str,
                "interpretation": str,
                "confidence": float
            }
        """

        day_data = self.data.get(str(lunar_day))

        if not day_data:
            logger.warning(f"No data for lunar day {lunar_day}")
            return self._get_default_significance(locale)

        # Select localized fields
        name_key = f"name_{locale}"
        interp_key = f"interpretation_{locale}"

        return {
            "name": day_data.get(name_key, day_data.get("name_en")),
            "type": day_data.get("significance"),
            "dream_quality": day_data.get("dream_type"),
            "interpretation": day_data.get(interp_key, day_data.get("interpretation_en")),
            "confidence": day_data.get("confidence", 0.75),
            "prophetic_probability": self._calculate_prophetic_probability(
                lunar_day,
                moon_phase
            )
        }

    def _calculate_prophetic_probability(
        self,
        lunar_day: int,
        moon_phase: str
    ) -> float:
        """
        Calculate prophetic probability (0-1)

        Higher probability for:
        - Full moon (days 15-16): 0.90-0.95
        - New moon (days 1-2): 0.80-0.85
        - Special days: 0.70-0.80
        - Other days: 0.50-0.70
        """

        base_probability = 0.60

        # Full moon boost
        if 14 <= lunar_day <= 16:
            base_probability = 0.92

        # New moon boost
        elif 1 <= lunar_day <= 2:
            base_probability = 0.83

        # Special prophetic days
        elif lunar_day in [3, 7, 12, 21, 29]:
            base_probability = 0.75

        # Adjust by phase
        phase_multipliers = {
            "full_moon": 1.0,
            "new_moon": 0.95,
            "waxing_gibbous": 0.90,
            "waning_gibbous": 0.85,
            "first_quarter": 0.80,
            "last_quarter": 0.75,
            "waxing_crescent": 0.70,
            "waning_crescent": 0.70
        }

        multiplier = phase_multipliers.get(moon_phase, 1.0)
        final_prob = min(0.95, base_probability * multiplier)

        return round(final_prob, 2)

    def get_recommendations(
        self,
        lunar_day: int,
        moon_phase: str,
        locale: str = "en"
    ) -> list[str]:
        """Get recommendations for dream work"""

        recommendations = []

        # Full moon recommendations
        if moon_phase == "full_moon":
            if locale == "ru":
                recommendations = [
                    "Максимально вероятные вещие сны",
                    "Записывайте все детали сразу после пробуждения",
                    "Обратите внимание на эмоции во сне",
                    "Сон может исполниться в течение 2 недель"
                ]
            else:
                recommendations = [
                    "Highly prophetic dreams likely",
                    "Record all details immediately upon waking",
                    "Pay attention to emotions in the dream",
                    "Dream may manifest within 2 weeks"
                ]

        # New moon recommendations
        elif moon_phase == "new_moon":
            if locale == "ru":
                recommendations = [
                    "Сны о новых начинаниях",
                    "Хорошее время для планирования",
                    "Медитируйте перед сном",
                    "Визуализируйте желаемое"
                ]
            else:
                recommendations = [
                    "Dreams about new beginnings",
                    "Good time for planning",
                    "Meditate before sleep",
                    "Visualize your desires"
                ]

        # General recommendations
        else:
            if locale == "ru":
                recommendations = [
                    "Ведите дневник снов",
                    "Обращайте внимание на повторяющиеся символы",
                    "Не игнорируйте тревожные сны"
                ]
            else:
                recommendations = [
                    "Keep a dream journal",
                    "Notice recurring symbols",
                    "Don't ignore warning dreams"
                ]

        return recommendations

    def _get_default_significance(self, locale: str) -> Dict[str, Any]:
        """Default response when data unavailable"""
        return {
            "name": "Обычный день" if locale == "ru" else "Regular day",
            "type": "neutral",
            "dream_quality": "standard",
            "interpretation": (
                "Сон имеет стандартное значение"
                if locale == "ru"
                else "Dream has standard significance"
            ),
            "confidence": 0.60,
            "prophetic_probability": 0.55
        }
```

### 6.3 Service Layer

```python
# backend/services/lunar/service.py

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class LunarService:
    def __init__(
        self,
        calculator: LunarCalculator,
        interpreter: LunarInterpreter,
        cache_client
    ):
        self.calculator = calculator
        self.interpreter = interpreter
        self.cache = cache_client

    async def get_current_lunar_info(
        self,
        timezone_str: str = "UTC",
        locale: str = "en"
    ) -> Dict[str, Any]:
        """Get current lunar information"""

        # Get current time in specified timezone
        tz = ZoneInfo(timezone_str)
        now = datetime.now(tz)

        return await self.get_lunar_info_for_date(now, locale)

    async def get_lunar_info_for_date(
        self,
        dt: datetime,
        locale: str = "en"
    ) -> Dict[str, Any]:
        """Get lunar information for specific date"""

        # Check cache
        cache_key = f"lunar:{dt.date()}:{locale}"
        cached = await self.cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit: {cache_key}")
            return cached

        # Calculate lunar day and phase
        lunar_day, illumination = self.calculator.get_lunar_day(dt)
        moon_phase = self.calculator.get_moon_phase_name(illumination, lunar_day)

        # Get interpretation
        significance = self.interpreter.get_significance(
            lunar_day,
            moon_phase,
            locale
        )

        recommendations = self.interpreter.get_recommendations(
            lunar_day,
            moon_phase,
            locale
        )

        # Get phase name (localized)
        moon_phase_names = {
            "en": {
                "new_moon": "New Moon",
                "waxing_crescent": "Waxing Crescent",
                "first_quarter": "First Quarter",
                "waxing_gibbous": "Waxing Gibbous",
                "full_moon": "Full Moon",
                "waning_gibbous": "Waning Gibbous",
                "last_quarter": "Last Quarter",
                "waning_crescent": "Waning Crescent"
            },
            "ru": {
                "new_moon": "Новолуние",
                "waxing_crescent": "Растущая луна",
                "first_quarter": "Первая четверть",
                "waxing_gibbous": "Прибывающая луна",
                "full_moon": "Полнолуние",
                "waning_gibbous": "Убывающая луна",
                "last_quarter": "Последняя четверть",
                "waning_crescent": "Темнеющая луна"
            }
        }

        result = {
            "date": dt.date().isoformat(),
            "lunar_day": lunar_day,
            "moon_phase": moon_phase,
            "moon_phase_name": moon_phase_names[locale][moon_phase],
            "illumination": round(illumination, 2),
            "significance": significance,
            "recommendations": recommendations,
            "next_full_moon": self.calculator.get_next_full_moon(dt).date().isoformat(),
            "next_new_moon": self.calculator.get_next_new_moon(dt).date().isoformat()
        }

        # Cache for 24 hours
        await self.cache.set(cache_key, result, ttl=86400)

        return result
```

### 6.4 Caching Layer

```python
# backend/services/lunar/cache.py

import json
import redis.asyncio as redis
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

class LunarCache:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    async def get(self, key: str) -> Optional[dict]:
        """Get cached value"""
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None

    async def set(self, key: str, value: dict, ttl: int = 3600):
        """Set cached value with TTL"""
        try:
            await self.redis.setex(
                key,
                ttl,
                json.dumps(value)
            )
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def delete(self, key: str):
        """Delete cached value"""
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")

    async def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern"""
        try:
            async for key in self.redis.scan_iter(match=pattern):
                await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
```

---

## 7. Data Schema

### 7.1 lunar_days.json

```json
{
  "lunar_days": {
    "1": {
      "name_ru": "Новые начинания",
      "name_en": "New Beginnings",
      "significance": "positive",
      "dream_type": "prophetic",
      "interpretation_ru": "Сны первого лунного дня символизируют новые возможности и начало важных циклов в жизни",
      "interpretation_en": "Dreams on the first lunar day symbolize new opportunities and the beginning of important life cycles",
      "confidence": 0.85,
      "keywords": ["начало", "возможность", "старт", "новизна"]
    },
    "15": {
      "name_ru": "Полнолуние - день силы",
      "name_en": "Full Moon - Power Day",
      "significance": "highly_positive",
      "dream_type": "prophetic",
      "interpretation_ru": "Максимально вероятные вещие сны, пик лунной энергии",
      "interpretation_en": "Highly prophetic dreams, peak of lunar energy",
      "confidence": 0.95,
      "keywords": ["полнота", "кульминация", "откровение", "пророчество"]
    }
    // ... остальные дни
  }
}
```

---

## 8. Testing

### 8.1 Unit Tests

```python
# tests/unit/test_lunar_calculator.py

import pytest
from datetime import datetime, timezone
from backend.services.lunar.calculator import LunarCalculator

def test_lunar_day_calculation():
    """Test accurate lunar day calculation"""
    calc = LunarCalculator()

    # Known full moon date
    dt = datetime(2025, 11, 15, 12, 0, 0, tzinfo=timezone.utc)
    lunar_day, illumination = calc.get_lunar_day(dt)

    assert 14 <= lunar_day <= 16  # Full moon range
    assert illumination >= 0.95

def test_moon_phase_names():
    """Test moon phase name determination"""
    calc = LunarCalculator()

    assert calc.get_moon_phase_name(0.10, 1) == "new_moon"
    assert calc.get_moon_phase_name(0.50, 8) == "first_quarter"
    assert calc.get_moon_phase_name(0.98, 15) == "full_moon"
    assert calc.get_moon_phase_name(0.50, 22) == "last_quarter"

def test_timezone_handling():
    """Test timezone conversions"""
    calc = LunarCalculator()

    dt_utc = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    dt_moscow = dt_utc.astimezone(ZoneInfo("Europe/Moscow"))

    day_utc, _ = calc.get_lunar_day(dt_utc)
    day_moscow, _ = calc.get_lunar_day(dt_moscow)

    # Should be the same lunar day
    assert day_utc == day_moscow
```

### 8.2 Integration Tests

```python
# tests/integration/test_lunar_service.py

@pytest.mark.asyncio
async def test_lunar_service_with_cache():
    """Test caching behavior"""
    service = create_lunar_service()

    # First call - cache miss
    result1 = await service.get_current_lunar_info()

    # Second call - cache hit
    result2 = await service.get_current_lunar_info()

    assert result1 == result2

    # Verify cache was used
    cache_stats = await service.cache.redis.info("stats")
    assert cache_stats["keyspace_hits"] >= 1
```

---

## 9. Performance

### 9.1 Benchmarks

```python
# benchmarks/lunar_benchmark.py

import time
import asyncio

async def benchmark_lunar_calculation():
    """Benchmark lunar calculations"""

    service = create_lunar_service()
    iterations = 1000

    start = time.time()

    tasks = [
        service.get_current_lunar_info()
        for _ in range(iterations)
    ]

    await asyncio.gather(*tasks)

    elapsed = time.time() - start
    avg_latency = (elapsed / iterations) * 1000  # ms

    print(f"Average latency: {avg_latency:.2f}ms")
    assert avg_latency < 50, "Latency exceeds 50ms threshold"
```

### 9.2 Expected Performance

```yaml
Without cache:
  - p50: 15ms
  - p95: 30ms
  - p99: 50ms

With cache (95% hit rate):
  - p50: 2ms
  - p95: 5ms
  - p99: 10ms

Throughput:
  - 10,000 req/s (cached)
  - 1,000 req/s (uncached)
```

---

## 10. Deployment

### 10.1 Environment Variables

```bash
# .env.lunar

REDIS_URL=redis://localhost:6379/1
LUNAR_DATA_PATH=/app/data/lunar_days.json
DEFAULT_TIMEZONE=UTC
CACHE_TTL=86400  # 24 hours
```

### 10.2 Docker

```dockerfile
FROM python:3.11-slim

# Install system dependencies for ephem
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 11. Future Enhancements

### Phase 2 (Weeks 9-12)
- [ ] Персональные лунные гороскопы
- [ ] Интеграция с астрологическими данными
- [ ] ML-модель для предсказания вещих снов
- [ ] Push-уведомления о важных лунных днях

### Phase 3 (Months 4-6)
- [ ] Анализ корреляции снов и лунных фаз (статистика)
- [ ] Интеграция с планетарными транзитами
- [ ] Персонализированный лунный календарь

---

**Document Version**: 1.0
**Last Updated**: 2025-11-01
**Owner**: Lunar Module Team

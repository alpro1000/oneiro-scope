"""Error handling for Astrology Service."""

from enum import Enum
from typing import Optional


class AstrologyErrorCode(str, Enum):
    """Standard error codes for astrology service."""

    # Input validation errors
    INVALID_DATE = "INVALID_DATE"
    INVALID_TIME = "INVALID_TIME"
    INVALID_COORDINATES = "INVALID_COORDINATES"
    MISSING_LOCATION = "MISSING_LOCATION"
    INVALID_PERIOD = "INVALID_PERIOD"
    INVALID_EVENT_TYPE = "INVALID_EVENT_TYPE"

    # External service errors
    GEOCODING_FAILED = "GEOCODING_FAILED"
    EPHEMERIS_UNAVAILABLE = "EPHEMERIS_UNAVAILABLE"
    LLM_ERROR = "LLM_ERROR"
    CACHE_ERROR = "CACHE_ERROR"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Internal errors
    CALCULATION_ERROR = "CALCULATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AstrologyError(Exception):
    """Base exception for astrology service."""

    def __init__(
        self,
        code: AstrologyErrorCode,
        message: str,
        suggestions: Optional[list[str]] = None,
        details: Optional[dict] = None,
    ):
        self.code = code
        self.message = message
        self.suggestions = suggestions or []
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "code": self.code.value,
            "message": self.message,
            "suggestions": self.suggestions,
            "details": self.details,
        }


class GeocodingError(AstrologyError):
    """Error in geocoding operation."""

    def __init__(self, place: str, reason: Optional[str] = None):
        message = f"Не удалось определить координаты для '{place}'"
        if reason:
            message += f": {reason}"

        suggestions = [
            "Уточните название города (например: 'Москва, Россия')",
            "Проверьте правильность написания",
            "Попробуйте указать координаты напрямую",
        ]

        super().__init__(
            code=AstrologyErrorCode.GEOCODING_FAILED,
            message=message,
            suggestions=suggestions,
            details={"place": place, "reason": reason},
        )


class EphemerisError(AstrologyError):
    """Error in ephemeris calculation."""

    def __init__(self, reason: str, date: Optional[str] = None):
        message = f"Ошибка расчета эфемерид: {reason}"
        suggestions = [
            "Проверьте, что дата находится в поддерживаемом диапазоне",
            "Попробуйте повторить запрос позже",
        ]

        super().__init__(
            code=AstrologyErrorCode.EPHEMERIS_UNAVAILABLE,
            message=message,
            suggestions=suggestions,
            details={"reason": reason, "date": date},
        )


class ValidationError(AstrologyError):
    """Input validation error."""

    def __init__(self, field: str, message: str, suggestions: Optional[list[str]] = None):
        code_map = {
            "birth_date": AstrologyErrorCode.INVALID_DATE,
            "birth_time": AstrologyErrorCode.INVALID_TIME,
            "coords": AstrologyErrorCode.INVALID_COORDINATES,
            "birth_place": AstrologyErrorCode.MISSING_LOCATION,
            "period": AstrologyErrorCode.INVALID_PERIOD,
            "event_type": AstrologyErrorCode.INVALID_EVENT_TYPE,
        }

        super().__init__(
            code=code_map.get(field, AstrologyErrorCode.INTERNAL_ERROR),
            message=f"Ошибка валидации поля '{field}': {message}",
            suggestions=suggestions or [],
            details={"field": field},
        )


class RateLimitError(AstrologyError):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            code=AstrologyErrorCode.RATE_LIMIT_EXCEEDED,
            message=f"Превышен лимит запросов. Повторите через {retry_after} секунд.",
            suggestions=[
                "Подождите указанное время",
                "Используйте кэшированные данные",
            ],
            details={"retry_after": retry_after},
        )


class LLMError(AstrologyError):
    """Error in LLM interpretation."""

    def __init__(self, reason: str):
        super().__init__(
            code=AstrologyErrorCode.LLM_ERROR,
            message=f"Ошибка генерации интерпретации: {reason}",
            suggestions=[
                "Астрологические данные рассчитаны корректно",
                "Интерпретация будет доступна позже",
            ],
            details={"reason": reason},
        )


def handle_error(error: Exception) -> dict:
    """
    Convert any exception to standardized error response.

    Usage:
        try:
            result = await service.calculate()
        except Exception as e:
            return handle_error(e)
    """
    if isinstance(error, AstrologyError):
        return {
            "status": "error",
            "error": error.to_dict(),
        }

    # Unknown error
    return {
        "status": "error",
        "error": {
            "code": AstrologyErrorCode.INTERNAL_ERROR.value,
            "message": str(error),
            "suggestions": ["Обратитесь в поддержку, если ошибка повторяется"],
            "details": {"type": type(error).__name__},
        },
    }

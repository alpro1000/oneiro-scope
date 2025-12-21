"""Dream Analysis Service.

The heavy dependencies (LLM interpreters, large pydantic schemas) are imported
on-demand to keep lightweight test environments from failing during module
import. Attributes are resolved lazily via ``__getattr__``.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.dreams.service import DreamService
    from backend.services.dreams.schemas import (
        DreamAnalysisRequest,
        DreamAnalysisResponse,
        DreamSymbol,
        DreamCategory,
    )


__all__ = [
    "DreamService",
    "DreamAnalysisRequest",
    "DreamAnalysisResponse",
    "DreamSymbol",
    "DreamCategory",
]


def __getattr__(name: str):
    if name == "DreamService":
        from backend.services.dreams.service import DreamService as _DreamService

        return _DreamService
    if name in {
        "DreamAnalysisRequest",
        "DreamAnalysisResponse",
        "DreamSymbol",
        "DreamCategory",
    }:
        from backend.services.dreams import schemas

        return getattr(schemas, name)
    raise AttributeError(f"module 'backend.services.dreams' has no attribute {name!r}")

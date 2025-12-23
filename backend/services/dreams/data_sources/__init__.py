"""Data source connectors for dream datasets."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.dreams.data_sources.connectors import (
        DREAMConnector,
        DREAMSConnector,
        DreamBankConnector,
        SDDBConnector,
    )
    from backend.services.dreams.data_sources.registry import DreamSourceRegistry


__all__ = [
    "DREAMConnector",
    "DREAMSConnector",
    "DreamBankConnector",
    "SDDBConnector",
    "DreamSourceRegistry",
]


def __getattr__(name: str):
    if name in {
        "DREAMConnector",
        "DREAMSConnector",
        "DreamBankConnector",
        "SDDBConnector",
    }:
        from backend.services.dreams.data_sources import connectors

        return getattr(connectors, name)
    if name == "DreamSourceRegistry":
        from backend.services.dreams.data_sources.registry import DreamSourceRegistry as _Registry

        return _Registry
    raise AttributeError(f"module 'backend.services.dreams.data_sources' has no attribute {name!r}")

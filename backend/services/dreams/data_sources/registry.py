"""Registry for configuring dream data sources via YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import yaml

from backend.services.dreams.data_sources.connectors import (
    DREAMConnector,
    DREAMSConnector,
    DreamBankConnector,
    SDDBConnector,
)


class DreamSourceRegistry:
    """Loads dream data sources from a configuration file."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        with open(self.config_path, "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def build_connectors(self) -> List[object]:
        connectors: List[object] = []
        datasets = self.config.get("datasets", {})

        if "sddb" in datasets:
            connectors.append(SDDBConnector(datasets["sddb"].get("path_or_url")))
        if "dreambank" in datasets:
            connectors.append(DreamBankConnector(datasets["dreambank"].get("path_or_url")))
        if "dreams" in datasets:
            connectors.append(DREAMSConnector(datasets["dreams"].get("path_or_url")))
        if "dream" in datasets:
            connectors.append(DREAMConnector(datasets["dream"].get("path_or_url")))

        return connectors

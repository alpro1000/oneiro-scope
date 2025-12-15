"""Lunar content tables loader."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


@lru_cache
def _load_tables() -> dict:
    data_path = Path(__file__).resolve().parents[2] / "data" / "lunar_tables.json"
    with open(data_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def get_lunar_day_text(lunar_day: int, locale: str) -> dict:
    if lunar_day < 1 or lunar_day > 30:
        raise ValueError("lunar_day must be between 1 and 30")

    tables = _load_tables()
    lang = locale if locale in tables else "en"
    table = tables.get(lang)
    entry = table[lunar_day] if table else None

    if entry is None and lang != "en":
        entry = tables.get("en", [None] * 31)[lunar_day]

    if entry is None:
        raise ValueError(f"No entry found for lunar day {lunar_day}")

    return entry


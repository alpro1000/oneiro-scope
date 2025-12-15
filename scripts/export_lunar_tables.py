"""Export lunar content tables from the legacy calendar.js."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CALENDAR_JS = ROOT / "scripts" / "calendar.js"
OUTPUT = ROOT / "backend" / "data" / "lunar_tables.json"


def _normalize_object_notation(raw: str) -> str:
    return re.sub(r"(\{|,)\s*(\w+):", r'\1"\2":', raw)


def extract_tables(source: str) -> dict:
    pattern = re.compile(r"const\s+TABLE_(?P<lang>\w+)\s*=\s*(\[.*?\]);", re.DOTALL)
    tables: dict[str, list] = {}
    for match in pattern.finditer(source):
        lang = match.group("lang").lower()
        if lang not in {"ru", "en"}:
            continue
        raw_table = match.group(2)
        normalized = _normalize_object_notation(raw_table)
        tables[lang] = json.loads(normalized)
    return tables


def main() -> None:
    text = CALENDAR_JS.read_text(encoding="utf-8")
    tables = extract_tables(text)
    if not {"ru", "en"}.issubset(tables):
        raise SystemExit("Failed to parse TABLE_RU and TABLE_EN from calendar.js")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(tables, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written lunar tables to {OUTPUT}")


if __name__ == "__main__":
    main()


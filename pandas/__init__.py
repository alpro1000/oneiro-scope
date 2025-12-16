"""Lightweight pandas stub for offline environments.

This stub satisfies the minimal DataFrame/Series API surface that the ETL
pipeline and tests rely on without pulling heavyweight native dependencies.
If the real pandas library is available on PYTHONPATH, prefer installing it
and removing this shim.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, List

__version__ = "0.0.0-stub"


class Series:
    def __init__(self, data: List[Any]):
        self.data = list(data)

    def apply(self, func):
        return Series([func(item) for item in self.data])

    def astype(self, _type):
        if _type is str:
            return Series([str(item) for item in self.data])
        return Series([_type(item) for item in self.data])

    def between(self, left, right):
        return Series([(left <= item <= right) for item in self.data])

    def __add__(self, other):
        if isinstance(other, Series):
            return Series([a + b for a, b in zip(self.data, other.data)])
        return Series([a + other for a in self.data])

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return f"Series({self.data!r})"

    def all(self):
        return all(bool(x) for x in self.data)


class DataFrame:
    def __init__(self, data: Iterable[dict[str, Any]] | None = None):
        rows = list(data or [])
        self._data = deepcopy(rows)
        self._columns = list({k for row in rows for k in row.keys()})

    def __getitem__(self, key: str) -> Series:
        return Series([row.get(key) for row in self._data])

    def __setitem__(self, key: str, value):
        if isinstance(value, Series):
            values = list(value.data)
        elif isinstance(value, list):
            values = list(value)
        else:
            values = [value for _ in range(len(self._data))] if self._data else [value]
        if len(values) < len(self._data):
            values.extend([None] * (len(self._data) - len(values)))
        if not self._data:
            for _ in range(len(values)):
                self._data.append({})
        for row, v in zip(self._data, values):
            row[key] = v
        if key not in self._columns:
            self._columns.append(key)

    def __contains__(self, key: str) -> bool:
        return key in self._columns

    def __len__(self) -> int:
        return len(self._data)

    @property
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, value):
        self._columns = list(value)

    def copy(self) -> "DataFrame":
        return DataFrame(deepcopy(self._data))

    def to_parquet(self, path: str | Path, index: bool = False):
        Path(path).write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def head(self, n: int = 5):
        preview = self._data[:n]
        return DataFrame(preview)

    def __repr__(self):
        return f"DataFrame({self._data!r})"


__all__ = ["DataFrame", "Series", "__version__"]

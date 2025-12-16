from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class DreamEmbedder:
    """Lightweight stand-in for the DReAMy embedder.

    The real implementation would load a transformer model. Here we return a
    deterministic pseudo-embedding so downstream code can operate without heavy
    dependencies.
    """

    model_name: str = "bert-base-uncased"

    def encode(self, text: str) -> List[float]:
        if text is None:
            return []
        normalized = str(text).strip().lower()
        # simple hashing into a fixed-length vector
        base = sum(ord(ch) for ch in normalized)
        length = len(normalized.split()) or 1
        return [round((base % (i + 97)) / 1000.0, 6) for i in range(8)] + [length / 10.0]

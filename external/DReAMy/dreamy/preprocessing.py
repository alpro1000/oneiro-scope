from __future__ import annotations

from typing import List


def preprocess_dream(text: str) -> List[str]:
    """A tiny tokenizer placeholder for dream preprocessing.

    The real DReAMy library would include normalization, stemming, and
    domain-specific cleaning. For the purposes of this repository we keep the
    implementation lightweight while preserving the public API expected by the
    pipeline.
    """

    if text is None:
        return []
    # basic whitespace tokenization and lower-casing
    tokens = [t for t in str(text).lower().split() if t]
    return tokens

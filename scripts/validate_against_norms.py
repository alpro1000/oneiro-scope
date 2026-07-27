#!/usr/bin/env python3
"""Calibration run: our HVdC coder over the ACTUAL norm corpora.

`norms-m` / `norms-f` on DreamBank are the dreams the 1966 Hall/Van de
Castle norm tables were hand-coded from. Running the deterministic coder
over the same dreams and comparing aggregate indicators against the
published norms measures the coder's systematic bias against human
coding — the exact concern from review: a precision-first engine
undercounts, so users would look "calmer than the norm" as an artifact.

The output quantifies that bias per indicator. Numbers land in the
rebuild report §7.4 and, once stable, can become per-indicator
calibration notes in hvdc_norms.json.

Usage:
    python scripts/fetch_dreambank.py          # once, downloads the corpora
    python scripts/validate_against_norms.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DATA = REPO / "data" / "dreambank"


def run_collection(name: str) -> dict:
    from backend.services.dreams.analyzer import DreamAnalyzer

    payload = json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))
    analyzer = DreamAnalyzer()

    totals = {
        "n": 0, "male": 0, "female": 0, "animal": 0, "indefinite": 0,
        "friendly": 0, "aggressive": 0, "sexual": 0,
        "successes": 0, "failures": 0, "misfortunes": 0, "good_fortunes": 0,
        "pos_emotions": 0, "neg_emotions": 0,
    }
    for dream in payload["dreams"]:
        text = dream.get("content", "")
        if not text or len(text) < 10:
            continue
        _, content, *_rest, coding = analyzer.analyze(text, "en")
        totals["n"] += 1
        totals["male"] += content.male_characters
        totals["female"] += content.female_characters
        totals["animal"] += content.animal_characters
        totals["indefinite"] += coding.count_characters("indefinite")
        totals["friendly"] += content.friendly_interactions
        totals["aggressive"] += content.aggressive_interactions
        totals["sexual"] += content.sexual_interactions
        totals["successes"] += content.successes
        totals["failures"] += content.failures
        totals["misfortunes"] += content.misfortunes
        totals["good_fortunes"] += content.good_fortunes
        totals["pos_emotions"] += content.positive_emotions
        totals["neg_emotions"] += content.negative_emotions
    return totals


def indicators(t: dict) -> dict:
    human = t["male"] + t["female"]
    all_chars = human + t["indefinite"] + t["animal"]
    emotions = t["pos_emotions"] + t["neg_emotions"]
    outcomes = t["successes"] + t["failures"]
    return {
        "male_percent": t["male"] / human * 100 if human else None,
        "animal_percent": t["animal"] / all_chars * 100 if all_chars else None,
        "aggression_friendliness_ratio": (
            t["aggressive"] / t["friendly"] if t["friendly"] else None
        ),
        "aggression_per_dream": t["aggressive"] / t["n"],
        "friendliness_per_dream": t["friendly"] / t["n"],
        "sexuality_per_dream": t["sexual"] / t["n"],
        "negative_percent": (
            t["neg_emotions"] / emotions * 100 if emotions else None
        ),
        "dreamer_success_percent": (
            t["successes"] / outcomes * 100 if outcomes else None
        ),
        "misfortune_per_dream": t["misfortunes"] / t["n"],
        "good_fortune_per_dream": t["good_fortunes"] / t["n"],
    }


PUBLISHED = {  # from backend/services/dreams/knowledge_base/hvdc_norms.json
    "norms-m": {
        "male_percent": 67, "animal_percent": 6,
        "aggression_friendliness_ratio": 0.59,
        "aggression_per_dream": 0.47, "friendliness_per_dream": 0.38,
        "sexuality_per_dream": 0.12, "negative_percent": 80,
        "dreamer_success_percent": 51,
        "misfortune_per_dream": 0.36, "good_fortune_per_dream": 0.06,
    },
    "norms-f": {
        "male_percent": 48, "animal_percent": 4,
        "aggression_friendliness_ratio": 0.32,
        "aggression_per_dream": 0.29, "friendliness_per_dream": 0.43,
        "sexuality_per_dream": 0.04, "negative_percent": 80,
        "dreamer_success_percent": 42,
        "misfortune_per_dream": 0.33, "good_fortune_per_dream": 0.06,
    },
}


def main() -> int:
    missing = [c for c in PUBLISHED if not (DATA / f"{c}.json").exists()]
    if missing:
        print(f"Missing corpora {missing} — run scripts/fetch_dreambank.py first.")
        return 1

    for name, published in PUBLISHED.items():
        t = run_collection(name)
        ours = indicators(t)
        print(f"\n=== {name}: {t['n']} dreams (human-coded basis of the 1966 norms) ===")
        print(f"{'indicator':32} {'coder':>8} {'norm':>8} {'coder/norm':>10}")
        for key, norm in published.items():
            val = ours[key]
            if val is None:
                print(f"{key:32} {'n/a':>8} {norm:>8}")
                continue
            ratio = val / norm if norm else float("nan")
            print(f"{key:32} {val:8.2f} {norm:8.2f} {ratio:10.2f}")
    print(
        "\ncoder/norm < 1.0 quantifies the precision-first undercount vs the"
        "\nhuman coders (see norm_comparison.method_note). Rates per dream"
        "\n(aggression_per_dream etc.) are the calibration-relevant rows;"
        "\npercent-composition rows (male_percent) also reflect detection"
        "\nasymmetries between categories."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

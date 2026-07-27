#!/usr/bin/env python3
"""Inter-annotator agreement for the HVdC golden set (Cohen's kappa).

Why this exists. The golden annotations and the coder were produced by the
same agent, so the CI metric measures INTERNAL CONSISTENCY, not accuracy:
a misreading of the HVdC rules would sit identically in both the coder and
the golds and never fail a test. The independent check is a second human
annotator coding the same 28 texts BLIND from the primary Hall & Van de
Castle rules, and this script quantifying the agreement.

Usage:
    1. Fill backend/tests/dreams/golden/blind_annotation_template.json
       (a copy without the golden labels) — do not look at golden_*.json.
    2. python scripts/kappa_golden.py <filled_template.json>

Output: per-category linear- and quadratic-weighted Cohen's kappa over the
28 paired counts, raw exact-agreement, and every disagreement listed for
adjudication. Interpretation guide (Landis & Koch 1977): <0.20 slight,
0.21-0.40 fair, 0.41-0.60 moderate, 0.61-0.80 substantial, >0.80 almost
perfect. Low kappa on a category means the two readings of the HVdC rules
diverge there — adjudicate against the primary source, fix whichever side
is wrong (golds OR coder), rerun.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GOLDEN_DIR = REPO / "backend" / "tests" / "dreams" / "golden"

FIELDS = [
    "male_characters", "female_characters", "animal_characters",
    "friendly_interactions", "aggressive_interactions", "sexual_interactions",
    "successes", "failures", "misfortunes", "good_fortunes",
]


def weighted_kappa(a: list[int], b: list[int], weight: str) -> float | None:
    """Cohen's kappa with linear/quadratic weights over ordinal counts.

    None when both annotators are constant AND identical — agreement is
    perfect but chance-corrected kappa is undefined (no variance)."""
    cats = sorted(set(a) | set(b))
    if len(cats) == 1:
        return None
    k = len(cats)
    idx = {c: i for i, c in enumerate(cats)}
    n = len(a)

    def w(i: int, j: int) -> float:
        d = abs(i - j) / (k - 1)
        return d if weight == "linear" else d * d

    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[idx[x]][idx[y]] += 1 / n
    pa = Counter(a)
    pb = Counter(b)

    num = sum(w(i, j) * obs[i][j] for i in range(k) for j in range(k))
    den = sum(
        w(i, j) * (pa[cats[i]] / n) * (pb[cats[j]] / n)
        for i in range(k)
        for j in range(k)
    )
    if den == 0:
        return None
    return 1 - num / den


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    filled = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    golden: dict[str, dict] = {}
    for name in ("golden_ru.json", "golden_en.json"):
        for d in json.loads((GOLDEN_DIR / name).read_text(encoding="utf-8"))["dreams"]:
            golden[d["id"]] = d["expected"]

    by_field_a: dict[str, list[int]] = {f: [] for f in FIELDS}
    by_field_b: dict[str, list[int]] = {f: [] for f in FIELDS}
    disagreements = []
    skipped = []

    for entry in filled["dreams"]:
        did = entry["id"]
        counts = entry.get("counts", {})
        if did not in golden:
            skipped.append((did, "not in golden set"))
            continue
        if any(counts.get(f) is None for f in FIELDS):
            skipped.append((did, "unfilled counts"))
            continue
        for f in FIELDS:
            a, b = int(golden[did][f]), int(counts[f])
            by_field_a[f].append(a)
            by_field_b[f].append(b)
            if a != b:
                disagreements.append((did, f, a, b))

    n = len(by_field_a[FIELDS[0]])
    if n == 0:
        print("No fully annotated dreams found — fill the template first.")
        return 1

    print(f"Inter-annotator agreement over {n} dreams "
          f"(A = golden set, B = {filled.get('annotator', '?')})\n")
    print(f"{'category':28} {'exact%':>7} {'κ_lin':>7} {'κ_quad':>7}")
    for f in FIELDS:
        a, b = by_field_a[f], by_field_b[f]
        exact = sum(x == y for x, y in zip(a, b)) / n * 100
        kl = weighted_kappa(a, b, "linear")
        kq = weighted_kappa(a, b, "quadratic")
        fmt = lambda v: f"{v:7.2f}" if v is not None else "  const"
        print(f"{f:28} {exact:6.0f}% {fmt(kl)} {fmt(kq)}")

    if disagreements:
        print(f"\n{len(disagreements)} disagreement(s) to adjudicate "
              "(dream, category, golden, annotator-2):")
        for did, f, a, b in disagreements:
            print(f"  {did:24} {f:26} A={a} B={b}")
    else:
        print("\nNo disagreements.")
    if skipped:
        print(f"\nSkipped: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

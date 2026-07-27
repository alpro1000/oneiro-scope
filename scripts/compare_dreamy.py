#!/usr/bin/env python3
"""Compare the OneiroScope HVdC coder against DReAMy on the golden set.

DReAMy (github.com/lorenzoscottb/DReAMy; Bertolini et al. 2023,
arXiv:2302.14828) annotates dream reports with Hall/Van de Castle
features via HuggingFace models. Comparable axes against our engine:

- characters  — DReAMy NER (T5, EN-only) generates a character list;
  we map its male/female/animal mentions to counts and score both
  engines against the hand-coded golds (EN subset for fairness).
- emotions    — DReAMy SA (XLM-RoBERTa-large, multilingual) predicts
  HVdC emotion presence (AN/AP/SD/CO/HA); we take the top label and
  compare against the light `expected_primary_emotion` golds.

NOT comparable: social interactions (A/F scales), success/failure,
misfortune/good fortune — DReAMy's public models do not code them (its
RE task generates activity triples, a different HVdC chapter). Those
stay exclusive to our structural coder; the Fogli et al. (2020) tool
that did code aggression is not pip-installable.

Usage:
    python scripts/compare_dreamy.py [--skip-ner] [--skip-sa]

Heavy: downloads ~3 GB of HF models on first run. Exits with a clear
message when dreamy/torch are not installed.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

GOLDEN = [
    REPO / "backend" / "tests" / "dreams" / "golden" / "golden_ru.json",
    REPO / "backend" / "tests" / "dreams" / "golden" / "golden_en.json",
]

EMO_LABEL_TO_OURS = {
    "AN": "anger",
    "AP": "apprehension",
    "SD": "sadness",
    "CO": "confusion",
    "HA": "happiness",
}

CHAR_FIELDS = ["male_characters", "female_characters", "animal_characters"]


def load_dreams():
    dreams = []
    for path in GOLDEN:
        dreams += json.loads(path.read_text(encoding="utf-8"))["dreams"]
    return dreams


def our_predictions(dreams):
    from backend.services.dreams.analyzer import DreamAnalyzer

    analyzer = DreamAnalyzer()
    out = {}
    for d in dreams:
        _, content, emotion, *_ = analyzer.analyze(d["text"], d["locale"])
        out[d["id"]] = {
            "chars": {f: getattr(content, f) for f in CHAR_FIELDS},
            "emotion": emotion.value,
        }
    return out


def parse_dreamy_characters(generated: str) -> dict[str, int]:
    """DReAMy NER generates a DreamBank-style character list, e.g.
    'individual male known adult; group indefinite ...'. Count gender
    mentions per generated item."""
    counts = {f: 0 for f in CHAR_FIELDS}
    for item in generated.replace(",", ";").split(";"):
        low = item.lower()
        if not low.strip():
            continue
        if "animal" in low:
            counts["animal_characters"] += 1
        elif "female" in low or "woman" in low or "girl" in low:
            counts["female_characters"] += 1
        elif "male" in low or "man" in low or "boy" in low:
            counts["male_characters"] += 1
    return counts


def micro_pr(rows, fields):
    tp, fp, fn = defaultdict(int), defaultdict(int), defaultdict(int)
    for gold, pred in rows:
        for f in fields:
            g, p = gold[f], pred[f]
            tp[f] += min(g, p)
            fp[f] += max(0, p - g)
            fn[f] += max(0, g - p)
    out = {}
    for f in fields:
        P = tp[f] / (tp[f] + fp[f]) if tp[f] + fp[f] else 1.0
        R = tp[f] / (tp[f] + fn[f]) if tp[f] + fn[f] else 1.0
        out[f] = (P, R, tp[f], fp[f], fn[f])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-ner", action="store_true")
    ap.add_argument("--skip-sa", action="store_true")
    args = ap.parse_args()

    dreams = load_dreams()
    ours = our_predictions(dreams)

    try:
        import dreamy  # noqa: F401
    except ImportError as exc:
        print(f"DReAMy not installed ({exc}). pip install dreamy torch — ~3GB of models.")
        return 2

    results: dict = {"n_dreams": len(dreams)}

    # ---- characters: EN subset (DReAMy NER model is EN-only) ----
    if not args.skip_ner:
        en = [d for d in dreams if d["locale"] == "en"]
        print(f"NER (characters) over {len(en)} EN dreams…", flush=True)
        import dreamy as dr

        generated = dr.annotate_reports(
            [d["text"] for d in en], task="NER", device="cpu", batch_size=4
        )
        texts = [
            g["generated_text"] if isinstance(g, dict) else str(g) for g in generated
        ]
        dreamy_rows, our_rows = [], []
        per_dream = {}
        for d, g in zip(en, texts):
            pred = parse_dreamy_characters(g)
            per_dream[d["id"]] = {"generated": g, "parsed": pred}
            dreamy_rows.append((d["expected"], pred))
            our_rows.append((d["expected"], ours[d["id"]]["chars"]))
        results["characters_en"] = {
            "dreamy": micro_pr(dreamy_rows, CHAR_FIELDS),
            "oneiro": micro_pr(our_rows, CHAR_FIELDS),
            "dreamy_raw": per_dream,
        }

    # ---- emotions: full set (SA default model is multilingual) ----
    if not args.skip_sa:
        print(f"SA (emotions) over {len(dreams)} dreams…", flush=True)
        import dreamy as dr

        preds = dr.annotate_reports(
            [d["text"] for d in dreams], task="SA", device="cpu",
            batch_size=4, return_type="distribution",
        )
        scored = 0
        agree_dreamy = agree_ours = 0
        emo_rows = []
        for d, p in zip(dreams, preds):
            gold = d.get("expected_primary_emotion")
            # distribution: list of {label, score}
            top = max(p, key=lambda x: x["score"])["label"] if isinstance(p, list) else str(p)
            mapped = EMO_LABEL_TO_OURS.get(top, top)
            emo_rows.append({"id": d["id"], "gold": gold, "dreamy": mapped,
                             "oneiro": ours[d["id"]]["emotion"]})
            if gold:
                scored += 1
                agree_dreamy += mapped == gold
                agree_ours += ours[d["id"]]["emotion"] == gold
        results["emotions"] = {
            "n_scored": scored,
            "dreamy_accuracy": agree_dreamy / scored if scored else None,
            "oneiro_accuracy": agree_ours / scored if scored else None,
            "rows": emo_rows,
        }

    out_path = REPO / "docs" / "reports" / "dreamy_comparison_raw.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def _ser(o):
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in o.items()} if isinstance(o, dict) else o

    out_path.write_text(json.dumps(results, default=_ser, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"raw results → {out_path}")

    # ---- human-readable table ----
    if "characters_en" in results:
        print("\nCharacters (EN subset, micro P/R vs hand-coded golds):")
        print(f"{'field':22} {'DReAMy P':>9} {'DReAMy R':>9} {'Oneiro P':>9} {'Oneiro R':>9}")
        for f in CHAR_FIELDS:
            dp, dr_, *_ = results["characters_en"]["dreamy"][f]
            op, orr, *_ = results["characters_en"]["oneiro"][f]
            print(f"{f:22} {dp:9.2f} {dr_:9.2f} {op:9.2f} {orr:9.2f}")
    if "emotions" in results:
        e = results["emotions"]
        print(f"\nPrimary emotion accuracy over {e['n_scored']} annotated dreams: "
              f"DReAMy {e['dreamy_accuracy']:.2f} · Oneiro {e['oneiro_accuracy']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

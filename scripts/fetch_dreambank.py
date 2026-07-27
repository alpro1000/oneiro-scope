#!/usr/bin/env python3
"""Download DreamBank collections (JSON mirror) into data/dreambank/.

Source: github.com/mattbierner/DreamScrape — a JSON scrape of
DreamBank.net (Domhoff & Schneider, UC Santa Cruz), ~30k dream reports
across ~90 collections. The two collections used for calibration are the
actual Hall/Van de Castle norm corpora: `norms-m` (491 male dreams) and
`norms-f` (490 female dreams) — the very dreams the 1966 norm tables
were hand-coded from.

DreamBank content is research material owned by its collectors; it is
NOT committed to this repository (data/dreambank/ is gitignored) — this
script re-fetches it reproducibly instead.

Usage:
    python scripts/fetch_dreambank.py                 # the two norm collections
    python scripts/fetch_dreambank.py alta ed emma    # any collections by id
    python scripts/fetch_dreambank.py --list          # probe some known ids

Alternative sources for the same material:
- Fogli, Aiello, Quercia (2020) algorithmic annotations of DreamBank
  (RSOS 10.1098/rsos.192080): Dryad, doi:10.5061/dryad.qbzkh18fr —
  https://datadryad.org/api/v2/datasets/doi%3A10.5061%2Fdryad.qbzkh18fr/download
- HuggingFace: `datasets.load_dataset("DReAMy-lib/DreamBank-dreams-en")`
Both hosts are blocked by some sandbox network policies; the GitHub raw
mirror above is what this script uses.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "data" / "dreambank"
RAW_BASE = "https://raw.githubusercontent.com/mattbierner/DreamScrape/master/dreams"

DEFAULT_COLLECTIONS = ["norms-m", "norms-f"]
KNOWN_SAMPLE = [
    "norms-m", "norms-f", "alta", "ed", "emma", "barb_sanders",
    "vietnam_vet", "blind-f", "blind-m",
]


def fetch(collection: str) -> Path:
    url = f"{RAW_BASE}/{collection}.json"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{collection}.json"
    print(f"{collection}: {url}")
    with urllib.request.urlopen(url, timeout=60) as resp:
        data = resp.read()
    payload = json.loads(data)
    out.write_bytes(data)
    print(f"  -> {out} ({len(payload.get('dreams', []))} dreams)")
    return out


def main() -> int:
    args = sys.argv[1:]
    if args == ["--list"]:
        for c in KNOWN_SAMPLE:
            try:
                req = urllib.request.Request(f"{RAW_BASE}/{c}.json", method="HEAD")
                urllib.request.urlopen(req, timeout=20)
                print(f"  {c}: available")
            except Exception as exc:
                print(f"  {c}: {exc}")
        return 0
    for collection in args or DEFAULT_COLLECTIONS:
        fetch(collection)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

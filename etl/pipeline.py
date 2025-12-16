from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

# Ensure local modules (pandas stub + external packages) are importable when executed from the etl/ directory
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "external" / "DReAMy"))
sys.path.insert(0, str(REPO_ROOT / "external" / "pyswisseph"))

import pandas as pd

from dreamy.preprocessing import preprocess_dream
from dreamy.embedder import DreamEmbedder
import swisseph as swe

RAW_DATA_PATH = REPO_ROOT / "data" / "dreams_curated.json"
ENRICHED_PATH = REPO_ROOT / "data" / "dreams_enriched.parquet"


def load_raw() -> pd.DataFrame:
    """Load curated dreams into a dataframe, or fall back to a small demo set."""

    if RAW_DATA_PATH.exists():
        with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = [
            {
                "symbol": "moon",
                "interpretation": "A calm night over the desert dunes.",
                "date": "2024-01-15",
            },
            {
                "symbol": "star",
                "interpretation": "Golden constellations guiding the traveler.",
                "date": "2024-02-02",
            },
        ]
    df = pd.DataFrame(data)
    if "date" not in df.columns:
        df["date"] = datetime.utcnow().date().isoformat()
    return df


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names and ensure dates are ISO-formatted strings."""

    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    if "symbol" not in df:
        df["symbol"] = "unknown"
    if "interpretation" not in df:
        df["interpretation"] = ""
    df["date"] = df["date"].apply(_normalize_date)
    return df


def _normalize_date(value: str | datetime) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date().isoformat()
        except ValueError:
            pass
    return datetime.utcnow().date().isoformat()


def enrich_with_dreamy(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет эмбеддинги и семантические теги."""

    embedder = DreamEmbedder(model_name="bert-base-uncased")
    df = df.copy()
    df["dreamy_text"] = df["symbol"].astype(str) + " " + df["interpretation"].astype(str)
    df["dreamy_tokens"] = df["dreamy_text"].apply(preprocess_dream)
    df["dreamy_embedding"] = df["dreamy_text"].apply(embedder.encode)
    return df


def enrich_with_astrology(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет фазу Луны для каждой даты."""

    swe.set_ephe_path(str(REPO_ROOT / "external" / "pyswisseph" / "ephe"))
    df = df.copy()
    df["lunar_phase"] = df["date"].apply(_lunar_phase_from_date)
    return df


def _lunar_phase_from_date(date_str: str) -> float:
    year, month, day = map(int, str(date_str).split("-"))
    jd = swe.julday(year, month, day)
    phase = swe.lun_phase(jd)
    # keep within [0, 1]
    return max(0.0, min(1.0, float(phase)))


def save_to_parquet(df: pd.DataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def run_pipeline(save: bool = True) -> pd.DataFrame:
    df = load_raw()
    df = normalize(df)
    df = enrich_with_dreamy(df)
    df = enrich_with_astrology(df)
    if save:
        save_to_parquet(df, ENRICHED_PATH)
    return df


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Oneiro-Scope ETL enrichment pipeline")
    parser.add_argument("--check", action="store_true", help="run pipeline without saving")
    args = parser.parse_args(list(argv) if argv is not None else None)

    df = run_pipeline(save=not args.check)
    if args.check:
        print(df.head())
    else:
        print(f"Saved enriched data to {ENRICHED_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

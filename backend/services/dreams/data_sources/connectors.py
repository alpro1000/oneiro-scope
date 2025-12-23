"""Connectors for scientific dream datasets and physiological archives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Union

import mne
import pandas as pd

from backend.services.dreams.schemas import (
    DataProvenance,
    DreamSourceMetadata,
    DreamSourceRecord,
    PhysiologicalEvent,
)


@dataclass
class _PathInfo:
    """Small helper for working with local or remote paths."""

    uri: str

    @property
    def path(self) -> Path:
        return Path(self.uri)

    @property
    def suffix(self) -> str:
        return self.path.suffix.lower()


class BaseConnector:
    """Base connector with provenance helpers."""

    dataset: str

    def __init__(self, path_or_url: Union[str, Path]):
        self.path_info = _PathInfo(str(path_or_url))

    def _build_provenance(self, loader: str, record_count: int) -> DataProvenance:
        return DataProvenance(
            dataset=self.dataset,
            loader=loader,
            uri=self.path_info.uri,
            record_count=record_count,
            ingested_at=datetime.utcnow(),
        )

    def _read_table(self) -> pd.DataFrame:
        if self.path_info.suffix in {".csv", ".tsv"}:
            separator = "\t" if self.path_info.suffix == ".tsv" else ","
            return pd.read_csv(self.path_info.uri, sep=separator)
        if self.path_info.suffix in {".json", ".jsonl"}:
            return pd.read_json(self.path_info.uri, lines=self.path_info.suffix == ".jsonl")
        raise ValueError(f"Unsupported tabular format: {self.path_info.suffix}")


class SDDBConnector(BaseConnector):
    """Connector for Sleep and Dream Database (SDDb)."""

    dataset = "SDDb"

    def load(self) -> List[DreamSourceRecord]:
        table = self._read_table()
        records: List[DreamSourceRecord] = []

        for _, row in table.iterrows():
            metadata = DreamSourceMetadata(
                dataset=self.dataset,
                source=row.get("source") or "sddb",
                gender=row.get("gender"),
                age=row.get("age"),
                date=row.get("date"),
                locale=row.get("locale") or "en",
            )
            records.append(
                DreamSourceRecord(
                    dream_text=row.get("dream_text", ""),
                    metadata=metadata,
                    provenance=self._build_provenance(loader="SDDBConnector", record_count=table.shape[0]),
                )
            )

        return records


class DreamBankConnector(BaseConnector):
    """Connector for DreamBank datasets."""

    dataset = "DreamBank"

    def load(self) -> List[DreamSourceRecord]:
        table = self._read_table()
        records: List[DreamSourceRecord] = []

        for _, row in table.iterrows():
            metadata = DreamSourceMetadata(
                dataset=self.dataset,
                source=row.get("series") or "dreambank",
                gender=row.get("gender"),
                age=row.get("age"),
                date=row.get("date"),
                locale=row.get("locale") or "en",
            )
            records.append(
                DreamSourceRecord(
                    dream_text=row.get("dream_text", ""),
                    metadata=metadata,
                    provenance=self._build_provenance(loader="DreamBankConnector", record_count=table.shape[0]),
                )
            )

        return records


class DREAMSConnector(BaseConnector):
    """Connector for DREAMS polysomnography datasets (EDF)."""

    dataset = "DREAMS"

    def load_edf(self, sleep_stage: Optional[str] = None, participant_id: Optional[str] = None) -> List[PhysiologicalEvent]:
        raw = mne.io.read_raw_edf(self.path_info.uri, preload=False, verbose="ERROR")
        duration_seconds = raw.n_times / float(raw.info["sfreq"]) if raw.info.get("sfreq") else None

        return [
            PhysiologicalEvent(
                participant_id=participant_id,
                sleep_stage=sleep_stage or "unspecified",
                channel_names=list(raw.ch_names),
                sampling_rate=float(raw.info.get("sfreq", 0.0)),
                start_time=raw.info.get("meas_date"),
                duration_seconds=duration_seconds,
                notes="EDF recording ingested for correlation",
                provenance=self._build_provenance(loader="DREAMSConnector", record_count=1),
            )
        ]


class DREAMConnector(BaseConnector):
    """Connector for DREAM EEG datasets linking physiology to narratives."""

    dataset = "DREAM"

    def load_bundle(
        self,
        dream_text: str,
        sleep_stage: Optional[str] = None,
        participant_id: Optional[str] = None,
    ) -> DreamSourceRecord:
        metadata = DreamSourceMetadata(
            dataset=self.dataset,
            source="dream-study",
            gender=None,
            age=None,
            date=None,
            locale="en",
            sleep_stage=sleep_stage,
            participant_id=participant_id,
        )
        return DreamSourceRecord(
            dream_text=dream_text,
            metadata=metadata,
            provenance=self._build_provenance(loader="DREAMConnector", record_count=1),
        )

    def load_edf_events(
        self,
        sleep_stage: Optional[str] = None,
        participant_id: Optional[str] = None,
    ) -> Sequence[PhysiologicalEvent]:
        raw = mne.io.read_raw_edf(self.path_info.uri, preload=False, verbose="ERROR")
        duration_seconds = raw.n_times / float(raw.info["sfreq"]) if raw.info.get("sfreq") else None
        return [
            PhysiologicalEvent(
                participant_id=participant_id,
                sleep_stage=sleep_stage or "unspecified",
                channel_names=list(raw.ch_names),
                sampling_rate=float(raw.info.get("sfreq", 0.0)),
                start_time=raw.info.get("meas_date"),
                duration_seconds=duration_seconds,
                notes="EDF recording ingested for correlation",
                provenance=self._build_provenance(loader="DREAMConnector", record_count=1),
            )
        ]


def load_from_connectors(connectors: Iterable[BaseConnector]) -> List[DreamSourceRecord]:
    """Load dream narratives from all connectors while preserving provenance."""

    records: List[DreamSourceRecord] = []
    for connector in connectors:
        if isinstance(connector, (SDDBConnector, DreamBankConnector)):
            records.extend(connector.load())
    return records

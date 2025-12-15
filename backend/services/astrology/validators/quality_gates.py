"""Quality gates for deterministic and LLM layers."""

from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, List

NUMERIC_PATTERN = re.compile(r"-?\d+\.\d+|-?\d+")


class QualityReport(dict):
    def add_error(self, code: str) -> None:
        self.setdefault("errors", []).append(code)

    def add_warning(self, code: str) -> None:
        self.setdefault("warnings", []).append(code)

    @property
    def passed(self) -> bool:
        return not self.get("errors")


def validate_longitudes(items: Iterable[float], report: QualityReport) -> None:
    for value in items:
        if not (0 <= value < 360):
            report.add_error("LONGITUDE_RANGE")


def validate_speeds(items: Iterable[float], report: QualityReport) -> None:
    for value in items:
        if not math.isfinite(value):
            report.add_error("NON_FINITE_SPEED")


def validate_houses(cusps: Any, birth_time_present: bool, report: QualityReport) -> None:
    if not birth_time_present:
        if cusps is not None:
            report.add_error("HOUSES_SHOULD_BE_NONE")
        else:
            report.add_warning("HOUSES_NOT_COMPUTED_NO_BIRTHTIME")
        return
    if cusps is None:
        report.add_error("HOUSES_MISSING")
        return
    if len(cusps) != 12:
        report.add_error("HOUSES_COUNT_INVALID")
    else:
        for earlier, later in zip(cusps, cusps[1:]):
            if later.degree <= earlier.degree:
                report.add_error("HOUSE_ORDERING")
                break


def validate_geodata(coords: Dict[str, float], coords_source: str, geocoder: Dict[str, Any] | None, report: QualityReport) -> None:
    lat = coords.get("lat")
    lon = coords.get("lon")
    if lat is None or lon is None or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        report.add_error("COORD_RANGE")
    if coords_source == "geocoder":
        if not geocoder or not geocoder.get("provider"):
            report.add_error("GEOCODER_METADATA_MISSING")


def detect_numeric_hallucination(text: str, computed_json: Dict[str, Any]) -> list[str]:
    allowed_numbers = set(map(str, _extract_numbers_from_json(computed_json)))
    hallucinations: List[str] = []
    for match in NUMERIC_PATTERN.findall(text):
        if match not in allowed_numbers:
            hallucinations.append(match)
    return hallucinations


def _extract_numbers_from_json(data: Any) -> List[str]:
    numbers: List[str] = []
    if isinstance(data, dict):
        for value in data.values():
            numbers.extend(_extract_numbers_from_json(value))
    elif isinstance(data, list):
        for value in data:
            numbers.extend(_extract_numbers_from_json(value))
    elif isinstance(data, (int, float)):
        numbers.append(str(data))
    return numbers


def enforce_llm_output_claims(output: Dict[str, Any], report: QualityReport) -> None:
    claims = output.get("claims", [])
    for claim in claims:
        if not claim.get("rule_id"):
            report.add_error("MISSING_RULE_ID")


__all__ = [
    "QualityReport",
    "validate_longitudes",
    "validate_speeds",
    "validate_houses",
    "validate_geodata",
    "detect_numeric_hallucination",
    "enforce_llm_output_claims",
]

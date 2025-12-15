"""LLM interpretation layer with strict provenance and rule enforcement."""

from __future__ import annotations

from typing import Any, Dict

from .validators.quality_gates import QualityReport, detect_numeric_hallucination, enforce_llm_output_claims


def interpret(computed_json: Dict[str, Any], kb: Dict[str, Any], llm_output: Dict[str, Any]) -> tuple[Dict[str, Any], QualityReport]:
    report = QualityReport()
    enforce_llm_output_claims(llm_output, report)
    hallucinations = detect_numeric_hallucination(str(llm_output), computed_json)
    if hallucinations:
        report.add_error("LLM_NUMERIC_HALLUCINATION")
    return llm_output, report

"""Cost tracker tests (memory backend, no Redis)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.core import cost_tracker


@pytest.fixture(autouse=True)
def _isolate():
    cost_tracker.reset_memory()
    yield
    cost_tracker.reset_memory()


def test_record_single_call_aggregates_in_report():
    today = date.today()
    cost_tracker.record(
        provider="groq",
        input_tokens=1000,
        output_tokens=500,
        cost_per_1k_tokens=0.0,
        when=today,
    )

    rows = cost_tracker.report(today, today)
    assert len(rows) == 1
    row = rows[0]
    assert row.provider == "groq"
    assert row.calls == 1
    assert row.input_tokens == 1000
    assert row.output_tokens == 500
    assert row.usd == 0.0


def test_record_multiple_calls_accumulate():
    today = date.today()
    for _ in range(3):
        cost_tracker.record(
            provider="gemini",
            input_tokens=2000,
            output_tokens=1000,
            cost_per_1k_tokens=0.000075,
            when=today,
        )

    rows = cost_tracker.report(today, today, provider="gemini")
    assert len(rows) == 1
    row = rows[0]
    assert row.calls == 3
    assert row.input_tokens == 6000
    assert row.output_tokens == 3000
    # 3 calls × 3000 total_tokens × $0.000075/1k = $0.000675
    assert row.usd == pytest.approx(0.000675, rel=1e-3)


def test_report_filters_by_provider():
    today = date.today()
    cost_tracker.record("groq", 100, 50, 0.0, when=today)
    cost_tracker.record("openai", 200, 100, 0.00015, when=today)

    only_openai = cost_tracker.report(today, today, provider="openai")
    assert len(only_openai) == 1
    assert only_openai[0].provider == "openai"

    all_rows = cost_tracker.report(today, today)
    assert {r.provider for r in all_rows} == {"groq", "openai"}


def test_report_spans_multiple_days():
    d1 = date.today() - timedelta(days=2)
    d2 = date.today() - timedelta(days=1)
    cost_tracker.record("groq", 100, 50, 0.0, when=d1)
    cost_tracker.record("groq", 200, 100, 0.0, when=d2)

    rows = cost_tracker.report(d1, d2, provider="groq")
    assert rows[0].calls == 2
    assert rows[0].input_tokens == 300


def test_report_excludes_days_outside_range():
    inside = date.today() - timedelta(days=1)
    outside = date.today() - timedelta(days=10)
    cost_tracker.record("groq", 100, 50, 0.0, when=inside)
    cost_tracker.record("groq", 999, 999, 0.0, when=outside)

    rows = cost_tracker.report(inside, inside, provider="groq")
    assert rows[0].input_tokens == 100


def test_report_end_before_start_raises():
    with pytest.raises(ValueError):
        cost_tracker.report(date.today(), date.today() - timedelta(days=1))


def test_record_never_raises_on_bad_input():
    # Bad provider name still records (downstream concern).
    # Negative tokens just go to the counter — no validation by design.
    cost_tracker.record("unknown", -5, 0, 0.0)  # must not raise

"""Physiognomy service tests: deterministic metrics, KB-backed
readings, disclaimer/provenance guarantees, questionnaire fallback."""

import math

import pytest

from backend.services.physiognomy import (
    FaceMetrics,
    FeatureAnswers,
    PhysiognomyRequest,
    PhysiognomyService,
)
from backend.services.physiognomy.geometry import (
    ALA_L, ALA_R, BROW_L, BROW_R, CHEEK_L, CHEEK_R, CHIN,
    EYE_L_IN, EYE_L_OUT, EYE_R_IN, EYE_R_OUT, FOREHEAD_TOP,
    JAW_L, JAW_R, LIP_BOTTOM, LIP_BOTTOM_OUT, LIP_TOP, LIP_TOP_OUT,
    MOUTH_L, MOUTH_R, NOSE_BASE,
    metrics_from_landmarks,
)

SVC = PhysiognomyService()

# Forbidden deterministic wording (project-wide rule).
FORBIDDEN = ["будет", "случится", "definitely", "точно предск"]


def synthetic_landmarks() -> list[list[float]]:
    """A stylized wide 'earth' face: 200px wide, 250px tall."""
    pts = [[100.0, 125.0] for _ in range(468)]
    pts[FOREHEAD_TOP] = [100.0, 0.0]
    pts[CHIN] = [100.0, 250.0]
    pts[CHEEK_L], pts[CHEEK_R] = [0.0, 110.0], [200.0, 110.0]
    pts[JAW_L], pts[JAW_R] = [4.0, 180.0], [196.0, 180.0]
    pts[BROW_L], pts[BROW_R] = [60.0, 80.0], [140.0, 80.0]
    pts[EYE_L_OUT], pts[EYE_L_IN] = [40.0, 100.0], [72.0, 100.0]
    pts[EYE_R_IN], pts[EYE_R_OUT] = [128.0, 100.0], [160.0, 100.0]
    pts[NOSE_BASE] = [100.0, 160.0]
    pts[ALA_L], pts[ALA_R] = [70.0, 155.0], [130.0, 155.0]
    pts[LIP_TOP], pts[LIP_BOTTOM] = [100.0, 195.0], [100.0, 210.0]
    return pts


def test_metrics_match_manual_computation():
    m = metrics_from_landmarks(synthetic_landmarks())
    assert math.isclose(m.width_length, 200.0 / 250.0, abs_tol=1e-6)
    assert math.isclose(m.jaw_cheek, 192.0 / 200.0, abs_tol=1e-6)
    # courts: 80 / 80 / 90 of 250
    assert math.isclose(m.upper_court, 80.0 / 250.0, abs_tol=1e-6)
    assert math.isclose(m.lower_court, 90.0 / 250.0, abs_tol=1e-6)
    # eye width 32, inner-canthal 56
    assert math.isclose(m.eye_spacing, 56.0 / 32.0, abs_tol=1e-6)


def test_landmarks_too_few_rejected():
    with pytest.raises(ValueError):
        metrics_from_landmarks([[0.0, 0.0]] * 10)


def test_rotated_face_rejected_by_yaw_gate():
    pts = synthetic_landmarks()
    # Simulate yaw: right eye foreshortened to half width.
    pts[EYE_R_OUT] = [144.0, 100.0]  # was 160 → eye width 32→16
    with pytest.raises(ValueError, match="rotated"):
        metrics_from_landmarks(pts)


def test_degenerate_landmarks_rejected_not_crash():
    # All points identical → zero face height/width must raise ValueError,
    # not ZeroDivisionError (API maps ValueError → 422).
    with pytest.raises(ValueError, match="Degenerate"):
        metrics_from_landmarks([[5.0, 5.0]] * 468)


def test_mcp_report_rejects_path_traversal():
    import asyncio

    from backend.mcp.tools.physiognomy import physiognomy_report

    with pytest.raises(ValueError, match="output_path must stay under"):
        asyncio.run(physiognomy_report(
            landmarks=synthetic_landmarks(),
            output_path="/etc/oneiro_pwned.html",
        ))


def test_mcp_analyze_requires_some_input():
    import asyncio

    from backend.mcp.tools.physiognomy import analyze_face

    with pytest.raises(ValueError, match="at least one"):
        asyncio.run(analyze_face())


def test_mcp_photo_path_confined_to_allowed_roots():
    import asyncio

    from backend.mcp.tools.physiognomy import analyze_face

    with pytest.raises(ValueError, match="photo_path must stay under"):
        asyncio.run(analyze_face(photo_path="/etc/passwd"))


def test_safe_roots_drops_filesystem_anchor():
    from pathlib import Path

    from backend.mcp.tools.physiognomy import _safe_roots

    # A root equal to '/' would let every absolute path pass — must be
    # dropped even if a deployment starts the server with cwd='/'.
    assert _safe_roots(Path("/")) == ()
    kept = _safe_roots(Path("/"), Path("/tmp"))
    assert Path("/tmp") in kept and Path("/") not in kept


def test_empty_output_path_falls_back_to_default(tmp_path):
    import asyncio

    from backend.mcp.tools.physiognomy import physiognomy_report

    res = asyncio.run(physiognomy_report(
        landmarks=synthetic_landmarks(), output_path="",
    ))
    # Empty string means "default": a unique temp file, not cwd.
    import tempfile
    from pathlib import Path

    from backend.mcp.tools._files import _REPORTS_DIR

    p = Path(res["report_path"]).resolve()
    tmp_root = Path(tempfile.gettempdir()).resolve()
    # Default lands in tempdir — or in reports/ when the environment's
    # tempdir resolves to the fs anchor (the hardened fallback).
    assert p.is_relative_to(tmp_root) or p.is_relative_to(_REPORTS_DIR)
    assert p.is_file() and p.suffix == ".html"
    assert "physiognomy_report_" in p.name


def test_default_path_falls_back_when_tempdir_is_anchor(monkeypatch):
    import tempfile as tf

    from backend.mcp.tools import _files

    # Pathological TMPDIR=/ must divert defaults into reports/,
    # never into the filesystem root.
    monkeypatch.setattr(tf, "gettempdir", lambda: "/")
    p = _files._safe_report_path("", "probe")
    assert p.is_relative_to(_files._REPORTS_DIR)


def test_relative_paths_anchor_to_reports_dir():
    from backend.mcp.tools._files import _REPORTS_DIR
    from backend.mcp.tools.physiognomy import _safe_report_path

    # Relative report paths must not depend on runtime cwd and must
    # land inside the dedicated reports dir.
    assert _safe_report_path("r.html").is_relative_to(_REPORTS_DIR)


def test_project_source_tree_not_writable_via_output_path():
    from backend.mcp.tools._files import _PROJECT_ROOT
    from backend.mcp.tools.physiognomy import _safe_report_path

    # The repo tree outside reports/ must be off-limits: otherwise an
    # HTTP caller gets a write primitive over source files.
    with pytest.raises(ValueError, match="must stay under"):
        _safe_report_path(str(_PROJECT_ROOT / "backend" / "evil.html"))


def test_non_html_output_rejected(tmp_path):
    from backend.mcp.tools.physiognomy import _safe_report_path

    with pytest.raises(ValueError, match="must end with .html"):
        _safe_report_path(str(tmp_path / "report.py"))


def test_html_report_file_via_mcp_tool(tmp_path):
    import asyncio

    from backend.mcp.tools.physiognomy import physiognomy_report

    out = tmp_path / "r.html"
    res = asyncio.run(physiognomy_report(
        landmarks=synthetic_landmarks(), output_path=str(out),
    ))
    assert res["report_path"] == str(out)
    html = out.read_text(encoding="utf-8")
    assert "не валидирована" in html          # disclaimer present
    assert "Shen Xiang Quan Bian" in html      # sources rendered
    assert res["primary_element"] == "earth"


def test_report_has_narrative_then_theses_layers():
    from backend.services.physiognomy.report import (
        compose_narrative,
        compose_theses,
        render_html,
    )

    resp = SVC.analyze(PhysiognomyRequest(landmarks=synthetic_landmarks()))
    paras = compose_narrative(resp, "ru")
    theses = compose_theses(resp, "ru")
    # Narrative weaves multiple readings into flowing paragraphs...
    assert len(paras) >= 3
    assert any("Основной тип лица" in p for p in paras)
    # ...theses are the compact memorization layer.
    assert any(x.startswith("Тип:") for x in theses)
    html = render_html(resp, locale="ru")
    # Order in the report: full portrait BEFORE the takeaways,
    # takeaways before the raw data.
    assert html.index("Портрет — развёрнуто") < html.index("Тезисы для запоминания")
    assert html.index("Тезисы для запоминания") < html.index("Измерения")


def test_horoscope_report_renderer_two_layers():
    from datetime import date, datetime
    from uuid import uuid4

    from backend.services.astrology.horoscope_report import render_horoscope_html
    from backend.services.astrology.schemas import (
        HoroscopePeriod,
        HoroscopeResponse,
    )

    resp = HoroscopeResponse(
        id=uuid4(), period=HoroscopePeriod.DAILY,
        period_start=date(2026, 7, 5), period_end=date(2026, 7, 5),
        transits=[], retrograde_planets=[],
        lunar_phase="waxing_gibbous", lunar_phase_display="Растущая Луна",
        lunar_day=12,
        summary="Развёрнутый текст дня.\nВторой абзац разбора.",
        love_and_relationships="Про отношения подробно.",
        career_and_finance="Про дело подробно.",
        recommendations=["Тезис один", "Тезис два"],
        created_at=datetime(2026, 7, 5, 12, 0),
    )
    html = render_horoscope_html(resp, locale="ru")
    assert html.index("Полный разбор") < html.index("Тезисы для запоминания")
    assert "Развёрнутый текст дня." in html
    assert "Тезис один" in html
    assert "Растущая Луна" in html
    assert "Рефлексивно-развлекательный" in html  # disclaimer


def test_wide_strong_jaw_classifies_earth():
    resp = SVC.analyze(PhysiognomyRequest(landmarks=synthetic_landmarks()))
    assert resp.primary_element == "earth"
    assert resp.metrics is not None
    assert resp.dominant_court in {"upper", "middle", "lower"}


def test_long_narrow_face_classifies_wood():
    m = FaceMetrics(
        width_length=0.60, fwhr=1.6, jaw_cheek=0.78, eye_spacing=1.0,
        upper_court=0.36, middle_court=0.34, lower_court=0.30,
    )
    resp = SVC.analyze(PhysiognomyRequest(metrics=m))
    assert resp.primary_element == "wood"


def test_every_reading_has_source_and_tradition_confidence():
    resp = SVC.analyze(PhysiognomyRequest(landmarks=synthetic_landmarks()))
    assert resp.readings
    for r in resp.readings:
        assert r.source, f"reading without source: {r.topic}"
        assert r.confidence == 0.6


def test_disclaimer_and_no_deterministic_language():
    resp = SVC.analyze(PhysiognomyRequest(landmarks=synthetic_landmarks()))
    assert "не валидирована" in resp.disclaimer
    joined = " ".join(r.text.lower() for r in resp.readings)
    for word in FORBIDDEN:
        assert word not in joined


def test_questionnaire_only_mode():
    answers = FeatureAnswers(
        face_shape="square", eye_spacing="wide", heavy_eyelid=True,
        steady_gaze=True, jaw_wide=True, forehead_high=False,
    )
    resp = SVC.analyze(PhysiognomyRequest(features=answers, locale="en"))
    assert resp.metrics is None
    topics = {r.topic for r in resp.readings}
    assert "five_elements.earth" in topics
    assert "features.eyelid_heavy" in topics
    assert "features.gaze_steady" in topics
    assert "scientifically validated" in resp.disclaimer


def test_features_supplement_metrics_without_duplication():
    answers = FeatureAnswers(heavy_eyelid=True, jaw_wide=True)
    resp = SVC.analyze(PhysiognomyRequest(
        landmarks=synthetic_landmarks(), features=answers,
    ))
    topics = [r.topic for r in resp.readings]
    # unmeasurable trait added from questionnaire
    assert "features.eyelid_heavy" in topics
    # measurable jaw comes from geometry only — no duplicate entries
    assert topics.count("features.jaw_wide") == 1


def _lips(pts, outer_up, inner_up, inner_lo, outer_lo, width=60.0):
    """Wire a mouth into the synthetic face: closed or open by gap."""
    pts[MOUTH_L], pts[MOUTH_R] = [100.0 - width / 2, 202.0], [100.0 + width / 2, 202.0]
    pts[LIP_TOP_OUT], pts[LIP_TOP] = [100.0, outer_up], [100.0, inner_up]
    pts[LIP_BOTTOM], pts[LIP_BOTTOM_OUT] = [100.0, inner_lo], [100.0, outer_lo]
    return pts


def test_thin_vermilion_reads_mouth_thin():
    # Closed mouth (gap 1px / 60px width), vermilion 6+7 → 13/60 ≈ 0.217.
    pts = _lips(synthetic_landmarks(), 196.0, 202.0, 203.0, 210.0)
    m = metrics_from_landmarks(pts)
    assert m.lip_thickness == pytest.approx(13.0 / 60.0, abs=1e-3)
    resp = SVC.analyze(PhysiognomyRequest(landmarks=pts))
    assert "features.mouth_thin" in {r.topic for r in resp.readings}


def test_full_vermilion_reads_mouth_full():
    # Vermilion 14+15 → 29/60 ≈ 0.483 ≥ 0.40.
    pts = _lips(synthetic_landmarks(), 188.0, 202.0, 203.0, 218.0)
    resp = SVC.analyze(PhysiognomyRequest(landmarks=pts))
    assert "features.mouth_full" in {r.topic for r in resp.readings}


def test_open_mouth_yields_no_thickness_and_no_reading():
    # Gap 15px / 60px = 0.25 > 0.06 — expression, not anatomy.
    pts = _lips(synthetic_landmarks(), 190.0, 195.0, 210.0, 215.0)
    m = metrics_from_landmarks(pts)
    assert m.lip_thickness is None
    resp = SVC.analyze(PhysiognomyRequest(landmarks=pts))
    topics = {r.topic for r in resp.readings}
    assert not {"features.mouth_thin", "features.mouth_full"} & topics


def test_geometry_mouth_wins_over_questionnaire():
    # When a closed-mouth frame measured the lips, the questionnaire
    # answer must not duplicate/contradict the geometric reading.
    pts = _lips(synthetic_landmarks(), 196.0, 202.0, 203.0, 210.0)
    resp = SVC.analyze(PhysiognomyRequest(
        landmarks=pts, features=FeatureAnswers(lip_fullness="full"),
    ))
    topics = [r.topic for r in resp.readings]
    assert topics.count("features.mouth_thin") == 1
    assert "features.mouth_full" not in topics


def test_mouth_answers_survive_mixed_mode():
    """Geometry no longer reads the mouth (openness ≠ thickness), so
    questionnaire mouth answers must pass through even when metrics
    are present — otherwise mouth traits become unreachable."""
    answers = FeatureAnswers(lip_fullness="thin")
    resp = SVC.analyze(PhysiognomyRequest(
        landmarks=synthetic_landmarks(), features=answers,
    ))
    topics = {r.topic for r in resp.readings}
    assert "features.mouth_thin" in topics


def _child_metrics() -> FaceMetrics:
    # Rounder child frame: wide, soft-jawed → pyknic per the frame rules.
    return FaceMetrics(
        width_length=0.91, fwhr=1.55, jaw_cheek=0.87, eye_spacing=1.23,
        upper_court=0.19, middle_court=0.44, lower_court=0.37,
    )


def _adult_metrics() -> FaceMetrics:
    # Same person grown: face elongated, jaw defined → athletic.
    return FaceMetrics(
        width_length=0.84, fwhr=1.67, jaw_cheek=0.91, eye_spacing=1.23,
        upper_court=0.19, middle_court=0.41, lower_court=0.40,
    )


def test_longitudinal_diffs_stable_and_changed_topics():
    from backend.services.physiognomy.longitudinal import compare_periods

    res = compare_periods([_child_metrics()], [_adult_metrics()], "ru")
    stable = {r["topic"] for r in res["stable"]}
    appeared = {r["topic"] for r in res["appeared"]}
    disappeared = {r["topic"] for r in res["disappeared"]}
    # Wide-set eyes survive the years between the periods...
    assert "features.eyes_wide_set" in stable
    # ...while the constitution frame shifts pyknic → athletic.
    assert "kretschmer.athletic" in appeared
    assert "kretschmer.pyknic" in disappeared
    assert res["metric_deltas"]["jaw_cheek"] == pytest.approx(0.04, abs=1e-6)
    # Adult-anthropometry caveat + disclaimer always travel with the diff.
    assert "антропометрия" in res["note"]
    assert "не валидирована" in res["disclaimer"]


def test_longitudinal_median_ignores_missing_optionals():
    from backend.services.physiognomy.longitudinal import median_metrics

    a, b = _adult_metrics(), _adult_metrics().model_copy(
        update={"lip_thickness": 0.28})
    med = median_metrics([a, b])
    assert med.lip_thickness == 0.28  # only the frame that has it counts
    assert med.nose_width is None


def test_mcp_timeline_from_metric_dicts():
    import asyncio

    from backend.mcp.tools.physiognomy import physiognomy_timeline

    res = asyncio.run(physiognomy_timeline(
        early_metrics=[_child_metrics().model_dump()],
        later_metrics=[_adult_metrics().model_dump()],
    ))
    assert res["frames_used"] == {"early": 1, "later": 1}
    assert res["later"]["primary_element"] == "earth"
    assert res["skipped"] == {"early": [], "later": []}


def test_mcp_timeline_requires_frames_per_period():
    import asyncio

    from backend.mcp.tools.physiognomy import physiognomy_timeline

    with pytest.raises(ValueError, match="early"):
        asyncio.run(physiognomy_timeline(
            later_metrics=[_adult_metrics().model_dump()],
        ))


def test_aggregate_support_and_stability():
    from backend.services.physiognomy.aggregate import analyze_frames

    # Two consistent adult frames + one child outlier: earth must hold
    # the consensus, stability must flag the drifting width ratio.
    frames = [_adult_metrics(), _adult_metrics(), _child_metrics()]
    res = analyze_frames(frames)
    assert res["frames_used"] == 3
    assert res["primary_element"] == "earth"
    assert res["element_consensus"]["earth"] >= 2
    by_topic = {r["topic"]: r for r in res["readings"]}
    # Wide-set eyes hold in every frame → full support.
    assert by_topic["features.eyes_wide_set"]["support"] == "3/3"
    assert res["stability"]["eye_spacing"]["stable"] is True
    assert res["stability"]["width_length"]["spread"] == pytest.approx(0.07, abs=1e-6)
    # Coverage map always states the honest limits.
    assert "нечитаемо" in res["coverage"]["unreadable"]
    assert "не валидирована" in res["disclaimer"]


def test_aggregate_questionnaire_supplements_without_support():
    from backend.services.physiognomy.aggregate import analyze_frames

    res = analyze_frames(
        [_adult_metrics()], features=FeatureAnswers(heavy_eyelid=True),
    )
    by_topic = {r["topic"]: r for r in res["readings"]}
    # Questionnaire reading present, but no frame support claimed.
    assert "support" not in by_topic["features.eyelid_heavy"]


def test_mcp_archive_from_metric_dicts():
    import asyncio

    from backend.mcp.tools.physiognomy import analyze_face_archive

    res = asyncio.run(analyze_face_archive(
        metrics_list=[_adult_metrics().model_dump()],
    ))
    assert res["primary_element"] == "earth"
    assert res["skipped"] == []


def test_methods_lists_sources_and_status():
    m = PhysiognomyService.methods()
    ids = {s["id"] for s in m["systems"]}
    assert ids == {"mianxiang", "western"}
    for s in m["systems"]:
        assert s["meta"]["sources"]
        assert "scientific_status" in s["meta"]
    assert m["confidence"]["interpretations"] == 0.6

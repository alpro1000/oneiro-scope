import json

from backend.services.astrology.natal_formatter import format_natal_chart


SAMPLE_DATA = {
    "name": "Анна",
    "date": "1990-12-21",
    "time": "12:00",
    "place": "Москва, Россия",
    "positions": {
        "sun": {"sign": "Sagittarius", "degree": 29, "house": 1},
        "moon": {"sign": "Leo", "degree": 14, "house": 9},
        "ascendant": {"sign": "Sagittarius", "degree": 5},
        "mercury": {"sign": "Sagittarius", "degree": 10, "house": 3},
        "venus": {"sign": "Leo", "degree": 7, "house": 9},
        "mars": {"sign": "Capricorn", "degree": 18, "house": 1},
    },
    "aspects": [
        {"planet1": "sun", "planet2": "moon", "type": "trine", "orb": 3.0},
        {"planet1": "mercury", "planet2": "neptune", "type": "square", "orb": 2.1},
    ],
}


def test_format_natal_chart_markdown_ru():
    report = format_natal_chart(SAMPLE_DATA)

    assert "# 🜚 НАТАЛЬНАЯ КАРТА" in report
    assert "Солнце в Стрелец" in report or "Солнце в Стрелце" in report
    assert "## 🔭 Аспекты" in report
    assert "орб 3.0°" in report


def test_format_natal_chart_json_output():
    payload = {**SAMPLE_DATA, "output_format": "json", "locale": "en"}
    report = format_natal_chart(payload)
    data = json.loads(report)

    assert data["title"] == "# 🜚 NATAL CHART"
    assert any("Sun" in entry for entry in data["core"])
    assert data["identity"][0][1] == "Анна"

#!/usr/bin/env python3
"""Test lunar day calculation for different timezones"""

import sys
sys.path.insert(0, '/home/user/oneiro-scope')

from backend.services.lunar.engine import compute_lunar

# Сегодня: 17 декабря 2025
date = "2025-12-17"

locations = [
    ("UTC", "UTC"),
    ("Москва", "Europe/Moscow"),      # UTC+3
    ("Прага", "Europe/Prague"),       # UTC+1
    ("Нью-Йорк", "America/New_York"), # UTC-5
    ("Токио", "Asia/Tokyo"),          # UTC+9
]

print("=" * 80)
print(f"ЛУННЫЙ ДЕНЬ для {date} в разных локациях")
print("=" * 80)
print("")

results = []
for name, tz in locations:
    result = compute_lunar(date, tz)
    results.append((name, tz, result))
    print(f"{name:15} (UTC{result.provenance['local_noon_utc'][11:16]}):  День {result.lunar_day:2d}  |  {result.phase_key:20s}  |  {result.moon_sign}")

print("")
print("=" * 80)

# Проверим уникальность
lunar_days = [r[2].lunar_day for r in results]
unique_days = set(lunar_days)

if len(unique_days) == 1:
    print(f"✅ Все локации показывают одинаковый лунный день: {lunar_days[0]}")
else:
    print(f"⚠️  РАСХОЖДЕНИЕ! Разные локации показывают разные дни: {sorted(unique_days)}")
    print("")
    print("Это происходит потому что:")
    print("1. Лунный день вычисляется на момент LOCAL NOON (12:00 по местному времени)")
    print("2. В разных timezone это разные моменты UTC")
    print("3. Если граница лунного дня проходит между этими моментами → разные результаты")

print("=" * 80)
print("")

# Проверим 18 декабря
print("Проверим следующий день:")
date2 = "2025-12-18"
for name, tz in locations[:3]:  # только первые 3 для краткости
    result = compute_lunar(date2, tz)
    print(f"{date2} {name:15}: День {result.lunar_day}")

print("")
print("=" * 80)
print("ВЫВОД:")
print("=" * 80)
print("")
print("Лунный день МОЖЕТ отличаться в зависимости от:")
print("1. Timezone (часовой пояс)")
print("2. Метода расчета (от полудня vs от восхода Солнца)")
print("3. Длительности конкретного лунного дня (не ровно 24 часа)")
print("")
print("РЕКОМЕНДАЦИЯ:")
print("- Выбрать ОДНУ референсную локацию (например, Москва для RU)")
print("- Документировать: 'Календарь приведен для московского времени'")
print("- Или добавить выбор timezone для пользователя")
print("")

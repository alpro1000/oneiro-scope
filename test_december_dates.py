#!/usr/bin/env python3
"""Test lunar calculation for multiple dates in December 2025"""

import sys
sys.path.insert(0, '/home/user/oneiro-scope')

from backend.services.lunar.engine import compute_lunar

dates = [
    "2025-12-01",
    "2025-12-05",
    "2025-12-10",
    "2025-12-15",
    "2025-12-17",  # Today - should be day 27
    "2025-12-20",
    "2025-12-25",
    "2025-12-30",
]

print("=" * 80)
print("LUNAR CALENDAR - December 2025")
print("=" * 80)

lunar_days = []
for date in dates:
    result = compute_lunar(date, "UTC")
    lunar_days.append(result.lunar_day)
    print(f"{date}: Day {result.lunar_day:2d} | {result.phase_key:20s} | Age: {result.moon_age_days:5.2f} days | {result.moon_sign}")

print("=" * 80)
print(f"\nUnique lunar days: {len(set(lunar_days))} out of {len(dates)} dates")
print(f"Lunar days: {sorted(set(lunar_days))}")

if len(set(lunar_days)) == len(dates):
    print("✅ PASS: All dates have different lunar days!")
else:
    print("⚠️  WARNING: Some dates share the same lunar day (expected within month)")

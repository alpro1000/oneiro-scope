#!/usr/bin/env python3
"""Test lunar calculation for specific date: 2025-12-17"""

import sys
sys.path.insert(0, '/home/user/oneiro-scope')

from backend.services.lunar.engine import compute_lunar

# Test today's date
date = "2025-12-17"
result = compute_lunar(date, "UTC")

print("=" * 80)
print(f"DATE: {date}")
print("=" * 80)
print(f"Lunar Day:        {result.lunar_day}")
print(f"Phase:            {result.phase_key}")
print(f"Moon Age:         {result.moon_age_days:.2f} days")
print(f"Phase Angle:      {result.phase_angle:.2f}°")
print(f"Illumination:     {result.illumination * 100:.1f}%")
print(f"Moon Sign:        {result.moon_sign}")
print(f"Sun Longitude:    {result.sun_longitude:.2f}°")
print(f"Moon Longitude:   {result.moon_longitude:.2f}°")
print(f"JD (UTC):         {result.jd_ut:.2f}")
print("=" * 80)

print("\nREAL DATA (according to user):")
print("Lunar Day:        27")
print("Phase:            Waning Crescent (close to New Moon)")
print("Moon Sign:        Scorpio → Sagittarius")
print("=" * 80)

print("\nDISCREPANCY:")
print(f"Day difference:   {27 - result.lunar_day} days off")
print(f"Phase mismatch:   {result.phase_key} vs 'waning_crescent'")

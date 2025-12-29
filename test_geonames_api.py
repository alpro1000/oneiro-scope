#!/usr/bin/env python3
"""
Test GeoNames API with real credentials.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Load .env file
env_file = Path(__file__).parent / "backend" / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

from utils.geonames_resolver import geonames_search_cities, GEONAMES_USER


async def test_real_api():
    """Test GeoNames API with real credentials."""

    print("=" * 70)
    print("TESTING GEONAMES API - REAL CONNECTION")
    print("=" * 70)
    print()

    # Check configuration
    print("Configuration:")
    print(f"  Username: {GEONAMES_USER}")
    print(f"  Status: {'✅ CONFIGURED' if GEONAMES_USER else '❌ NOT SET'}")
    print()

    if not GEONAMES_USER:
        print("⚠️  No username configured! Using fallback only.")
        print()

    # Test queries
    test_cases = [
        ("Berli", "en", "Test small German city (API should return results)"),
        ("Tokyo", "en", "Test Japanese city"),
        ("Санкт", "ru", "Test Russian city with Cyrillic"),
        ("Влад", "ru", "Test small Russian city (not in fallback DB)"),
    ]

    for query, locale, description in test_cases:
        print("─" * 70)
        print(f"Test: {description}")
        print(f"Query: '{query}' (locale: {locale})")
        print("─" * 70)

        try:
            results = await geonames_search_cities(query, max_results=5)

            if results:
                print(f"✓ Found {len(results)} cities:")
                for i, city in enumerate(results, 1):
                    source = "🌍 GeoNames API" if city.get('geoname_id') else "💾 Fallback DB"
                    print(f"  {i}. {city['display']} {source}")
                    print(f"     Coordinates: ({city['lat']:.4f}, {city['lon']:.4f})")
                    if city.get('geoname_id'):
                        print(f"     GeoNames ID: {city['geoname_id']}")
            else:
                print("✗ No cities found")
        except Exception as e:
            print(f"✗ Error: {type(e).__name__}: {e}")

        print()

    print("=" * 70)
    print("TEST COMPLETED")
    print("=" * 70)
    print()
    print("Legend:")
    print("  🌍 = Data from GeoNames API (real-time)")
    print("  💾 = Data from fallback database (90+ popular cities)")
    print()


if __name__ == "__main__":
    asyncio.run(test_real_api())

#!/usr/bin/env python3
"""
Test script for city autocomplete endpoint.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from utils.geonames_resolver import geonames_search_cities


async def test_autocomplete():
    """Test city autocomplete functionality."""

    print("=" * 60)
    print("TESTING CITY AUTOCOMPLETE")
    print("=" * 60)

    test_queries = [
        ("Моск", "ru"),  # Moscow in Russian
        ("Par", "en"),   # Paris
        ("New", "en"),   # New York
        ("Лонд", "ru"),  # London in Russian
        ("xyz123", "en"), # Should fail
    ]

    for query, locale in test_queries:
        print(f"\n{'─' * 60}")
        print(f"Query: '{query}' (locale: {locale})")
        print(f"{'─' * 60}")

        try:
            results = await geonames_search_cities(query, max_results=5)

            if results:
                print(f"✓ Found {len(results)} cities:")
                for i, city in enumerate(results, 1):
                    print(f"  {i}. {city['display']}")
                    print(f"     Coordinates: ({city['lat']:.4f}, {city['lon']:.4f})")
                    if city.get('geoname_id'):
                        print(f"     GeoNames ID: {city['geoname_id']}")
            else:
                print("✗ No cities found")

        except Exception as e:
            print(f"✗ Error: {type(e).__name__}: {e}")

    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_autocomplete())

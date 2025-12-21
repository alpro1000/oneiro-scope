#!/usr/bin/env python3
"""Test GeoNames environment configuration"""

import os
import sys

import pytest

sys.path.insert(0, '/home/user/oneiro-scope')

# Load .env file
from dotenv import load_dotenv
load_dotenv('/home/user/oneiro-scope/backend/.env')

print("=" * 60)
print("GeoNames Environment Check")
print("=" * 60)

username = os.getenv('GEONAMES_USERNAME')
lang = os.getenv('GEONAMES_LANG')

if not username or username in {"your_geonames_username", "demo"}:
    pytest.skip(
        "GeoNames integration test requires real credentials; skipping in test environment.",
        allow_module_level=True,
    )

print(f"\n✓ GEONAMES_USERNAME: {username}")
print(f"✓ GEONAMES_LANG: {lang}\n")

if username == 'your_geonames_username':
    print("⚠️  WARNING: Вы не изменили GEONAMES_USERNAME!")
    print("   Пожалуйста, замените на ваш реальный username с GeoNames.org")
    print("")
    sys.exit(1)

if username == 'demo':
    print("⚠️  WARNING: Используется 'demo' username!")
    print("   Demo имеет ограниченную квоту (20k запросов/час на всех).")
    print("   Рекомендуется зарегистрировать свой бесплатный аккаунт.")
    print("")

print("=" * 60)
print("✅ Конфигурация GeoNames выглядит правильно!")
print("=" * 60)
print("")
print("Следующий шаг: Тест реального запроса...")
print("")

# Test actual GeoNames API call
import asyncio
from backend.utils.geonames_resolver import geonames_lookup

async def test_api():
    try:
        print("Тестируем запрос: 'Москва'...")
        result = await geonames_lookup("Москва")
        print(f"✅ SUCCESS! Resolved: {result['resolved_name']}, {result['country']}")
        print(f"   Coordinates: {result['lat']:.2f}, {result['lon']:.2f}")
        print("")
        return True
    except ValueError as e:
        print(f"❌ FAILED: {e}")
        print("")
        print("Возможные причины:")
        print("1. Web Services не активированы (см. Шаг 1.5 выше)")
        print("2. Неправильный username")
        print("3. GeoNames API недоступен")
        print("")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

success = asyncio.run(test_api())

if success:
    print("=" * 60)
    print("🎉 ВСЁ РАБОТАЕТ! GeoNames API настроен правильно.")
    print("=" * 60)
else:
    sys.exit(1)

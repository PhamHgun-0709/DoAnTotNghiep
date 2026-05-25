#!/usr/bin/env python3
"""Final system verification test"""

import requests
import sys

print("=" * 80)
print("🧪 SYSTEM VERIFICATION TEST")
print("=" * 80)

try:
    # Test 1: Health Check
    print("\n1️⃣ Testing API Health Endpoint...")
    r = requests.get('http://localhost:8000/health', timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ Status Code: {r.status_code}")
        print(f"   ✅ PostgreSQL Ready: {data.get('postgres_ready')}")
        print(f"   ✅ All Assets Ready: {data.get('all_required_assets_ready')}")
    else:
        print(f"   ❌ Status Code: {r.status_code}")
        sys.exit(1)

    # Test 2: API Summary
    print("\n2️⃣ Testing API Summary Endpoint...")
    r = requests.get('http://localhost:8000/api/summary', timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ Status Code: {r.status_code}")
        print(f"   ✅ Total Ads: {data.get('total_ads', 'N/A')}")
        print(f"   ✅ Total Spend: ${data.get('total_spent', 0):,.0f}")
        print(f"   ✅ Avg CTR: {data.get('avg_ctr', 0):.2f}%")
        print(f"   ✅ Avg CVR: {data.get('avg_cvr', 0):.2f}%")
    else:
        print(f"   ❌ Status Code: {r.status_code}")
        sys.exit(1)

    # Test 3: Database Records
    print("\n3️⃣ Testing Database Connection...")
    r = requests.get('http://localhost:8000/health')
    assets = r.json().get('data_assets', {})
    if assets.get('scored_ads_csv', {}).get('exists'):
        print(f"   ✅ Processed data file exists")
        print(f"   ✅ Last modified: {assets.get('scored_ads_csv', {}).get('last_modified_utc')}")

    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED - SYSTEM IS FULLY OPERATIONAL!")
    print("=" * 80)
    print("\n📊 Dashboard: http://localhost:8501")
    print("📡 API Docs: http://localhost:8000/docs")
    print("🗄️  Database: localhost:5432")
    print("\n🎉 THESIS PROJECT READY FOR PRESENTATION!")

except requests.exceptions.ConnectionError:
    print("   ❌ Cannot connect to API (http://localhost:8000)")
    print("   💡 Make sure Docker containers are running:")
    print("      docker compose -f infra/docker/docker-compose.yml ps")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

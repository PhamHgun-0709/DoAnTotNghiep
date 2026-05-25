"""
Load 1M advertising dataset into PostgreSQL
"""

import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime
import os

print("🚀 Loading 1M advertising dataset into PostgreSQL...\n")

# Database configuration (matches docker-compose)
DB_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg://{os.getenv('DB_USER', 'postgres')}:{os.getenv('DB_PASSWORD', '')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'ad_analytics')}"
)

print(f"📂 Reading CSV file...")
df = pd.read_csv("data/data_100_campaigns_high_cvr.csv")
print(f"   ✅ {len(df):,} rows loaded")

# Convert date column
print(f"\n🔄 Processing data...")
df['date'] = pd.to_datetime(df['date'])

# Create engine
print(f"📡 Connecting to PostgreSQL...")
engine = create_engine(DB_URL)

# Check connection
try:
    with engine.connect() as conn:
        print(f"   ✅ Connected to database: ad_analytics")
except Exception as e:
    print(f"   ❌ Connection failed: {e}")
    print(f"\n💡 Make sure:")
    print(f"   1. Docker containers are running: docker-up.ps1")
    print(f"   2. PostgreSQL is ready: docker ps")
    exit(1)

# Create table and load data
print(f"\n💾 Loading data into PostgreSQL...")
try:
    df.to_sql(
        'ads_campaigns',
        engine,
        if_exists='replace',  # Replace existing table
        index=False,
        chunksize=5000,
        method='multi'
    )
    print(f"   ✅ Data loaded successfully!")
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

# Verify
print(f"\n✅ VERIFICATION:")
with engine.connect() as conn:
    result = conn.execute("SELECT COUNT(*) as count FROM ads_campaigns")
    count = result.fetchone()[0]
    print(f"   Total records in database: {count:,}")
    
    result = conn.execute("""
        SELECT 
            COUNT(DISTINCT campaign_id) as campaigns,
            COUNT(DISTINCT age_group) as age_groups,
            COUNT(DISTINCT platform) as platforms
        FROM ads_campaigns
    """)
    campaigns, age_groups, platforms = result.fetchone()
    print(f"   Campaigns: {campaigns}")
    print(f"   Age groups: {age_groups}")
    print(f"   Platforms: {platforms}")

print(f"\n" + "="*80)
print(f"✨ Dataset ready for analysis!")
print(f"="*80)
print(f"\n📊 Sample queries to run in API dashboard:\n")
print(f"   GET http://localhost:8000/api/summary")
print(f"   GET http://localhost:8000/api/charts/quality-distribution")
print(f"   GET http://localhost:8000/api/charts/age-kpi")

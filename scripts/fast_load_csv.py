"""
Fast method to load CSV into PostgreSQL using COPY command
"""

import psycopg2
from psycopg2 import sql
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "ad_analytics")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

CSV_FILE = "data/data_100_campaigns_high_cvr.csv"

print("🚀 Loading CSV into PostgreSQL using COPY command (FAST METHOD)...\n")

# Connect to database
print("📡 Connecting to PostgreSQL...")
try:
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    print("✅ Connected to database: ad_analytics\n")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\n💡 Make sure:")
    print(f"   1. Docker containers are running")
    print(f"   2. PostgreSQL is ready on port 5432")
    exit(1)

try:
    # Drop existing table if exists
    print("🔄 Preparing table...")
    cursor.execute("DROP TABLE IF EXISTS ads_campaigns CASCADE;")
    
    # Create table
    cursor.execute("""
        CREATE TABLE ads_campaigns (
            ad_id INTEGER PRIMARY KEY,
            campaign_id INTEGER,
            date DATE,
            platform VARCHAR(50),
            age_group VARCHAR(10),
            impressions INTEGER,
            clicks INTEGER,
            conversions INTEGER,
            spend DECIMAL(15, 2),
            revenue DECIMAL(15, 2)
        );
    """)
    print("✅ Table created\n")
    
    # Use COPY to load CSV
    print("💾 Loading CSV file with COPY command...")
    csv_path = os.path.abspath(CSV_FILE)
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Skip header
        header = f.readline()
        print(f"   Header: {header.strip()}")
        
        # Copy data
        cursor.copy_from(
            f,
            'ads_campaigns',
            sep=',',
            columns=['ad_id', 'campaign_id', 'date', 'platform', 'age_group',
                'impressions', 'clicks', 'conversions', 'spend', 'revenue']
        )
    
    # Create indexes
    print("   Creating indexes...")
    cursor.execute("CREATE INDEX idx_campaign_id ON ads_campaigns(campaign_id);")
    cursor.execute("CREATE INDEX idx_date ON ads_campaigns(date);")
    cursor.execute("CREATE INDEX idx_platform ON ads_campaigns(platform);")
    cursor.execute("CREATE INDEX idx_age_group ON ads_campaigns(age_group);")
    
    # Commit
    conn.commit()
    print("✅ Data loaded successfully!\n")
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM ads_campaigns;")
    count = cursor.fetchone()[0]
    print(f"📊 VERIFICATION:")
    print(f"   Total records: {count:,}")
    
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT campaign_id) as campaigns,
            COUNT(DISTINCT age_group) as age_groups,
            COUNT(DISTINCT platform) as platforms
        FROM ads_campaigns
    """)
    campaigns, age_groups, platforms = cursor.fetchone()
    print(f"   Campaigns: {campaigns}")
    print(f"   Age groups: {age_groups}")
    print(f"   Platforms: {platforms}")
    
    print(f"\n✅ DATASET READY FOR ANALYSIS!")
    print(f"   📍 Location: data/data_100_campaigns_high_cvr.csv")
    print(f"   📊 Database: ads_campaigns table in ad_analytics")
    
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
    exit(1)
finally:
    cursor.close()
    conn.close()

print(f"\n🌐 Access dashboard: http://localhost:8501")
print(f"📡 API: http://localhost:8000/docs")

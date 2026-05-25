"""
Generate the canonical demo dataset for the thesis project.
Đề tài: "Phân tích và tối ưu hóa chiến dịch quảng cáo sử dụng Apache Spark"
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

print("🚀 Generating canonical advertising campaign records...")

# Configuration
NUM_RECORDS = 100
OUTPUT_FILE = "data/data_100_campaigns_high_cvr.csv"

# Random seeds for reproducibility
np.random.seed(42)
random.seed(42)

# Define choices for categorical fields
platforms = ["Facebook", "Google Ads", "TikTok", "Instagram", "LinkedIn", "Programmatic"]
age_groups = ["13-17", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"]

# Generate base data
print(f"  📊 Generating {NUM_RECORDS:,} records...")

data = {
    "ad_id": range(1, NUM_RECORDS + 1),
    "campaign_id": np.random.randint(1000, 2000, NUM_RECORDS),
    "date": [
        (datetime(2025, 1, 1) + timedelta(days=int(x))).strftime("%Y-%m-%d")
        for x in np.random.uniform(0, 365, NUM_RECORDS)
    ],
    "platform": np.random.choice(platforms, NUM_RECORDS),
    "age_group": np.random.choice(age_groups, NUM_RECORDS),
}

# Generate engagement metrics with realistic correlations
print("  📈 Generating engagement metrics...")

impressions = np.random.exponential(scale=10000, size=NUM_RECORDS).astype(int) + 100
clicks = np.minimum(
    (impressions * np.random.beta(2, 20, NUM_RECORDS)).astype(int),
    impressions
)
conversions = np.minimum(
    (clicks * np.random.beta(2, 25, NUM_RECORDS)).astype(int),
    clicks
)

data["impressions"] = impressions
data["clicks"] = clicks
data["conversions"] = conversions

# Generate spend with correlation to impressions
print("  💰 Generating spend and revenue...")
data["spend"] = (impressions * np.random.uniform(0.001, 0.01, NUM_RECORDS)).round(2)

# Revenue: typically 10-50% of spend for profitable campaigns, 0-10% for others
revenue_multiplier = np.where(
    np.random.random(NUM_RECORDS) > 0.3,  # 70% profitable campaigns
    np.random.uniform(0.15, 0.5, NUM_RECORDS),  # ROI: 15-50%
    np.random.uniform(0, 0.1, NUM_RECORDS),  # ROI: 0-10%
)
data["revenue"] = (data["spend"] * revenue_multiplier * (1 + conversions / (clicks + 1))).round(2)

# Create DataFrame
df = pd.DataFrame(data)

# Reorder columns
columns_order = [
    "ad_id", "campaign_id", "date", "platform", "age_group",
    "impressions", "clicks", "conversions", "spend", "revenue"
]
df = df[columns_order]

# Display statistics
print("\n" + "="*80)
print("📋 DATASET SUMMARY")
print("="*80)
print(f"Total records: {len(df):,}")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")
print(f"Campaigns: {df['campaign_id'].nunique()}")
print(f"Platforms: {df['platform'].nunique()}")
print(f"Age groups: {df['age_group'].nunique()}")
print(f"\n📊 Key Metrics:")
print(f"  Total Impressions: {df['impressions'].sum():,.0f}")
print(f"  Total Clicks: {df['clicks'].sum():,.0f}")
print(f"  Total Conversions: {df['conversions'].sum():,.0f}")
print(f"  Total Spend: ${df['spend'].sum():,.2f}")
print(f"  Total Revenue: ${df['revenue'].sum():,.2f}")
print(f"  Avg CTR: {(df['clicks'].sum() / df['impressions'].sum() * 100):.2f}%")
print(f"  Avg CVR: {(df['conversions'].sum() / df['clicks'].sum() * 100):.2f}%")
print(f"  Avg ROI: {((df['revenue'].sum() - df['spend'].sum()) / df['spend'].sum() * 100):.2f}%")
print("\n" + "="*80)

# Save to CSV
print(f"\n💾 Saving to {OUTPUT_FILE}...")
df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
print(f"✅ Dataset saved successfully!")

# Display sample
print(f"\n📄 Sample data (first 10 rows):")
print(df.head(10).to_string(index=False))

print("\n" + "="*80)
print("✨ Data generation completed!")
print(f"File size: {pd.io.common.get_filepath_or_buffer(OUTPUT_FILE)[0]}")
import os
file_size = os.path.getsize(OUTPUT_FILE)
print(f"File size: {file_size / (1024*1024):.2f} MB")

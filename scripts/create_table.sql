-- Create table for advertising campaigns
CREATE TABLE IF NOT EXISTS ads_campaigns (
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

-- Create indexes for faster queries
CREATE INDEX idx_campaign_id ON ads_campaigns(campaign_id);
CREATE INDEX idx_date ON ads_campaigns(date);
CREATE INDEX idx_platform ON ads_campaigns(platform);
CREATE INDEX idx_age_group ON ads_campaigns(age_group);

"""
KPI calculation and advanced analytics service.
Handles CPM, ROI, and other advanced metrics.
"""

from __future__ import annotations

from typing import Any
import numpy as np


def calculate_cpm(spend: float, impressions: float) -> float:
    """
    Calculate Cost Per Mille (CPM).
    CPM = (Spend / Impressions) × 1000
    
    Args:
        spend: Total spend in currency units
        impressions: Total impressions
        
    Returns:
        CPM value (default 0 if impressions is 0)
    """
    if impressions <= 0:
        return 0.0
    return round((spend / impressions) * 1000, 2)


def calculate_roi(revenue: float, spend: float) -> float:
    """
    Calculate Return on Investment (ROI).
    ROI = (Revenue - Spend) / Spend × 100%
    
    Args:
        revenue: Total revenue generated
        spend: Total spend in currency units
        
    Returns:
        ROI percentage (default 0 if spend is 0)
    """
    if spend <= 0:
        return 0.0
    return round(((revenue - spend) / spend) * 100, 2)


def calculate_roas(revenue: float, spend: float) -> float:
    """
    Calculate Return on Ad Spend (ROAS).
    ROAS = Revenue / Spend
    
    Args:
        revenue: Total revenue generated
        spend: Total spend in currency units
        
    Returns:
        ROAS multiple (default 0 if spend is 0)
    """
    if spend <= 0:
        return 0.0
    return round(revenue / spend, 2)


def calculate_cost_per_conversion(spend: float, conversions: float) -> float:
    """
    Calculate Cost Per Conversion (CPC = Cost Per Conversion, not Click).
    
    Args:
        spend: Total spend in currency units
        conversions: Total conversions
        
    Returns:
        Cost per conversion (default 0 if conversions is 0)
    """
    if conversions <= 0:
        return 0.0
    return round(spend / conversions, 2)


def build_advanced_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Build advanced summary with all KPIs including CPM, ROAS, etc.
    Assumes revenue = conversions * avg_conversion_value (default 10).
    
    Args:
        records: List of ad performance records
        
    Returns:
        Dictionary with comprehensive KPI metrics
    """
    if not records:
        return {
            "count": 0,
            "total_spent": 0.0,
            "total_impressions": 0.0,
            "total_conversions": 0.0,
            "total_revenue": 0.0,
            "metrics": {
                "avg_ctr": 0.0,
                "avg_cpc": 0.0,
                "avg_cpm": 0.0,
                "avg_cpa": 0.0,
                "avg_roi": 0.0,
                "avg_roas": 0.0,
            },
        }
    
    count = len(records)
    spend_sum = sum(float(r.get("spend", 0)) or 0 for r in records)
    impressions_sum = sum(float(r.get("impressions", 0)) or 0 for r in records)
    conversions_sum = sum(float(r.get("conversions", 0)) or 0 for r in records)
    
    # Assume avg conversion value = 10 (configurable)
    avg_conversion_value = 10.0
    revenue_sum = conversions_sum * avg_conversion_value
    
    # Calculate averages
    ctr_values = [float(r.get("ctr", 0)) or 0 for r in records]
    cpc_values = [float(r.get("cpc", 0)) or 0 for r in records]
    cpm_values = [float(r.get("cpm", 0)) or 0 for r in records]
    cpa_values = [float(r.get("cpa", 0)) or 0 for r in records if r.get("cpa")]
    
    avg_ctr = sum(ctr_values) / count if ctr_values else 0.0
    avg_cpc = sum(cpc_values) / count if cpc_values else 0.0
    avg_cpm = sum(cpm_values) / count if cpm_values else 0.0
    avg_cpa = sum(cpa_values) / len(cpa_values) if cpa_values else 0.0
    
    avg_roi = calculate_roi(revenue_sum, spend_sum)
    avg_roas = calculate_roas(revenue_sum, spend_sum)
    
    return {
        "count": count,
        "total_spent": round(spend_sum, 2),
        "total_impressions": int(impressions_sum),
        "total_conversions": round(conversions_sum, 2),
        "total_revenue": round(revenue_sum, 2),
        "metrics": {
            "avg_ctr": round(avg_ctr, 4),
            "avg_cpc": round(avg_cpc, 2),
            "avg_cpm": round(avg_cpm, 2),
            "avg_cpa": round(avg_cpa, 2),
            "avg_roi": avg_roi,
            "avg_roas": avg_roas,
        },
    }


def identify_high_roi_campaigns(
    records: list[dict[str, Any]], 
    revenue_per_conversion: float = 10.0,
    top_n: int = 5
) -> list[dict[str, Any]]:
    """
    Identify campaigns with highest ROI potential.
    
    Args:
        records: List of ad performance records (grouped by campaign)
        revenue_per_conversion: Assumed revenue value per conversion
        top_n: Number of top campaigns to return
        
    Returns:
        List of top ROI campaigns with metrics
    """
    campaign_metrics = {}
    
    for record in records:
        campaign_id = record.get("campaign_id", "unknown")
        
        if campaign_id not in campaign_metrics:
            campaign_metrics[campaign_id] = {
                "campaign_id": campaign_id,
                "total_spent": 0.0,
                "total_conversions": 0.0,
                "count": 0,
            }
        
        campaign_metrics[campaign_id]["total_spent"] += float(record.get("spend", 0)) or 0
        campaign_metrics[campaign_id]["total_conversions"] += float(record.get("conversions", 0)) or 0
        campaign_metrics[campaign_id]["count"] += 1
    
    # Calculate ROI for each campaign
    campaigns_with_roi = []
    for campaign_id, metrics in campaign_metrics.items():
        revenue = metrics["total_conversions"] * revenue_per_conversion
        roi = calculate_roi(revenue, metrics["total_spent"])
        roas = calculate_roas(revenue, metrics["total_spent"])
        cpc = calculate_cost_per_conversion(metrics["total_spent"], metrics["total_conversions"])
        
        campaigns_with_roi.append({
            "campaign_id": campaign_id,
            "total_spent": round(metrics["total_spent"], 2),
            "total_conversions": round(metrics["total_conversions"], 2),
            "roi": roi,
            "roas": roas,
            "cost_per_conversion": cpc,
            "ad_count": metrics["count"],
        })
    
    # Sort by ROI descending and return top N
    return sorted(campaigns_with_roi, key=lambda x: x["roi"], reverse=True)[:top_n]

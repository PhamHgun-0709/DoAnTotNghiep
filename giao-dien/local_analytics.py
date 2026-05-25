from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None


def format_number(value, decimals=2):
    """Format số theo kiểu Việt đẹp"""
    if pd.isna(value) or value == 0:
        return "0"
    try:
        value = float(value)
        if value >= 1_000_000:
            return f"{value/1_000_000:.1f}M"
        elif value >= 1_000:
            return f"{value/1_000:.1f}K"
        else:
            return f"{value:,.{decimals}f}"
    except Exception:
        return str(value)


def format_percent(value):
    """Format phần trăm"""
    if pd.isna(value):
        return "0%"
    return f"{float(value):.2f}%"


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    if pd.isna(numerator):
        return 0.0
    return float(numerator) / float(denominator)


def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    cols = {c.lower(): c for c in df.columns}

    def pick(*needles: str, exclude: Tuple[str, ...] = ()) -> Optional[str]:
        for k, original in cols.items():
            if exclude and any(x in k for x in exclude):
                continue
            if any(n in k for n in needles):
                return original
        return None

    def pick_prefer(prefer: Tuple[str, ...], needles: Tuple[str, ...], exclude: Tuple[str, ...] = ()) -> Optional[str]:
        for k, original in cols.items():
            if exclude and any(x in k for x in exclude):
                continue
            if any(p in k for p in prefer):
                return original
        return pick(*needles, exclude=exclude)

    date_col = pick('date', 'day', 'datetime', 'timestamp')
    platform_col = pick('platform', 'channel', 'source')
    campaign_col = pick('campaign_id', 'campaign', 'campaignid')
    age_col = pick('age_group', 'agegroup', 'age')

    impressions_col = pick('impression')
    clicks_col = pick('click')
    conversions_col = pick_prefer(
        prefer=('total_conversion', 'conversions', 'conversion'),
        needles=('conversion',),
        exclude=('rate', 'ratio', 'cvr', '%'),
    )
    spend_col = pick('spend', 'cost', exclude=('cpc', 'cpm', 'cpa', 'per', 'rate'))
    revenue_col = pick('revenue', 'sales', 'value')

    return {
        'date': date_col,
        'platform': platform_col,
        'campaign_id': campaign_col,
        'age_group': age_col,
        'impressions': impressions_col,
        'clicks': clicks_col,
        'conversions': conversions_col,
        'spend': spend_col,
        'revenue': revenue_col,
    }


def get_trend_indicator(current, previous=None):
    """Tạo trend indicator (↑ ↓ →)"""
    if previous is None or current == previous:
        return "→ Ổn định"
    change = ((current - previous) / abs(previous)) * 100 if previous != 0 else 0
    arrow = "↑" if change > 0 else "↓"
    return f"{arrow} {abs(change):.1f}%"


def coerce_numeric_metrics_inplace(df: pd.DataFrame, cols: Dict[str, Optional[str]]) -> None:
    """Coerce core metric columns to numeric and remove invalid negatives."""
    for key in ("impressions", "clicks", "conversions", "spend", "revenue"):
        col_name = cols.get(key)
        if not col_name or col_name not in df.columns:
            continue
        s = pd.to_numeric(df[col_name], errors="coerce").fillna(0.0).astype(float)
        df[col_name] = s.clip(lower=0.0)


def convert_money_columns_to_vnd_inplace(df: pd.DataFrame, cols: Dict[str, Optional[str]]) -> None:
    """Convert spend/revenue columns to VND once, in-place.

    Assumption: incoming CSV values are USD-like amounts.
    Override rate via env USD_TO_VND. Set USD_TO_VND=1 to keep raw values.
    """
    rate = float(os.getenv("USD_TO_VND", "25000"))
    rate = max(0.0, rate)
    if rate in (0.0, 1.0):
        return
    for key in ("spend", "revenue"):
        col_name = cols.get(key)
        if not col_name or col_name not in df.columns:
            continue
        s = pd.to_numeric(df[col_name], errors="coerce").fillna(0.0).astype(float)
        df[col_name] = (s * rate).clip(lower=0.0)


def compute_kpis_from_totals(totals: Dict[str, float]) -> Dict[str, float]:
    clicks = totals.get('total_clicks', 0.0)
    impressions = totals.get('total_impressions', 0.0)
    conversions = totals.get('total_conversions', 0.0)
    spend = totals.get('total_spend', 0.0)
    revenue = totals.get('total_revenue', 0.0)

    kpis: Dict[str, float] = dict(totals)
    kpis['ctr'] = _safe_div(clicks, impressions) * 100
    kpis['cvr'] = _safe_div(conversions, clicks) * 100
    kpis['cpc'] = _safe_div(spend, clicks)
    kpis['cpm'] = _safe_div(spend, impressions) * 1000
    kpis['cpa'] = _safe_div(spend, conversions)
    kpis['roi'] = (_safe_div(revenue - spend, spend) * 100) if spend else 0.0
    kpis['roas'] = _safe_div(revenue, spend)
    return kpis


def calculate_kpis(df: pd.DataFrame) -> Dict[str, float]:
    """Tính toán KPI từ DataFrame"""
    detected = detect_columns(df)
    totals: Dict[str, float] = {}

    if detected['impressions']:
        totals['total_impressions'] = float(df[detected['impressions']].sum())
    if detected['clicks']:
        totals['total_clicks'] = float(df[detected['clicks']].sum())
    if detected['conversions']:
        totals['total_conversions'] = float(df[detected['conversions']].sum())
    if detected['spend']:
        totals['total_spend'] = float(df[detected['spend']].sum())
    if detected['revenue']:
        totals['total_revenue'] = float(df[detected['revenue']].sum())

    return compute_kpis_from_totals(totals)


def prepare_timeseries(df: pd.DataFrame, cols: Dict[str, Optional[str]]) -> Optional[pd.DataFrame]:
    if not cols.get('date'):
        return None
    date_col = cols['date']
    assert date_col is not None

    needed = [date_col]
    for k in ['impressions', 'clicks', 'conversions', 'spend', 'revenue']:
        if cols.get(k):
            needed.append(cols[k])
    tmp = df[needed].copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col], errors='coerce')
    tmp = tmp.dropna(subset=[date_col])
    if tmp.empty:
        return None

    tmp['__date'] = tmp[date_col].dt.date
    agg = {
        cols['impressions']: 'sum' if cols.get('impressions') else 'size',
        cols['clicks']: 'sum' if cols.get('clicks') else 'size',
        cols['conversions']: 'sum' if cols.get('conversions') else 'size',
        cols['spend']: 'sum' if cols.get('spend') else 'size',
        cols['revenue']: 'sum' if cols.get('revenue') else 'size',
    }
    agg = {k: v for k, v in agg.items() if k is not None}

    daily = tmp.groupby('__date', as_index=False).agg(agg).sort_values('__date')
    daily = daily.rename(columns={
        cols.get('impressions') or '': 'impressions',
        cols.get('clicks') or '': 'clicks',
        cols.get('conversions') or '': 'conversions',
        cols.get('spend') or '': 'spend',
        cols.get('revenue') or '': 'revenue',
    })
    for c in ['impressions', 'clicks', 'conversions', 'spend', 'revenue']:
        if c in daily.columns:
            daily[c] = daily[c].fillna(0)

    daily['ctr'] = daily.apply(lambda r: _safe_div(r.get('clicks', 0.0), r.get('impressions', 0.0)) * 100, axis=1)
    daily['cvr'] = daily.apply(lambda r: _safe_div(r.get('conversions', 0.0), r.get('clicks', 0.0)) * 100, axis=1)
    daily['roas'] = daily.apply(lambda r: _safe_div(r.get('revenue', 0.0), r.get('spend', 0.0)), axis=1)
    daily['roi'] = daily.apply(lambda r: (_safe_div(r.get('revenue', 0.0) - r.get('spend', 0.0), r.get('spend', 0.0)) * 100) if r.get('spend', 0.0) else 0.0, axis=1)
    return daily


def kpi_trends_from_timeseries(daily: Optional[pd.DataFrame], window_days: int = 7) -> Dict[str, str]:
    if daily is None or daily.empty or len(daily) < window_days * 2:
        return {}
    cur = daily.tail(window_days)
    prev = daily.tail(window_days * 2).head(window_days)

    def avg(col: str) -> float:
        return float(cur[col].mean()) if col in cur.columns else 0.0

    def avg_prev(col: str) -> float:
        return float(prev[col].mean()) if col in prev.columns else 0.0

    return {
        'ctr': get_trend_indicator(avg('ctr'), avg_prev('ctr')),
        'cvr': get_trend_indicator(avg('cvr'), avg_prev('cvr')),
        'roas': get_trend_indicator(avg('roas'), avg_prev('roas')),
        'roi': get_trend_indicator(avg('roi'), avg_prev('roi')),
    }


def aggregate_performance(df: pd.DataFrame, cols: Dict[str, Optional[str]]) -> Dict[str, pd.DataFrame]:
    imp = cols.get('impressions')
    clk = cols.get('clicks')
    conv = cols.get('conversions')
    spend = cols.get('spend')
    revenue = cols.get('revenue')

    def base_agg(data: pd.DataFrame, group_col: str) -> pd.DataFrame:
        use_cols = [c for c in [imp, clk, conv, spend, revenue] if c]
        agg_map = {c: 'sum' for c in use_cols}
        view_cols = [group_col] + use_cols
        g = data[view_cols].groupby(group_col, as_index=False).agg(agg_map)
        g = g.rename(columns={
            imp or '': 'impressions',
            clk or '': 'clicks',
            conv or '': 'conversions',
            spend or '': 'spend',
            revenue or '': 'revenue',
        })
        for c in ['impressions', 'clicks', 'conversions', 'spend', 'revenue']:
            if c not in g.columns:
                g[c] = 0.0
            g[c] = g[c].fillna(0.0)
        g['ctr'] = g.apply(lambda r: _safe_div(r['clicks'], r['impressions']) * 100, axis=1)
        g['cvr'] = g.apply(lambda r: _safe_div(r['conversions'], r['clicks']) * 100, axis=1)
        g['cpa'] = g.apply(lambda r: _safe_div(r['spend'], r['conversions']), axis=1)
        g['roas'] = g.apply(lambda r: _safe_div(r['revenue'], r['spend']), axis=1)
        g['roi'] = g.apply(lambda r: (_safe_div(r['revenue'] - r['spend'], r['spend']) * 100) if r['spend'] else 0.0, axis=1)
        return g

    out: Dict[str, pd.DataFrame] = {}
    if cols.get('platform'):
        out['platform'] = base_agg(df, cols['platform'])
    if cols.get('campaign_id'):
        out['campaign'] = base_agg(df, cols['campaign_id'])
    if cols.get('age_group') and cols.get('platform'):
        segment_col = '__segment'
        keep = [cols['platform'], cols['age_group']]
        keep += [c for c in [imp, clk, conv, spend, revenue] if c]
        tmp = df[keep].copy()
        tmp[segment_col] = tmp[cols['platform']].astype(str) + ' | ' + tmp[cols['age_group']].astype(str)
        seg = base_agg(tmp, segment_col).rename(columns={segment_col: 'segment'})
        out['segment'] = seg
    return out


def budget_recommendation(platform_df: pd.DataFrame, total_spend: float) -> pd.DataFrame:
    dfp = platform_df.copy()

    def norm(s: pd.Series) -> pd.Series:
        if s.max() == s.min():
            return pd.Series(np.ones(len(s)), index=s.index)
        return (s - s.min()) / (s.max() - s.min())

    dfp['score'] = (
        0.45 * norm(dfp['roas'].clip(lower=0)) +
        0.35 * norm(dfp['roi']) +
        0.20 * norm(dfp['cvr'])
    ) - (0.25 * norm(dfp['cpa']))
    dfp['score'] = dfp['score'].clip(lower=0)
    if dfp['score'].sum() == 0:
        dfp['score'] = 1.0
    dfp['recommended_spend'] = (dfp['score'] / dfp['score'].sum()) * float(total_spend)
    dfp['delta'] = dfp['recommended_spend'] - dfp['spend']
    return dfp


def check_system_health(api_base: str) -> Dict[str, str]:
    status = {
        'api': 'UNKNOWN',
        'db': 'UNKNOWN',
        'spark': 'READY',
    }
    if requests is None:
        return status
    try:
        r = requests.get(f"{api_base.rstrip('/')}/health", timeout=2)
        if r.status_code != 200:
            status['api'] = 'OFFLINE'
            return status
        payload = r.json() if hasattr(r, 'json') else {}
        status['api'] = 'ONLINE'
        if isinstance(payload, dict):
            if payload.get('postgres_ready') is True:
                status['db'] = 'ONLINE'
            elif payload.get('postgres_ready') is False:
                status['db'] = 'DEGRADED'
            else:
                status['db'] = 'UNKNOWN'
            if payload.get('spark_ready') is True:
                status['spark'] = 'ACTIVE'
        return status
    except Exception:
        status['api'] = 'OFFLINE'
        return status


def spark_processing_panel(rows: int, file_mb: float, df: pd.DataFrame,
                           cols: Dict[str, Optional[str]], measured_sec: float) -> Dict[str, float]:
    workers = 4
    partitions = int(min(32, max(8, round(rows / 75000))))
    mem_bytes = int(df.memory_usage(deep=False).sum())
    mem_gb = mem_bytes / (1024 ** 3)
    spark_est = max(1.2, measured_sec / 3.5)
    return {
        'rows': float(rows),
        'file_mb': float(file_mb),
        'partitions': float(partitions),
        'workers': float(workers),
        'mem_gb': float(mem_gb),
        'pandas_sec': float(measured_sec),
        'spark_est_sec': float(spark_est),
    }

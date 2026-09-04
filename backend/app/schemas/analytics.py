from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ConsumerAnalyticsResponse(BaseModel):
    total_scans: int
    likely_genuine_count: int
    suspicious_count: int
    tampered_count: int
    recent_risk_scores: List[float] = []


class AdminAnalyticsResponse(BaseModel):
    total_scans: int
    total_cases: int
    open_cases: int
    verified_counterfeits: int
    quality_pass_rate_percent: float
    decision_distribution: Dict[str, int]
    common_anomaly_types: Dict[str, int]


class BrandAnalyticsResponse(BaseModel):
    brand_code: str
    brand_name: str
    total_scans: int
    active_packaging_versions: int
    counterfeit_risk_rate_percent: float
    risk_distribution: Dict[str, int]


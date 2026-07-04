from __future__ import annotations

from enum import Enum
from typing import List, Literal
from pydantic import BaseModel, Field, model_validator


class Sector(str, Enum):
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    SERVICES = "services"
    WHOLESALE = "wholesale"
    FOOD_HOSPITALITY = "food_hospitality"


class DataQuality(BaseModel):
    completeness: float = Field(ge=0, le=1)
    recency: float = Field(ge=0, le=1)
    cross_source_agreement: float = Field(ge=0, le=1)
    identity_match: float = Field(ge=0, le=1)
    anomaly_risk: float = Field(ge=0, le=1, description="1 means highest anomaly risk")


class BusinessProfile(BaseModel):
    business_id: str
    legal_name: str
    sector: Sector
    vintage_months: int = Field(ge=0, le=600)
    monthly_revenue_inr: float = Field(gt=0)
    revenue_growth_6m: float = Field(ge=-1, le=5)
    revenue_volatility: float = Field(ge=0, le=3)
    bank_inflow_gst_ratio: float = Field(ge=0, le=3)
    gst_filing_regularity: float = Field(ge=0, le=1)
    upi_share: float = Field(ge=0, le=1)
    cash_buffer_days: float = Field(ge=0, le=365)
    dscr: float = Field(ge=0, le=10)
    debt_obligation_ratio: float = Field(ge=0, le=1)
    cheque_or_emi_bounce_rate: float = Field(ge=0, le=1)
    receivable_days: float = Field(ge=0, le=365)
    payable_days: float = Field(ge=0, le=365)
    largest_buyer_share: float = Field(ge=0, le=1)
    top_5_buyer_share: float = Field(ge=0, le=1)
    bureau_score: int | None = Field(default=None, ge=300, le=900)
    requested_amount_inr: float = Field(gt=0)
    requested_tenure_months: int = Field(ge=1, le=120)
    data_quality: DataQuality

    @model_validator(mode="after")
    def concentration_is_consistent(self) -> "BusinessProfile":
        if self.top_5_buyer_share < self.largest_buyer_share:
            raise ValueError("top_5_buyer_share cannot be below largest_buyer_share")
        return self


class Driver(BaseModel):
    key: str
    label: str
    direction: Literal["positive", "negative", "neutral"]
    impact: float
    evidence: str


class CreditStructure(BaseModel):
    outcome: Literal[
        "eligible",
        "conditional_offer",
        "structured_offer",
        "additional_data_required",
        "bankability_plan",
    ]
    recommended_product: str
    safe_amount_inr: float
    recommended_tenure_months: int
    conditions: List[str]


class Assessment(BaseModel):
    assessment_id: str
    business_id: str
    financial_health_score: int
    data_confidence_score: int
    resilience_score: int
    risk_band: Literal["A", "B", "C", "D", "E"]
    decision: CreditStructure
    top_drivers: List[Driver]
    bankability_actions: List[str]
    warnings: List[str]
    model_version: str = "vp-core-0.1.0"


class ScenarioRequest(BaseModel):
    profile: BusinessProfile
    revenue_shock_pct: float = Field(default=-0.15, ge=-0.9, le=1.0)
    buyer_delay_days: int = Field(default=30, ge=0, le=180)
    proposed_amount_inr: float | None = Field(default=None, gt=0)
    proposed_tenure_months: int | None = Field(default=None, ge=1, le=120)


class ScenarioResult(BaseModel):
    baseline_score: int
    stressed_score: int
    score_change: int
    stressed_dscr: float
    stressed_cash_buffer_days: float
    recommendation: str


class ConsentGrant(BaseModel):
    consent_id: str
    business_id: str
    purposes: List[str] = Field(min_length=1)
    source_systems: List[str] = Field(min_length=1)
    granted_at: str
    expires_at: str
    status: Literal["active", "revoked", "expired"] = "active"


class AuditEvent(BaseModel):
    event_id: str
    assessment_id: str
    business_id: str
    event_type: Literal["assessment_created", "human_decision_recorded"]
    actor: str
    occurred_at: str
    model_version: str
    payload_hash: str
    reason: str | None = None


class HumanDecisionRequest(BaseModel):
    assessment_id: str
    business_id: str
    actor: str
    decision: Literal["approve", "review", "decline"]
    reason: str = Field(min_length=8, max_length=1000)

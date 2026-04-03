"""
Pydantic schemas for API request/response models.
Provides full Swagger documentation for /docs.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# ─── Enums ────────────────────────────────────────────

class SignalType(str, Enum):
    SST = "sst"
    CHLOROPHYLL = "chlorophyll"
    WIND_SPEED = "wind_speed"
    PH = "ph"
    TURBIDITY = "turbidity"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FeedbackType(str, Enum):
    VALIDATED = "validated"
    FALSE_POSITIVE = "false_positive"
    UNCERTAIN = "uncertain"


# ─── Zone Schemas ─────────────────────────────────────

class ZoneBase(BaseModel):
    id: str = Field(..., example="zone_mumbai")
    name: str = Field(..., example="Mumbai Coast")
    region: str = Field(..., example="Arabian Sea")
    lat: float = Field(..., example=19.076)
    lng: float = Field(..., example=72.8777)
    description: str = Field(..., example="Major port city coast")


class ZoneResponse(ZoneBase):
    current_sensitivity: float = Field(1.0, description="Memory Agent's adaptive sensitivity (0.3-2.0)")
    alert_count_24h: int = Field(0, description="Alerts in last 24 hours")
    anomaly_score: float = Field(0.0, description="Current aggregate anomaly score")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "zone_mumbai",
                "name": "Mumbai Coast",
                "region": "Arabian Sea",
                "lat": 19.076,
                "lng": 72.8777,
                "description": "Major port city coast",
                "current_sensitivity": 1.0,
                "alert_count_24h": 3,
                "anomaly_score": 0.72,
            }
        }


# ─── Reading Schemas ──────────────────────────────────

class ReadingResponse(BaseModel):
    timestamp: str
    zone_id: str
    sst: float = Field(..., description="Sea Surface Temperature (°C)")
    chlorophyll: float = Field(..., description="Chlorophyll-a (mg/m³)")
    wind_speed: float = Field(..., description="Wind Speed (m/s)")
    ph: float = Field(..., description="pH Level")
    turbidity: float = Field(..., description="Turbidity (NTU)")


class ReadingsListResponse(BaseModel):
    zone_id: str
    zone_name: str
    total_readings: int
    readings: list[ReadingResponse]


# ─── Anomaly Schemas ──────────────────────────────────

class AnomalyResponse(BaseModel):
    id: int
    zone_id: str
    zone_name: str
    timestamp: str
    signal: str = Field(..., description="Which signal triggered this anomaly")
    anomaly_score: float = Field(..., description="Isolation Forest anomaly score (-1=anomaly, 1=normal)")
    z_score: float = Field(..., description="Z-score of the residual")
    value: float = Field(..., description="Actual observed value")
    expected_value: float = Field(..., description="Expected baseline value")
    deviation_pct: float = Field(..., description="Percentage deviation from expected")


class AnomaliesListResponse(BaseModel):
    total: int
    anomalies: list[AnomalyResponse]


# ─── Alert Schemas ────────────────────────────────────

class AlertResponse(BaseModel):
    id: int
    zone_id: str
    zone_name: str
    timestamp: str
    severity: AlertSeverity
    priority_score: float = Field(..., description="0-1, higher = more critical")
    title: str = Field(..., example="Thermal Buildup Detected")
    description: str
    signals_involved: list[str] = Field(..., description="Which signals contributed")
    magnitude_score: float
    recency_score: float
    trajectory_score: float
    convergence_score: float
    is_suppressed: bool = Field(False, description="Whether this alert was suppressed by Decision Agent")
    feedback: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "zone_id": "zone_mumbai",
                "zone_name": "Mumbai Coast",
                "timestamp": "2026-04-01T14:00:00",
                "severity": "high",
                "priority_score": 0.85,
                "title": "Thermal Buildup Detected",
                "description": "SST has increased by 2.1°C over 8 days",
                "signals_involved": ["sst", "wind_speed"],
                "magnitude_score": 0.9,
                "recency_score": 0.8,
                "trajectory_score": 0.95,
                "convergence_score": 0.7,
                "is_suppressed": False,
                "feedback": None,
            }
        }


class AlertsListResponse(BaseModel):
    total: int
    active_alerts: int
    suppressed_alerts: int
    alerts: list[AlertResponse]


# ─── Feedback Schemas ─────────────────────────────────

class FeedbackRequest(BaseModel):
    feedback: FeedbackType = Field(..., description="Was this alert valid?")
    notes: Optional[str] = Field(None, example="Confirmed algal bloom via satellite imagery")


class FeedbackResponse(BaseModel):
    alert_id: int
    feedback: str
    zone_sensitivity_before: float
    zone_sensitivity_after: float
    message: str


# ─── Forecast Schemas ─────────────────────────────────

class ForecastPoint(BaseModel):
    timestamp: str
    predicted_value: float
    lower_bound: float = Field(..., description="Lower 95% confidence interval")
    upper_bound: float = Field(..., description="Upper 95% confidence interval")


class ForecastResponse(BaseModel):
    zone_id: str
    zone_name: str
    signal: str
    forecast_horizon_hours: int
    forecast: list[ForecastPoint]


# ─── Chat Schemas ─────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., example="What needs attention right now?")
    zone_id: Optional[str] = Field(None, description="Optional zone context")


class ChatResponse(BaseModel):
    response: str
    context_zones: list[str] = Field(..., description="Zones referenced in response")
    alerts_referenced: int = Field(0, description="Number of alerts referenced")


# ─── Briefing Schema ──────────────────────────────────

class BriefingResponse(BaseModel):
    timestamp: str
    summary: str = Field(..., description="Natural language situational briefing")
    top_alerts: list[AlertResponse]
    zones_requiring_attention: list[str]
    system_confidence: float = Field(..., description="Overall system confidence in current assessments")


# ─── System Schemas ───────────────────────────────────

class AgentStatus(BaseModel):
    name: str
    status: str = Field(..., example="operational")
    last_run: Optional[str] = None
    details: Optional[str] = None


class SystemHealthResponse(BaseModel):
    status: str = Field(..., example="operational")
    uptime_seconds: float
    total_zones: int
    total_readings: int
    total_anomalies_detected: int
    total_alerts_generated: int
    total_alerts_suppressed: int
    model_accuracy: float = Field(..., description="Based on feedback loop")
    agents: list[AgentStatus]


# ─── NASA Events ──────────────────────────────────────

class NASAEventResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    category: str
    source: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    date: str
    link: Optional[str] = None


class NASAEventsListResponse(BaseModel):
    total: int
    events: list[NASAEventResponse]


# ─── Cascade Prediction Schemas ───────────────────────

class CascadePrediction(BaseModel):
    source_zone_id: str
    source_zone_name: str
    target_zone_id: str
    target_zone_name: str
    cascade_probability: float = Field(..., description="0-1, probability of cascade reaching target zone")
    adjacency_strength: float = Field(..., description="Geographic/oceanic connectivity")
    propagation_days_min: int
    propagation_days_max: int
    cascading_signals: list[str]
    source_severity: str
    source_priority_score: float
    cascade_in_progress: bool
    mechanism: str = Field(..., description="Oceanographic mechanism of propagation")
    recommended_action: str


class CascadeResponse(BaseModel):
    total_predictions: int
    active_cascades: int
    predictions: list[CascadePrediction]


class CascadeNetworkNode(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    region: str
    own_risk: float
    incoming_cascade_risk: float
    total_risk: float


class CascadeNetworkEdge(BaseModel):
    source: str
    target: str
    strength: float
    active_cascade: bool


class CascadeNetworkResponse(BaseModel):
    nodes: list[CascadeNetworkNode]
    edges: list[CascadeNetworkEdge]
    active_cascades: int


# ─── Economic Impact Schemas ──────────────────────────

class EconomicBreakdown(BaseModel):
    total_impact_crore: float = Field(..., description="Total estimated economic impact in ₹ crore")
    fishing_impact_crore: float
    shipping_impact_crore: float
    tourism_impact_crore: float
    currency: str = "INR"
    unit: str = "crore (1 crore = 10 million)"


class SocialImpact(BaseModel):
    fishing_families_affected: int
    population_affected_lakh: float
    key_industries_at_risk: list[str]
    protected_areas_at_risk: list[str]


class EconomicImpactResponse(BaseModel):
    zone_id: str
    zone_name: str
    severity: float
    duration_days: int
    signals_analyzed: list[str]
    economic_impact: EconomicBreakdown
    social_impact: SocialImpact
    vulnerability_index: float
    impact_summary: str = Field(..., description="Human-readable impact statement")


class AllImpactsResponse(BaseModel):
    total_active_alerts: int
    total_economic_impact_crore: float
    total_families_affected: int
    impacts: list[EconomicImpactResponse]


# ─── Incident Report Schema ──────────────────────────

class IncidentReportResponse(BaseModel):
    report_id: str = Field(..., example="IR-2026-0001")
    generated_at: str
    classification: str
    header: dict
    scoring_breakdown: dict
    signals_involved: list[str]
    signal_analysis: list[dict]
    timeline: list[dict]
    economic_impact: dict
    social_impact: dict
    impact_summary: str
    system_response: dict
    recommended_actions: list[str]
    data_sources: list[str]
    disclaimer: str


# ─── Multi-Language Briefing Schema ───────────────────

class MultiLangBriefingResponse(BaseModel):
    language: str
    language_name: str
    briefing: str = Field(..., description="Briefing text in the requested language")
    alerts_count: int
    timestamp: str
    generated_by: str = Field(..., description="'gemini' or 'fallback'")


# ─── Telegram Status Schema ──────────────────────────

class TelegramStatusResponse(BaseModel):
    configured: bool
    chat_id_set: bool
    alerts_sent: int
    setup_instructions: str


# ─── What-If Simulation Schema ───────────────────────

class SimulationRequest(BaseModel):
    zone_id: str = Field(..., example="zone_mumbai")
    scenario: dict = Field(
        ...,
        example={"sst": 2.0, "chlorophyll": 1.5},
        description="Signal changes to simulate. Absolute values (e.g., sst: +2.0°C) or percentage strings (e.g., 'wind_speed': '20%')"
    )

class SimulationResponse(BaseModel):
    zone_id: str
    zone_name: str
    scenario_applied: dict
    current_state: dict
    simulated_state: dict
    baselines: dict
    deviations_from_baseline: dict
    direct_changes: dict
    cascading_effects: dict = Field(..., description="Indirect effects on other signals")
    risk_assessment: dict
    economic_impact: dict
    recommendations: list[str]


# ─── Root Cause Schema ────────────────────────────────

class RootCauseEntry(BaseModel):
    cause: str
    mechanism: str
    confidence: float

class RootCauseResponse(BaseModel):
    zone_id: str
    zone_name: str
    analysis_window: str
    deviations: dict
    anomalous_signals: list[dict]
    root_causes: list[RootCauseEntry]
    primary_cause: RootCauseEntry
    total_causes_identified: int


# ─── Agent Logs Schema ────────────────────────────────

class AgentLogEntry(BaseModel):
    timestamp: str
    agent: str
    action: str
    details: str
    zone_id: Optional[str] = None
    severity: str = "info"

class AgentLogsResponse(BaseModel):
    total_logs: int
    reasoning_chains: int
    logs: list[AgentLogEntry]
    agent_activity: dict


# ─── Pattern Memory Schema ────────────────────────────

class SimilarEvent(BaseModel):
    date: str
    days_ago: int
    similarity_score: float
    signals_involved: list[str]
    avg_severity: float
    num_anomalies: int
    outcome: str
    signals_in_common: list[str]

class PatternMemoryResponse(BaseModel):
    zone_id: str
    zone_name: str
    current_anomaly_signals: list[str]
    current_severity: float
    similar_events: list[SimilarEvent]
    insight: str


# ─── Time-to-Risk Schema ─────────────────────────────

class TimeToRiskWarning(BaseModel):
    signal: str
    current_value: float
    baseline: float
    current_deviation: float
    trend: str
    rate_per_hour: float
    rate_per_day: float
    time_to_risk_levels: dict
    human_readable: Optional[str] = None

class TimeToRiskResponse(BaseModel):
    zone_id: str
    zone_name: str
    analysis_window: str
    projection_horizon: str
    warnings: list[TimeToRiskWarning]
    summary: dict


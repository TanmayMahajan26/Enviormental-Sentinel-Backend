"""
🌍 Environmental Sentinel — FastAPI Backend
AI-Powered Geospatial Intelligence Engine for Indian Coastal Monitoring

Endpoints are fully documented at /docs (Swagger UI)

5-Agent Architecture:
🟢 Data Agent     — 90-day India coastal dataset generation
🔵 Analysis Agent — STL + Isolation Forest + Holt-Winters forecasting
🟡 Decision Agent — Multi-signal convergence scoring
🟣 Memory Agent   — Adaptive threshold self-correction
🔴 Explanation Agent — Gemini LLM briefings & chat
"""
import time
import json
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import database as db
from config import HOST, PORT, FRONTEND_DIR
from schemas import (
    ZoneResponse,
    ReadingsListResponse, ReadingResponse,
    AnomaliesListResponse, AnomalyResponse,
    AlertsListResponse, AlertResponse,
    FeedbackRequest, FeedbackResponse,
    ForecastResponse, ForecastPoint,
    ChatRequest, ChatResponse,
    BriefingResponse,
    SystemHealthResponse, AgentStatus,
    NASAEventsListResponse, NASAEventResponse,
    SignalType,
    CascadePrediction, CascadeResponse, CascadeNetworkResponse,
    EconomicImpactResponse, AllImpactsResponse,
    IncidentReportResponse,
    MultiLangBriefingResponse,
    TelegramStatusResponse,
    SimulationRequest, SimulationResponse,
    RootCauseResponse,
    AgentLogsResponse,
    PatternMemoryResponse,
    TimeToRiskResponse,
)
from agents import data_agent, analysis_agent, decision_agent, memory_agent, explanation_agent
from agents import live_data_agent
from agents import cascade_agent, impact_agent, telegram_agent
from agents import intelligence_agent
from scheduler import start_scheduler, get_scheduler_status

# ─── Track startup time ───
START_TIME = time.time()


# ─── Lifespan: Initialize on startup ───
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run initialization on startup."""
    print("=" * 60)
    print("🌍 ENVIRONMENTAL SENTINEL — Starting up...")
    print("=" * 60)

    # 1. Initialize database
    db.init_db()
    db.seed_zones()

    # 2. Generate 90-day data (Data Agent)
    data_agent.seed_readings()

    # 3. Train ML models (Analysis Agent)
    # Check if models already exist
    import os
    from config import MODELS_DIR
    model_files = []
    if os.path.exists(MODELS_DIR):
        model_files = [f for f in os.listdir(MODELS_DIR) if f.endswith(".pkl")]

    if len(model_files) < 8:
        analysis_agent.train_all_zones()
    else:
        print("[Analysis Agent] Models already trained, skipping.")

    # 4. Run Decision Agent
    decision_agent.evaluate_and_prioritize()

    # 5. Simulate Memory Agent feedback (for demo)
    memory_agent.simulate_feedback_history()

    # 6. Start background scheduler (6h ingestion + 24h retrain)
    await start_scheduler()

    # 7. Seed agent conversation logs for demo
    intelligence_agent.seed_demo_logs()

    print("\n" + "=" * 60)
    print("🌍 ENVIRONMENTAL SENTINEL — Ready!")
    print(f"📖 API Docs: http://localhost:{PORT}/docs")
    print(f"🖥️  Dashboard: http://localhost:{PORT}/")
    print(f"⏰ Live ingestion: every 6 hours | Retrain: every 24 hours")
    print(f"🧠 Agents: 9 active | Features: 10 | Endpoints: 30+")
    print("=" * 60 + "\n")

    yield  # Server is running

    print("\n🌍 Environmental Sentinel shutting down...")


# ─── FastAPI App ───
app = FastAPI(
    title="🌍 Environmental Sentinel API",
    description="""
## AI-Powered Geospatial Intelligence Engine

Smart environmental monitoring system for **8 Indian coastal zones** with a 5-agent AI architecture.

### 🔄 Live Data Pipeline
- **Every 6 hours**: Fetches real-world data from NOAA ERDDAP, Open-Meteo, OpenAQ (no API keys needed)
- **Every 24 hours**: Auto-retrains ML models on the rolling 90-day window
- **Rolling window**: Data older than 90 days is automatically pruned
- **Self-correcting**: Memory Agent adapts zone sensitivity based on operator feedback

### 🤖 Agent Architecture
| Agent | Role |
|-------|------|
| 🟢 **Data Agent** | Live ingestion from NOAA/OpenAQ/Open-Meteo + 90-day synthetic baseline |
| 🔵 **Analysis Agent** | STL Decomposition → Isolation Forest → Holt-Winters Forecasting |
| 🟡 **Decision Agent** | Multi-signal convergence scoring + alert suppression |
| 🟣 **Memory Agent** | Adaptive self-correction via operator feedback loop |
| 🔴 **Explanation Agent** | Gemini LLM briefings + context-aware chat |

### 📡 Real-Time Data Sources (ALL FREE, no keys needed)
| Source | Data | Update |
|--------|------|--------|
| NOAA ERDDAP | SST + Chlorophyll-a | Every 6h |
| Open-Meteo | Wind + Weather | Every 6h |
| OpenAQ | Air Quality (PM2.5) | Every 6h |
| NASA EONET | Natural Events | On demand |

### 📊 Monitored Signals
- **SST** — Sea Surface Temperature (°C)
- **Chlorophyll-a** — Algal concentration (mg/m³)
- **Wind Speed** — Surface wind (m/s)
- **pH** — Ocean acidity
- **Turbidity** — Water clarity (NTU)

### 🗺️ Monitored Zones
Mumbai Coast • Goa Coast • Kochi Coast • Chennai Coast • Visakhapatnam Coast • Sundarbans Delta • Gulf of Kutch • Andaman Islands
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS (allow frontend to call API) ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════
# ZONE ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/api/zones",
         response_model=list[ZoneResponse],
         tags=["🗺️ Zones"],
         summary="List all monitored zones",
         description="Returns all 8 Indian coastal monitoring zones with current sensitivity and alert stats.")
def list_zones():
    zones = db.get_all_zones()
    result = []
    for z in zones:
        sens = db.get_zone_sensitivity(z["id"])
        anomalies = db.get_anomalies(zone_id=z["id"], limit=5)
        avg_score = 0.0
        if anomalies:
            avg_score = sum(abs(a["anomaly_score"]) for a in anomalies) / len(anomalies)

        result.append(ZoneResponse(
            id=z["id"],
            name=z["name"],
            region=z["region"],
            lat=z["lat"],
            lng=z["lng"],
            description=z["description"],
            current_sensitivity=sens["sensitivity"] if sens else 1.0,
            alert_count_24h=len([
                a for a in db.get_alerts(include_suppressed=False, limit=100)
                if a["zone_id"] == z["id"]
            ]),
            anomaly_score=round(avg_score, 3),
        ))
    return result


@app.get("/api/zones/{zone_id}",
         response_model=ZoneResponse,
         tags=["🗺️ Zones"],
         summary="Get zone details",
         description="Returns detailed info for a specific zone including current sensitivity from the Memory Agent.")
def get_zone(zone_id: str):
    z = db.get_zone(zone_id)
    if not z:
        raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")

    sens = db.get_zone_sensitivity(zone_id)
    anomalies = db.get_anomalies(zone_id=zone_id, limit=5)
    avg_score = sum(abs(a["anomaly_score"]) for a in anomalies) / len(anomalies) if anomalies else 0.0

    return ZoneResponse(
        id=z["id"],
        name=z["name"],
        region=z["region"],
        lat=z["lat"],
        lng=z["lng"],
        description=z["description"],
        current_sensitivity=sens["sensitivity"] if sens else 1.0,
        alert_count_24h=len([
            a for a in db.get_alerts(include_suppressed=False, limit=100)
            if a["zone_id"] == zone_id
        ]),
        anomaly_score=round(avg_score, 3),
    )


# ═══════════════════════════════════════════════════════════
# READINGS ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/api/zones/{zone_id}/readings",
         response_model=ReadingsListResponse,
         tags=["📊 Readings"],
         summary="Get time-series readings for a zone",
         description="Returns hourly environmental sensor readings (SST, chlorophyll, wind, pH, turbidity). 90 days = 2160 data points per zone.")
def get_zone_readings(
    zone_id: str,
    limit: int = Query(default=168, description="Number of readings (default: 168 = 7 days)"),
    offset: int = Query(default=0, description="Offset for pagination"),
):
    zone = db.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")

    readings = db.get_readings(zone_id, limit=limit, offset=offset)
    total = db.get_readings_count(zone_id)

    return ReadingsListResponse(
        zone_id=zone_id,
        zone_name=zone["name"],
        total_readings=total,
        readings=[ReadingResponse(**{
            "timestamp": r["timestamp"],
            "zone_id": r["zone_id"],
            "sst": r["sst"],
            "chlorophyll": r["chlorophyll"],
            "wind_speed": r["wind_speed"],
            "ph": r["ph"],
            "turbidity": r["turbidity"],
        }) for r in readings],
    )


# ═══════════════════════════════════════════════════════════
# ANOMALY ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/api/anomalies",
         response_model=AnomaliesListResponse,
         tags=["🔍 Anomalies"],
         summary="Get detected anomalies",
         description="Returns anomalies detected by the Isolation Forest model. Each anomaly includes the signal, z-score, and deviation from expected.")
def get_anomalies(
    zone_id: str = Query(default=None, description="Filter by zone ID"),
    limit: int = Query(default=50, description="Max results"),
):
    anomalies = db.get_anomalies(zone_id=zone_id, limit=limit)

    return AnomaliesListResponse(
        total=len(anomalies),
        anomalies=[AnomalyResponse(
            id=a["id"],
            zone_id=a["zone_id"],
            zone_name=a.get("zone_name", a["zone_id"]),
            timestamp=a["timestamp"],
            signal=a["signal"],
            anomaly_score=a["anomaly_score"],
            z_score=a["z_score"],
            value=a["value"],
            expected_value=a["expected_value"],
            deviation_pct=a["deviation_pct"],
        ) for a in anomalies],
    )


# ═══════════════════════════════════════════════════════════
# ALERT ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/api/alerts",
         response_model=AlertsListResponse,
         tags=["🚨 Alerts"],
         summary="Get ranked priority alerts",
         description="Returns alerts ranked by the Decision Agent's multi-signal convergence score. Higher priority_score = needs more attention.")
def get_alerts(
    include_suppressed: bool = Query(default=False, description="Include suppressed alerts"),
    limit: int = Query(default=20, description="Max results"),
):
    alerts = db.get_alerts(include_suppressed=include_suppressed, limit=limit)
    active = [a for a in alerts if not a.get("is_suppressed")]
    suppressed_list = [a for a in alerts if a.get("is_suppressed")]

    return AlertsListResponse(
        total=len(alerts),
        active_alerts=len(active),
        suppressed_alerts=len(suppressed_list),
        alerts=[AlertResponse(
            id=a["id"],
            zone_id=a["zone_id"],
            zone_name=a.get("zone_name", a["zone_id"]),
            timestamp=a["timestamp"],
            severity=a["severity"],
            priority_score=a["priority_score"],
            title=a["title"],
            description=a.get("description", ""),
            signals_involved=json.loads(a["signals_involved"]) if isinstance(a["signals_involved"], str) else a["signals_involved"],
            magnitude_score=a["magnitude_score"],
            recency_score=a["recency_score"],
            trajectory_score=a["trajectory_score"],
            convergence_score=a["convergence_score"],
            is_suppressed=bool(a.get("is_suppressed")),
            feedback=a.get("feedback"),
        ) for a in alerts],
    )


@app.post("/api/alerts/{alert_id}/feedback",
          response_model=FeedbackResponse,
          tags=["🚨 Alerts"],
          summary="Submit feedback on an alert",
          description="Operator feedback (validated/false_positive) triggers the Memory Agent to adjust zone sensitivity. This is the adaptive learning loop.")
def submit_feedback(alert_id: int, request: FeedbackRequest):
    result = memory_agent.process_feedback(
        alert_id=alert_id,
        feedback=request.feedback.value,
        notes=request.notes,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return FeedbackResponse(
        alert_id=result["alert_id"],
        feedback=result["feedback"],
        zone_sensitivity_before=result["zone_sensitivity_before"],
        zone_sensitivity_after=result["zone_sensitivity_after"],
        message=result["message"],
    )


# ═══════════════════════════════════════════════════════════
# FORECAST ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/api/forecast/{zone_id}",
         response_model=ForecastResponse,
         tags=["📈 Forecast"],
         summary="Get probabilistic forecast",
         description="Returns Holt-Winters forecast with 95% confidence intervals for SST or Chlorophyll. Forecast horizon: 7 days (168 hours).")
def get_forecast(
    zone_id: str,
    signal: str = Query(default="sst", description="Signal to forecast (sst or chlorophyll)"),
    horizon: int = Query(default=168, description="Forecast horizon in hours"),
):
    zone = db.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")

    forecast = analysis_agent.get_forecast(zone_id, signal, horizon)
    if not forecast:
        raise HTTPException(status_code=404, detail=f"No forecast model for {zone_id}/{signal}")

    return ForecastResponse(
        zone_id=zone_id,
        zone_name=zone["name"],
        signal=signal,
        forecast_horizon_hours=horizon,
        forecast=[ForecastPoint(**f) for f in forecast],
    )


# ═══════════════════════════════════════════════════════════
# AI CHAT & BRIEFING ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.post("/api/chat",
          response_model=ChatResponse,
          tags=["🤖 AI Intelligence"],
          summary="Context-aware AI chat",
          description="Ask questions like 'What needs attention right now?' or 'Tell me about Mumbai thermal buildup'. Uses Gemini LLM with full system context.")
async def chat_endpoint(request: ChatRequest):
    result = await explanation_agent.chat(
        message=request.message,
        zone_id=request.zone_id,
    )
    return ChatResponse(**result)


@app.get("/api/briefing",
         response_model=BriefingResponse,
         tags=["🤖 AI Intelligence"],
         summary="Get situational briefing",
         description="'What needs attention right now?' — AI-generated synthesis of all active alerts, ranked by priority, with recommended actions.")
async def get_briefing():
    result = await explanation_agent.generate_briefing()

    # Convert alert dicts to AlertResponse models
    top_alerts = []
    for a in result.get("top_alerts", [])[:5]:
        try:
            signals = a.get("signals_involved", "[]")
            if isinstance(signals, str):
                signals = json.loads(signals)

            top_alerts.append(AlertResponse(
                id=a.get("id", 0),
                zone_id=a.get("zone_id", ""),
                zone_name=a.get("zone_name", a.get("zone_id", "")),
                timestamp=a.get("timestamp", ""),
                severity=a.get("severity", "low"),
                priority_score=a.get("priority_score", 0),
                title=a.get("title", ""),
                description=a.get("description", ""),
                signals_involved=signals,
                magnitude_score=a.get("magnitude_score", 0),
                recency_score=a.get("recency_score", 0),
                trajectory_score=a.get("trajectory_score", 0),
                convergence_score=a.get("convergence_score", 0),
                is_suppressed=bool(a.get("is_suppressed", False)),
                feedback=a.get("feedback"),
            ))
        except Exception:
            pass

    return BriefingResponse(
        timestamp=result["timestamp"],
        summary=result["summary"],
        top_alerts=top_alerts,
        zones_requiring_attention=result.get("zones_requiring_attention", []),
        system_confidence=result.get("system_confidence", 0.5),
    )


# ═══════════════════════════════════════════════════════════
# NASA EVENTS ENDPOINT
# ═══════════════════════════════════════════════════════════

@app.get("/api/events/nasa",
         response_model=NASAEventsListResponse,
         tags=["🛰️ External Data"],
         summary="Live NASA EONET events",
         description="Fetches real-time natural events (wildfires, cyclones, floods) from NASA EONET API v3.")
async def get_nasa_events(
    limit: int = Query(default=20, description="Max events to fetch"),
):
    events = await data_agent.fetch_nasa_eonet_events(limit=limit)

    return NASAEventsListResponse(
        total=len(events),
        events=[NASAEventResponse(**e) for e in events],
    )


# ═══════════════════════════════════════════════════════════
# LIVE DATA PIPELINE ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.post("/api/pipeline/ingest",
          tags=["📡 Live Pipeline"],
          summary="Trigger live data ingestion NOW",
          description="Manually trigger a live data fetch from all sources (NOAA ERDDAP, Open-Meteo, OpenAQ). Normally runs automatically every 6 hours.")
async def trigger_ingestion():
    result = await live_data_agent.ingest_live_data()
    return result


@app.post("/api/pipeline/retrain",
          tags=["📡 Live Pipeline"],
          summary="Trigger model retraining NOW",
          description="Manually retrain all ML models on the current rolling 90-day window. Normally runs automatically every 24 hours.")
async def trigger_retrain():
    result = await live_data_agent.retrain_models()
    return result


@app.get("/api/pipeline/status",
         tags=["📡 Live Pipeline"],
         summary="Get pipeline status",
         description="Returns the live data pipeline status: last ingestion, next scheduled run, data sources, rolling window info.")
def get_pipeline_status():
    pipeline = live_data_agent.get_pipeline_status()
    scheduler = get_scheduler_status()
    return {
        **pipeline,
        "scheduler": scheduler,
    }


# ═══════════════════════════════════════════════════════════
# MEMORY AGENT ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/api/sensitivity",
         tags=["🧠 Memory Agent"],
         summary="Get all zone sensitivities",
         description="Returns the Memory Agent's adaptive sensitivity values for each zone. Lower sensitivity = zone has many false positives.")
def get_sensitivities():
    return memory_agent.get_all_sensitivities()


# ═══════════════════════════════════════════════════════════
# FEATURE 1: CROSS-ZONE CASCADE PREDICTION
# ═══════════════════════════════════════════════════════════

@app.get("/api/cascade",
         response_model=CascadeResponse,
         tags=["🔗 Cascade Prediction"],
         summary="Predict cross-zone cascade effects",
         description="Predicts which zones will be affected NEXT based on ocean current adjacency, historical correlation, and current anomaly state. Example: 'Mumbai thermal buildup → Goa Coast likely affected in 3-5 days (78%)'")
def get_cascade_predictions(
    source_zone: str = Query(default=None, description="Filter by source zone"),
):
    predictions = cascade_agent.predict_cascade(source_zone)
    in_progress = [p for p in predictions if p["cascade_in_progress"]]
    return CascadeResponse(
        total_predictions=len(predictions),
        active_cascades=len(in_progress),
        predictions=[CascadePrediction(**p) for p in predictions],
    )


@app.get("/api/cascade/network",
         response_model=CascadeNetworkResponse,
         tags=["🔗 Cascade Prediction"],
         summary="Get zone connectivity network",
         description="Returns nodes (zones with risk scores) and edges (ocean current connections) for cascade visualization on a map.")
def get_cascade_network():
    network = cascade_agent.get_cascade_network()
    return CascadeNetworkResponse(**network)


# ═══════════════════════════════════════════════════════════
# FEATURE 2: ECONOMIC IMPACT ESTIMATION
# ═══════════════════════════════════════════════════════════

@app.get("/api/impact",
         tags=["💰 Economic Impact"],
         summary="Estimate economic impact of ALL active alerts",
         description="Converts abstract anomaly scores into ₹ crore impact figures. Maps each event to fishing revenue, shipping delays, tourism loss, and affected families.")
def get_all_impacts():
    impacts = impact_agent.estimate_all_active_impacts()
    total_crore = sum(i["economic_impact"]["total_impact_crore"] for i in impacts)
    total_families = sum(i["social_impact"]["fishing_families_affected"] for i in impacts)

    return {
        "total_active_alerts": len(impacts),
        "total_economic_impact_crore": round(total_crore, 2),
        "total_families_affected": total_families,
        "impacts": impacts,
    }


@app.get("/api/impact/{zone_id}",
         response_model=EconomicImpactResponse,
         tags=["💰 Economic Impact"],
         summary="Estimate economic impact for a specific zone",
         description="Detailed economic impact assessment for a zone including ₹ fishing revenue loss, shipping delays, tourism impact, and families affected.")
def get_zone_impact(
    zone_id: str,
    severity: float = Query(default=0.5, description="Event severity 0-1"),
    duration_days: int = Query(default=7, description="Expected duration in days"),
):
    zone = db.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")

    # Get active signals from any anomalies
    anomalies = db.get_anomalies(zone_id=zone_id, limit=10)
    signals = list(set(a["signal"] for a in anomalies)) if anomalies else ["sst"]

    result = impact_agent.estimate_impact(zone_id, signals, severity, duration_days)
    return EconomicImpactResponse(**result)


# ═══════════════════════════════════════════════════════════
# FEATURE 4: INCIDENT REPORT GENERATION
# ═══════════════════════════════════════════════════════════

@app.get("/api/incident/{alert_id}",
         response_model=IncidentReportResponse,
         tags=["📝 Incident Reports"],
         summary="Generate incident report for an alert",
         description="Auto-generates a structured incident report with timeline, economic impact, scoring breakdown, and recommended actions. Suitable for regulatory filing.")
def get_incident_report(alert_id: int):
    report = impact_agent.generate_incident_report(alert_id)
    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"])
    return IncidentReportResponse(**report)


# ═══════════════════════════════════════════════════════════
# FEATURE 5: MULTI-LANGUAGE BRIEFINGS
# ═══════════════════════════════════════════════════════════

@app.get("/api/briefing/{language}",
         response_model=MultiLangBriefingResponse,
         tags=["🌐 Multi-Language"],
         summary="Get briefing in any Indian language",
         description="Generate situational briefing in Hindi, Tamil, Marathi, Bengali, etc. Supported: english, hindi, marathi, tamil, telugu, bengali, gujarati, malayalam, kannada, odia.")
async def get_multilang_briefing(
    language: str,
    zone_id: str = Query(default=None, description="Optional: focus on specific zone"),
):
    result = await impact_agent.generate_multilang_briefing(language, zone_id)
    return MultiLangBriefingResponse(**result)


@app.get("/api/languages",
         tags=["🌐 Multi-Language"],
         summary="List supported languages",
         description="Returns all supported languages for briefings and their native script names.")
def list_languages():
    return {
        "supported_languages": impact_agent.SUPPORTED_LANGUAGES,
        "zone_default_languages": impact_agent.ZONE_LANGUAGE_MAP,
    }


# ═══════════════════════════════════════════════════════════
# FEATURE 3: TELEGRAM BOT
# ═══════════════════════════════════════════════════════════

@app.get("/api/telegram/status",
         response_model=TelegramStatusResponse,
         tags=["📱 Telegram Bot"],
         summary="Telegram bot status",
         description="Check if Telegram bot is configured. Follow setup instructions to enable real-time mobile alerts.")
def telegram_status():
    return TelegramStatusResponse(**telegram_agent.get_telegram_status())


@app.post("/api/telegram/send-alerts",
          tags=["📱 Telegram Bot"],
          summary="Push alerts to Telegram NOW",
          description="Manually trigger sending all high/critical alerts to the configured Telegram chat.")
async def telegram_send_alerts():
    result = await telegram_agent.send_priority_alerts(min_severity="high")
    return result


@app.post("/api/telegram/webhook",
          tags=["📱 Telegram Bot"],
          summary="Telegram webhook handler",
          description="Receives updates from Telegram. Set this URL as your bot's webhook.")
async def telegram_webhook(update: dict):
    chat_id = await telegram_agent.handle_telegram_update(update)
    return {"ok": True, "chat_id": chat_id}


# ═══════════════════════════════════════════════════════════
# WHAT-IF SIMULATION
# ═══════════════════════════════════════════════════════════

@app.post("/api/simulate",
          response_model=SimulationResponse,
          tags=["🧪 What-If Simulation"],
          summary="Run a what-if environmental simulation",
          description="Simulate future impact of environmental changes. Example: 'What if SST increases by 2°C and chlorophyll by 1.5 mg/m³?' Shows cascading effects, ecosystem impacts, economic damage, and action recommendations.")
def run_what_if(req: SimulationRequest):
    result = intelligence_agent.run_simulation(req.zone_id, req.scenario)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return SimulationResponse(**result)


# ═══════════════════════════════════════════════════════════
# ROOT CAUSE DETECTION
# ═══════════════════════════════════════════════════════════

@app.get("/api/rootcause/{zone_id}",
         response_model=RootCauseResponse,
         tags=["🧬 Root Cause AI"],
         summary="Detect root cause of anomalies",
         description="Not just 'Temperature is rising' but 'Likely cause: reduced wind + high solar radiation'. Uses rule-based causal patterns to identify WHY anomalies are occurring.")
def get_root_cause(zone_id: str):
    result = intelligence_agent.detect_root_cause(zone_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return RootCauseResponse(**result)


# ═══════════════════════════════════════════════════════════
# AGENT CONVERSATION LOGS
# ═══════════════════════════════════════════════════════════

@app.get("/api/agent-logs",
         response_model=AgentLogsResponse,
         tags=["🤖 Agent Logs"],
         summary="View multi-agent reasoning chain",
         description="Shows the real-time conversation between agents: Data Agent → anomaly detected → Decision Agent → priority high → Explanation Agent → generating insight. Makes the system feel ALIVE.")
def get_agent_logs(
    limit: int = Query(default=50, description="Max entries"),
    agent: str = Query(default=None, description="Filter by agent name"),
    zone_id: str = Query(default=None, description="Filter by zone"),
):
    result = intelligence_agent.get_reasoning_chain(zone_id)
    return AgentLogsResponse(**result)


# ═══════════════════════════════════════════════════════════
# PATTERN MEMORY
# ═══════════════════════════════════════════════════════════

@app.get("/api/memory/{zone_id}",
         response_model=PatternMemoryResponse,
         tags=["🧠 Pattern Memory"],
         summary="Find similar past events",
         description="Searches historical data for similar anomaly patterns. 'This looks like the event 47 days ago that turned out to be a false positive.' Provides institutional memory.")
def get_pattern_memory(zone_id: str):
    result = intelligence_agent.find_similar_events(zone_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return PatternMemoryResponse(**result)


# ═══════════════════════════════════════════════════════════
# TIME-TO-RISK EARLY WARNING
# ═══════════════════════════════════════════════════════════

@app.get("/api/time-to-risk/{zone_id}",
         response_model=TimeToRiskResponse,
         tags=["⏰ Early Warning"],
         summary="Calculate time-to-risk for each signal",
         description="Projects when each signal will reach risk thresholds based on current trends. 'SST will reach CRITICAL in ~48 hours at current rate.'")
def get_time_to_risk(zone_id: str):
    result = intelligence_agent.calculate_time_to_risk(zone_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return TimeToRiskResponse(**result)


# ═══════════════════════════════════════════════════════════
# SYSTEM HEALTH ENDPOINT
# ═══════════════════════════════════════════════════════════

@app.get("/api/system/health",
         response_model=SystemHealthResponse,
         tags=["⚙️ System"],
         summary="System health & agent status",
         description="Returns overall system health including agent statuses, data counts, and model accuracy based on feedback loop.")
def system_health():
    stats = db.get_system_stats()

    import os
    from config import MODELS_DIR
    models_trained = 0
    if os.path.exists(MODELS_DIR):
        models_trained = len([f for f in os.listdir(MODELS_DIR) if f.endswith(".pkl")])

    return SystemHealthResponse(
        status="operational",
        uptime_seconds=round(time.time() - START_TIME, 1),
        total_zones=stats["total_zones"],
        total_readings=stats["total_readings"],
        total_anomalies_detected=stats["total_anomalies"],
        total_alerts_generated=stats["total_alerts"],
        total_alerts_suppressed=stats["total_suppressed"],
        model_accuracy=stats["model_accuracy"],
        agents=[
            AgentStatus(
                name="🟢 Data Agent (Live Pipeline)",
                status="operational",
                details=f"{stats['total_readings']} readings | Ingests from NOAA/OpenAQ/Open-Meteo every 6h",
            ),
            AgentStatus(
                name="🔵 Analysis Agent",
                status="operational" if models_trained > 0 else "not_trained",
                details=f"{models_trained}/8 zone models trained, {stats['total_anomalies']} anomalies | Auto-retrain every 24h",
            ),
            AgentStatus(
                name="🟡 Decision Agent",
                status="operational",
                details=f"{stats['total_alerts']} alerts generated, {stats['total_suppressed']} suppressed",
            ),
            AgentStatus(
                name="🟣 Memory Agent",
                status="operational",
                details=f"{stats['total_feedback']} feedback entries processed",
            ),
            AgentStatus(
                name="🔴 Explanation Agent",
                status="operational" if os.getenv("GEMINI_API_KEY") else "no_api_key",
                details="Gemini LLM connected" if os.getenv("GEMINI_API_KEY") else "Running in fallback mode (set GEMINI_API_KEY)",
            ),
            AgentStatus(
                name="🔗 Cascade Agent",
                status="operational",
                details="Cross-zone cascade prediction via ocean current adjacency matrix",
            ),
            AgentStatus(
                name="💰 Impact Agent",
                status="operational",
                details="Economic impact estimation + incident reports + multi-language briefings",
            ),
            AgentStatus(
                name="📱 Telegram Agent",
                status="operational" if os.getenv("TELEGRAM_BOT_TOKEN") else "not_configured",
                details="Mobile alerts enabled" if os.getenv("TELEGRAM_BOT_TOKEN") else "Add TELEGRAM_BOT_TOKEN to .env",
            ),
            AgentStatus(
                name="⏰ Background Scheduler",
                status="operational" if get_scheduler_status()['running'] else "stopped",
                details=f"Ingestion: every 6h | Retrain: every 24h | Runs: {get_scheduler_status().get('ingestion_count', 0)}",
            ),
        ],
    )


# ═══════════════════════════════════════════════════════════
# SERVE FRONTEND (Static Files)
# ═══════════════════════════════════════════════════════════

import os
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", tags=["🖥️ Frontend"])
    def serve_frontend():
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Frontend not built yet. Use /docs for API documentation."}


# ═══════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)

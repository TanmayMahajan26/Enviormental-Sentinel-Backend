"""
🧠 INTELLIGENCE AGENT — Advanced Cognitive Features
Combines 5 high-impact capabilities:

1. What-If Simulation — "What if pollution increases 20%?"
2. Root Cause Detection — "Likely cause: reduced wind + high solar"
3. Agent Conversation Logs — Shows the multi-agent reasoning chain
4. Pattern Memory — "Similar event occurred 47 days ago"
5. Time-to-Risk Early Warning — "High risk expected in 48 hours"
"""
import json
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Optional
import database as db


# ═══════════════════════════════════════════════════════════
# 1. WHAT-IF SIMULATION ENGINE
# ═══════════════════════════════════════════════════════════

# Impact coefficients: how a % change in one signal affects others
SIGNAL_INTERACTIONS = {
    "sst": {
        "chlorophyll": 0.6,    # Warmer water → algal growth
        "ph": -0.3,           # Warmer → slightly more acidic
        "turbidity": 0.2,     # Thermal mixing
        "wind_speed": 0.0,    # SST doesn't affect wind
    },
    "chlorophyll": {
        "ph": -0.4,           # Blooms consume CO2 → pH changes
        "turbidity": 0.5,     # Blooms increase turbidity
        "sst": 0.05,          # Minimal effect
        "wind_speed": 0.0,
    },
    "wind_speed": {
        "sst": -0.15,         # Wind cooling
        "chlorophyll": 0.1,    # Wind mixing brings nutrients
        "turbidity": 0.35,    # Wind stirs sediment
        "ph": 0.0,
    },
    "ph": {
        "chlorophyll": -0.2,  # Acidification stresses algae
        "sst": 0.0,
        "wind_speed": 0.0,
        "turbidity": 0.0,
    },
    "turbidity": {
        "chlorophyll": -0.15, # High turbidity blocks light
        "sst": 0.0,
        "ph": -0.05,
        "wind_speed": 0.0,
    },
}

# Risk thresholds (absolute values that trigger concern)
RISK_THRESHOLDS = {
    "sst": {"low": 1.0, "medium": 2.0, "high": 3.5, "critical": 5.0},
    "chlorophyll": {"low": 0.5, "medium": 1.5, "high": 3.0, "critical": 6.0},
    "wind_speed": {"low": 2.0, "medium": 5.0, "high": 10.0, "critical": 15.0},
    "ph": {"low": 0.1, "medium": 0.3, "high": 0.5, "critical": 0.8},
    "turbidity": {"low": 5.0, "medium": 15.0, "high": 30.0, "critical": 50.0},
}

# Ecosystem impact descriptions
ECOSYSTEM_IMPACTS = {
    "coral_bleaching": {
        "trigger": lambda sst_dev, ph_dev: sst_dev > 2.0 or ph_dev < -0.3,
        "description": "Coral bleaching risk: elevated SST and/or acidification stress coral symbiotic algae",
        "affected": "Coral reefs, reef fish, tourism industry",
        "severity": "HIGH",
    },
    "harmful_algal_bloom": {
        "trigger": lambda chl_dev, sst_dev: chl_dev > 2.0 and sst_dev > 0.5,
        "description": "Harmful Algal Bloom (HAB) risk: nutrient enrichment in warm waters",
        "affected": "Fisheries, shellfish, coastal communities, water treatment",
        "severity": "HIGH",
    },
    "hypoxia": {
        "trigger": lambda chl_dev, turb_dev: chl_dev > 3.0 or turb_dev > 20.0,
        "description": "Hypoxic dead zone risk: excessive organic matter decomposition depletes dissolved oxygen",
        "affected": "Bottom-dwelling species, shrimp, crab populations",
        "severity": "CRITICAL",
    },
    "fish_migration": {
        "trigger": lambda sst_dev, wind_dev: abs(sst_dev) > 1.5 or wind_dev > 5.0,
        "description": "Fish migration disruption: temperature and current changes alter feeding grounds",
        "affected": "Fishing industry, food security, marine biodiversity",
        "severity": "MEDIUM",
    },
    "maritime_hazard": {
        "trigger": lambda wind_dev, turb_dev: wind_dev > 8.0 or turb_dev > 25.0,
        "description": "Maritime navigation hazard: high winds and low visibility",
        "affected": "Shipping, fishing vessels, coastal infrastructure",
        "severity": "HIGH",
    },
    "health_emergency": {
        "trigger": lambda sst_dev, chl_dev: sst_dev > 3.0 and chl_dev > 2.0,
        "description": "Coastal health emergency: heat + algal toxins in water and air",
        "affected": "Coastal population, beach-goers, water supply",
        "severity": "CRITICAL",
    },
}


def run_simulation(zone_id: str, scenario: dict) -> dict:
    """
    Run a what-if simulation for a zone.

    Args:
        zone_id: The zone to simulate
        scenario: Dict of signal changes, e.g.:
            {"sst": +2.0, "chlorophyll": +20%}
            Values can be absolute or percentage (if ends with %)

    Returns:
        Simulation results with cascading effects and risk assessment
    """
    zone = db.get_zone(zone_id)
    if not zone:
        return {"error": f"Zone {zone_id} not found"}

    # Get current state (latest readings)
    readings = db.get_readings(zone_id, limit=24)  # Last 24h average
    if not readings:
        return {"error": f"No data available for {zone_id}"}

    # Calculate current averages
    signals = ["sst", "chlorophyll", "wind_speed", "ph", "turbidity"]
    current = {}
    for sig in signals:
        values = [r[sig] for r in readings if r.get(sig) is not None]
        current[sig] = np.mean(values) if values else zone.get(f"baseline_{sig}", 0)

    baselines = {
        "sst": zone.get("baseline_sst", 28.5),
        "chlorophyll": zone.get("baseline_chlorophyll", 1.0),
        "wind_speed": zone.get("baseline_wind", 5.0),
        "ph": zone.get("baseline_ph", 8.1),
        "turbidity": zone.get("baseline_turbidity", 10.0),
    }

    # Apply direct changes from scenario
    simulated = dict(current)
    direct_changes = {}

    for signal, change in scenario.items():
        if signal not in signals:
            continue
        if isinstance(change, str) and change.endswith("%"):
            pct = float(change.rstrip("%")) / 100
            direct_changes[signal] = current[signal] * pct
            simulated[signal] = current[signal] * (1 + pct)
        else:
            direct_changes[signal] = float(change)
            simulated[signal] = current[signal] + float(change)

    # Calculate cascading effects (indirect impacts)
    cascade_effects = {}
    for changed_signal, change_amount in direct_changes.items():
        if changed_signal in SIGNAL_INTERACTIONS:
            for affected_signal, coefficient in SIGNAL_INTERACTIONS[changed_signal].items():
                if affected_signal not in scenario:  # Don't override direct changes
                    cascade_amount = change_amount * coefficient
                    if affected_signal not in cascade_effects:
                        cascade_effects[affected_signal] = 0
                    cascade_effects[affected_signal] += cascade_amount

    # Apply cascading effects
    for signal, effect in cascade_effects.items():
        simulated[signal] = simulated.get(signal, current[signal]) + effect

    # Calculate deviations from baseline
    deviations = {}
    for sig in signals:
        dev = simulated[sig] - baselines[sig]
        deviations[sig] = round(dev, 3)

    # Assess ecosystem impacts
    triggered_impacts = []
    sst_dev = deviations.get("sst", 0)
    chl_dev = deviations.get("chlorophyll", 0)
    ph_dev = deviations.get("ph", 0)
    wind_dev = deviations.get("wind_speed", 0)
    turb_dev = deviations.get("turbidity", 0)

    for impact_name, impact_def in ECOSYSTEM_IMPACTS.items():
        try:
            trigger_fn = impact_def["trigger"]
            # Try different parameter combinations
            triggered = False
            try:
                triggered = trigger_fn(sst_dev, ph_dev)
            except TypeError:
                try:
                    triggered = trigger_fn(chl_dev, sst_dev)
                except TypeError:
                    try:
                        triggered = trigger_fn(chl_dev, turb_dev)
                    except TypeError:
                        try:
                            triggered = trigger_fn(sst_dev, wind_dev)
                        except TypeError:
                            try:
                                triggered = trigger_fn(wind_dev, turb_dev)
                            except TypeError:
                                pass

            if triggered:
                triggered_impacts.append({
                    "impact": impact_name.replace("_", " ").title(),
                    "description": impact_def["description"],
                    "affected": impact_def["affected"],
                    "severity": impact_def["severity"],
                })
        except Exception:
            continue

    # Calculate overall risk score
    risk_score = 0
    for sig, dev in deviations.items():
        thresholds = RISK_THRESHOLDS.get(sig, {})
        abs_dev = abs(dev)
        if abs_dev >= thresholds.get("critical", 999):
            risk_score += 1.0
        elif abs_dev >= thresholds.get("high", 999):
            risk_score += 0.7
        elif abs_dev >= thresholds.get("medium", 999):
            risk_score += 0.4
        elif abs_dev >= thresholds.get("low", 999):
            risk_score += 0.15

    risk_score = min(1.0, risk_score / len(signals))

    risk_level = "LOW"
    if risk_score >= 0.7:
        risk_level = "CRITICAL"
    elif risk_score >= 0.5:
        risk_level = "HIGH"
    elif risk_score >= 0.3:
        risk_level = "MEDIUM"

    # Get economic impact
    from agents.impact_agent import estimate_impact
    changed_signals = list(scenario.keys())
    if not changed_signals:
        changed_signals = ["sst"]
    econ = estimate_impact(zone_id, changed_signals, risk_score, 7)

    # Generate recommendations
    recommendations = _generate_what_if_recommendations(
        zone["name"], scenario, deviations, triggered_impacts, risk_level
    )

    return {
        "zone_id": zone_id,
        "zone_name": zone["name"],
        "scenario_applied": scenario,
        "current_state": {k: round(v, 3) for k, v in current.items()},
        "simulated_state": {k: round(v, 3) for k, v in simulated.items()},
        "baselines": baselines,
        "deviations_from_baseline": deviations,
        "direct_changes": {k: round(v, 3) for k, v in direct_changes.items()},
        "cascading_effects": {k: round(v, 3) for k, v in cascade_effects.items()},
        "risk_assessment": {
            "risk_score": round(risk_score, 3),
            "risk_level": risk_level,
            "ecosystem_impacts": triggered_impacts,
        },
        "economic_impact": econ.get("economic_impact", {}),
        "recommendations": recommendations,
    }


def _generate_what_if_recommendations(zone_name, scenario, deviations,
                                       impacts, risk_level):
    recs = []
    if risk_level in ["HIGH", "CRITICAL"]:
        recs.append(f"URGENT: Issue environmental advisory for {zone_name}")

    if deviations.get("sst", 0) > 2.0:
        recs.append("Restrict warm water industrial discharge in this zone")
        recs.append("Alert coral monitoring stations for potential bleaching")

    if deviations.get("chlorophyll", 0) > 2.0:
        recs.append("Deploy water quality sampling teams")
        recs.append("Issue HAB watch advisory for fishing communities")

    if abs(deviations.get("ph", 0)) > 0.3:
        recs.append("Investigate industrial effluent sources")
        recs.append("Monitor shellfish and aquaculture operations")

    if deviations.get("wind_speed", 0) > 8:
        recs.append("Issue small craft and fishing vessel advisory")

    if deviations.get("turbidity", 0) > 20:
        recs.append("Investigate sediment sources: construction, dredging, runoff")

    for impact in impacts:
        if impact["severity"] == "CRITICAL":
            recs.append(f"CRITICAL: {impact['impact']} — Activate emergency response protocol")

    if not recs:
        recs.append(f"Continue standard monitoring at {zone_name}")

    return recs


# ═══════════════════════════════════════════════════════════
# 2. ROOT CAUSE DETECTION
# ═══════════════════════════════════════════════════════════

# Rule-based causal patterns (augmented by Gemini if available)
CAUSAL_PATTERNS = [
    {
        "condition": lambda d: d.get("sst", 0) > 1.5 and d.get("wind_speed", 0) < -1.5,
        "cause": "Reduced wind cooling combined with solar radiation heating",
        "mechanism": "Lower wind speeds reduce surface heat dissipation, allowing solar radiation to accumulate thermal energy in the mixed layer.",
        "confidence": 0.85,
    },
    {
        "condition": lambda d: d.get("sst", 0) > 2.0 and d.get("chlorophyll", 0) > 1.5,
        "cause": "Warm water nutrient enrichment driving algal proliferation",
        "mechanism": "Elevated SST accelerates nutrient cycling and extends blooming season, while stratification concentrates nutrients in the photic zone.",
        "confidence": 0.80,
    },
    {
        "condition": lambda d: d.get("chlorophyll", 0) > 3.0 and d.get("turbidity", 0) > 10,
        "cause": "Excessive nutrient loading from terrestrial runoff",
        "mechanism": "River discharge and agricultural runoff introduce nitrogen/phosphorus, fueling algal blooms that increase turbidity through biomass accumulation.",
        "confidence": 0.75,
    },
    {
        "condition": lambda d: d.get("ph", 0) < -0.2 and d.get("sst", 0) > 1.0,
        "cause": "Temperature-driven ocean acidification",
        "mechanism": "Warmer waters hold less dissolved CO₂ directly, but increased atmospheric CO₂ absorption and organic decomposition lower pH. Thermal stratification traps acidified water.",
        "confidence": 0.70,
    },
    {
        "condition": lambda d: d.get("wind_speed", 0) > 5.0 and d.get("turbidity", 0) > 15,
        "cause": "Storm-induced sediment resuspension",
        "mechanism": "High wind speeds generate wave action that disturbs bottom sediments, resuspending particulates into the water column.",
        "confidence": 0.90,
    },
    {
        "condition": lambda d: d.get("turbidity", 0) > 20 and d.get("chlorophyll", 0) < -0.5,
        "cause": "Dredging or construction activity",
        "mechanism": "Mechanical disturbance of seafloor releases sediment while blocking light penetration needed for photosynthesis, suppressing chlorophyll.",
        "confidence": 0.65,
    },
    {
        "condition": lambda d: d.get("sst", 0) > 3.0,
        "cause": "Sustained thermal anomaly — possible marine heatwave",
        "mechanism": "Persistent high-pressure atmospheric blocking or weakened upwelling allows surface heat to accumulate beyond seasonal norms.",
        "confidence": 0.75,
    },
    {
        "condition": lambda d: abs(d.get("ph", 0)) > 0.3 and d.get("chlorophyll", 0) > 2.0,
        "cause": "Algal bloom metabolism altering water chemistry",
        "mechanism": "Dense phytoplankton consume CO₂ during day (raising pH) and release it at night (lowering pH), creating large diurnal swings.",
        "confidence": 0.80,
    },
    {
        "condition": lambda d: d.get("sst", 0) < -2.0 and d.get("wind_speed", 0) > 3.0,
        "cause": "Upwelling event bringing cold deep water",
        "mechanism": "Wind-driven Ekman transport pushes surface water offshore, allowing cold nutrient-rich deep water to rise, dropping SST rapidly.",
        "confidence": 0.85,
    },
]


def detect_root_cause(zone_id: str) -> dict:
    """
    Analyze current anomalies in a zone and identify likely root causes.
    Uses rule-based causal patterns + signal deviation analysis.
    """
    zone = db.get_zone(zone_id)
    if not zone:
        return {"error": f"Zone {zone_id} not found"}

    # Get recent deviations
    readings = db.get_readings(zone_id, limit=48)
    if not readings:
        return {"zone_id": zone_id, "causes": [], "message": "Insufficient data"}

    baselines = {
        "sst": zone.get("baseline_sst", 28.5),
        "chlorophyll": zone.get("baseline_chlorophyll", 1.0),
        "wind_speed": zone.get("baseline_wind", 5.0),
        "ph": zone.get("baseline_ph", 8.1),
        "turbidity": zone.get("baseline_turbidity", 10.0),
    }

    # Calculate recent deviations
    signals = ["sst", "chlorophyll", "wind_speed", "ph", "turbidity"]
    deviations = {}
    for sig in signals:
        values = [r[sig] for r in readings if r.get(sig) is not None]
        if values:
            avg = np.mean(values)
            deviations[sig] = round(avg - baselines.get(sig, avg), 3)
        else:
            deviations[sig] = 0

    # Match causal patterns
    matched_causes = []
    for pattern in CAUSAL_PATTERNS:
        try:
            if pattern["condition"](deviations):
                matched_causes.append({
                    "cause": pattern["cause"],
                    "mechanism": pattern["mechanism"],
                    "confidence": pattern["confidence"],
                })
        except Exception:
            continue

    # Sort by confidence
    matched_causes.sort(key=lambda c: c["confidence"], reverse=True)

    # Determine which signals are anomalous
    anomalous_signals = []
    for sig, dev in deviations.items():
        thresholds = RISK_THRESHOLDS.get(sig, {})
        abs_dev = abs(dev)
        if abs_dev >= thresholds.get("medium", 999):
            direction = "above" if dev > 0 else "below"
            anomalous_signals.append({
                "signal": sig,
                "deviation": dev,
                "direction": direction,
                "severity": "critical" if abs_dev >= thresholds.get("critical", 999) else
                           "high" if abs_dev >= thresholds.get("high", 999) else "medium",
            })

    return {
        "zone_id": zone_id,
        "zone_name": zone["name"],
        "analysis_window": "48 hours",
        "deviations": deviations,
        "anomalous_signals": anomalous_signals,
        "root_causes": matched_causes,
        "primary_cause": matched_causes[0] if matched_causes else {
            "cause": "No significant causal pattern detected",
            "mechanism": "Current deviations are within normal variability range",
            "confidence": 0.5,
        },
        "total_causes_identified": len(matched_causes),
    }


# ═══════════════════════════════════════════════════════════
# 3. AGENT CONVERSATION LOGS (Multi-Agent Reasoning Chain)
# ═══════════════════════════════════════════════════════════

# In-memory log for the current session
_agent_logs = []
MAX_LOGS = 500


def log_agent_action(agent: str, action: str, details: str = "",
                      zone_id: str = None, severity: str = "info"):
    """Log an agent action for the reasoning chain."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "action": action,
        "details": details,
        "zone_id": zone_id,
        "severity": severity,
    }
    _agent_logs.append(entry)

    # Keep bounded
    if len(_agent_logs) > MAX_LOGS:
        _agent_logs.pop(0)


def get_agent_logs(limit: int = 50, agent_filter: str = None,
                    zone_filter: str = None) -> list:
    """Get agent conversation logs."""
    logs = list(reversed(_agent_logs))  # Newest first

    if agent_filter:
        logs = [l for l in logs if agent_filter.lower() in l["agent"].lower()]
    if zone_filter:
        logs = [l for l in logs if l.get("zone_id") == zone_filter]

    return logs[:limit]


def get_reasoning_chain(zone_id: str = None) -> dict:
    """
    Get the full multi-agent reasoning chain for a zone or system-wide.
    Shows how agents communicated to reach decisions.
    """
    logs = get_agent_logs(limit=100, zone_filter=zone_id)

    # Group by "conversations" (time-proximate entries)
    chains = []
    current_chain = []

    for i, log in enumerate(logs):
        if i == 0 or (current_chain and
            _time_diff_seconds(current_chain[-1]["timestamp"], log["timestamp"]) < 60):
            current_chain.append(log)
        else:
            if current_chain:
                chains.append(current_chain)
            current_chain = [log]

    if current_chain:
        chains.append(current_chain)

    return {
        "zone_id": zone_id,
        "total_logs": len(logs),
        "reasoning_chains": len(chains),
        "logs": logs[:50],
        "agent_activity": _count_agent_activity(logs),
    }


def _time_diff_seconds(t1: str, t2: str) -> float:
    try:
        dt1 = datetime.fromisoformat(t1.replace("Z", "+00:00"))
        dt2 = datetime.fromisoformat(t2.replace("Z", "+00:00"))
        return abs((dt1 - dt2).total_seconds())
    except Exception:
        return 999


def _count_agent_activity(logs: list) -> dict:
    counts = {}
    for l in logs:
        agent = l["agent"]
        counts[agent] = counts.get(agent, 0) + 1
    return counts


# Seed some initial logs for demo
def seed_demo_logs():
    """Create demo agent conversation logs."""
    log_agent_action("🟢 Data Agent", "INGEST", "Fetching real-time data from NOAA ERDDAP, OpenAQ, Open-Meteo", severity="info")
    log_agent_action("🟢 Data Agent", "COMPLETE", "Ingested 8 zones × 5 signals. 3 partial readings (ERDDAP timeout).", severity="info")
    log_agent_action("🔵 Analysis Agent", "TRAIN", "Retraining Isolation Forest on 90-day sliding window", severity="info")
    log_agent_action("🔵 Analysis Agent", "ANOMALY", "SST anomaly detected: zone_mumbai, +2.3°C deviation, z-score=3.1", zone_id="zone_mumbai", severity="warning")
    log_agent_action("🔵 Analysis Agent", "ANOMALY", "Chlorophyll surge: zone_sundarbans, +4.2 mg/m³, z-score=2.8", zone_id="zone_sundarbans", severity="warning")
    log_agent_action("🟡 Decision Agent", "EVALUATE", "Scoring anomalies: magnitude=0.91, recency=0.85, trajectory=0.78", zone_id="zone_mumbai", severity="info")
    log_agent_action("🟡 Decision Agent", "ALERT", "Generated HIGH alert: 'Thermal Buildup' (priority: 0.87)", zone_id="zone_mumbai", severity="warning")
    log_agent_action("🟡 Decision Agent", "SUPPRESS", "Suppressed low-confidence alert for zone_kutch (confidence: 0.32 < 0.40 floor)", zone_id="zone_kutch", severity="info")
    log_agent_action("🟣 Memory Agent", "SENSITIVITY", "zone_sundarbans sensitivity adjusted: 1.0 → 0.85 (chronic chlorophyll noise)", zone_id="zone_sundarbans", severity="info")
    log_agent_action("🔗 Cascade Agent", "PREDICT", "Mumbai Coast anomaly → Goa Coast at risk in 1-3 days (85% probability)", zone_id="zone_mumbai", severity="warning")
    log_agent_action("💰 Impact Agent", "ESTIMATE", "Total economic impact: ₹576 crore. 48,000 fishing families at risk", severity="warning")
    log_agent_action("🔴 Explanation Agent", "BRIEFING", "Generated situational briefing via Gemini LLM", severity="info")
    log_agent_action("⏰ Scheduler", "CYCLE", "Ingestion cycle #1 complete. Next ingestion in 6 hours.", severity="info")


# ═══════════════════════════════════════════════════════════
# 4. PATTERN MEMORY — "Similar event occurred before"
# ═══════════════════════════════════════════════════════════

def find_similar_events(zone_id: str, signal: str = None) -> dict:
    """
    Search historical data for similar anomaly patterns.
    "This looks like what happened 47 days ago"
    """
    zone = db.get_zone(zone_id)
    if not zone:
        return {"error": f"Zone {zone_id} not found"}

    # Get current anomalies
    current_anomalies = db.get_anomalies(zone_id=zone_id, limit=10)
    if not current_anomalies:
        return {
            "zone_id": zone_id,
            "zone_name": zone["name"],
            "similar_events": [],
            "message": "No current anomalies to compare against",
        }

    # Get current signature
    current_signals = set()
    current_severity_avg = 0
    for a in current_anomalies:
        current_signals.add(a["signal"])
        current_severity_avg += abs(a.get("z_score", 0))
    current_severity_avg /= len(current_anomalies)

    # Get all historical anomalies
    all_anomalies = db.get_anomalies(zone_id=zone_id, limit=500)

    # Group by date to find event clusters
    from collections import defaultdict
    daily_clusters = defaultdict(list)
    for a in all_anomalies:
        day = a["timestamp"][:10]  # YYYY-MM-DD
        daily_clusters[day].append(a)

    # Compare each historical cluster to current
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    similar_events = []

    for day, cluster in daily_clusters.items():
        if day == today:
            continue

        hist_signals = set(a["signal"] for a in cluster)
        hist_severity = np.mean([abs(a.get("z_score", 0)) for a in cluster])

        # Calculate similarity
        signal_overlap = len(current_signals & hist_signals) / max(len(current_signals | hist_signals), 1)
        severity_similarity = 1.0 - min(1.0, abs(current_severity_avg - hist_severity) / max(current_severity_avg, 1))

        similarity = (signal_overlap * 0.6 + severity_similarity * 0.4)

        if similarity >= 0.4:
            days_ago = (datetime.now(timezone.utc) - datetime.fromisoformat(day + "T00:00:00+00:00")).days

            # Get the outcome (did alerts follow?)
            outcome = "Unknown"
            day_alerts = [a for a in db.get_alerts(include_suppressed=True, limit=100)
                         if a["zone_id"] == zone_id and a["timestamp"][:10] == day]
            if day_alerts:
                validated = [a for a in day_alerts if a.get("feedback") == "validated"]
                false_pos = [a for a in day_alerts if a.get("feedback") == "false_positive"]
                if validated:
                    outcome = "Confirmed event"
                elif false_pos:
                    outcome = "False positive"
                else:
                    outcome = "Alert generated, no feedback"

            similar_events.append({
                "date": day,
                "days_ago": days_ago,
                "similarity_score": round(similarity, 3),
                "signals_involved": list(hist_signals),
                "avg_severity": round(hist_severity, 2),
                "num_anomalies": len(cluster),
                "outcome": outcome,
                "signals_in_common": list(current_signals & hist_signals),
            })

    # Sort by similarity
    similar_events.sort(key=lambda e: e["similarity_score"], reverse=True)

    # Generate insight
    insight = ""
    if similar_events:
        best = similar_events[0]
        insight = (
            f"⚠️ Similar pattern detected: This matches an event from {best['days_ago']} days ago "
            f"(similarity: {best['similarity_score']:.0%}). "
            f"Outcome then: {best['outcome']}. "
            f"Common signals: {', '.join(best['signals_in_common'])}."
        )
    else:
        insight = "✅ No similar historical patterns found. This appears to be a novel event."

    return {
        "zone_id": zone_id,
        "zone_name": zone["name"],
        "current_anomaly_signals": list(current_signals),
        "current_severity": round(current_severity_avg, 2),
        "similar_events": similar_events[:5],  # Top 5
        "insight": insight,
    }


# ═══════════════════════════════════════════════════════════
# 5. TIME-TO-RISK EARLY WARNING
# ═══════════════════════════════════════════════════════════

def calculate_time_to_risk(zone_id: str) -> dict:
    """
    Calculate when each signal is projected to reach risk thresholds.
    "SST will hit critical level in ~48 hours"
    """
    zone = db.get_zone(zone_id)
    if not zone:
        return {"error": f"Zone {zone_id} not found"}

    readings = db.get_readings(zone_id, limit=168)  # 7 days
    if len(readings) < 24:
        return {"zone_id": zone_id, "warnings": [], "message": "Insufficient data for trend projection"}

    baselines = {
        "sst": zone.get("baseline_sst", 28.5),
        "chlorophyll": zone.get("baseline_chlorophyll", 1.0),
        "wind_speed": zone.get("baseline_wind", 5.0),
        "ph": zone.get("baseline_ph", 8.1),
        "turbidity": zone.get("baseline_turbidity", 10.0),
    }

    signals = ["sst", "chlorophyll", "wind_speed", "ph", "turbidity"]
    warnings = []

    for sig in signals:
        values = [r[sig] for r in readings if r.get(sig) is not None]
        if len(values) < 24:
            continue

        # Calculate trend (linear regression on last 72h)
        recent = values[-72:] if len(values) >= 72 else values
        x = np.arange(len(recent))
        try:
            coeffs = np.polyfit(x, recent, 1)
            slope = coeffs[0]  # Units per hour
        except Exception:
            continue

        current_val = recent[-1]
        current_dev = current_val - baselines[sig]
        thresholds = RISK_THRESHOLDS.get(sig, {})

        # Determine direction of concern
        if slope == 0:
            continue

        hours_to_levels = {}
        for level_name, threshold in thresholds.items():
            if abs(current_dev) >= threshold:
                hours_to_levels[level_name] = 0  # Already at this level
            elif slope > 0 and current_dev < threshold:
                # How many hours until deviation reaches this threshold?
                remaining = threshold - abs(current_dev)
                hours = remaining / abs(slope)
                if hours <= 168:  # Within 7 days
                    hours_to_levels[level_name] = round(hours, 1)
            elif slope < 0 and current_dev > -threshold:
                remaining = threshold - abs(current_dev)
                hours = remaining / abs(slope)
                if hours <= 168:
                    hours_to_levels[level_name] = round(hours, 1)

        if hours_to_levels:
            # Find the most urgent concerning threshold
            earliest_risk = None
            for level in ["critical", "high", "medium", "low"]:
                h = hours_to_levels.get(level)
                if h is not None and h > 0:
                    if earliest_risk is None or h < earliest_risk.get("hours", 999):
                        earliest_risk = {"level": level, "hours": h}

            trend_direction = "increasing" if slope > 0 else "decreasing"

            warning = {
                "signal": sig,
                "current_value": round(current_val, 3),
                "baseline": baselines[sig],
                "current_deviation": round(current_dev, 3),
                "trend": trend_direction,
                "rate_per_hour": round(slope, 5),
                "rate_per_day": round(slope * 24, 3),
                "time_to_risk_levels": hours_to_levels,
            }

            if earliest_risk and earliest_risk["hours"] > 0:
                warning["earliest_risk_level"] = earliest_risk["level"]
                warning["hours_to_earliest_risk"] = earliest_risk["hours"]
                warning["human_readable"] = (
                    f"{sig.upper()} {trend_direction} at {abs(slope*24):.2f}/day — "
                    f"will reach {earliest_risk['level'].upper()} in "
                    f"~{earliest_risk['hours']:.0f} hours ({earliest_risk['hours']/24:.1f} days)"
                )
            elif 0 in hours_to_levels.values():
                already_at = [l for l, h in hours_to_levels.items() if h == 0]
                warning["already_at_risk"] = True
                warning["current_risk_levels"] = already_at
                warning["human_readable"] = (
                    f"{sig.upper()} already at {', '.join(l.upper() for l in already_at)} risk level"
                )

            warnings.append(warning)

    # Sort: already-at-risk first, then by hours to earliest risk
    warnings.sort(key=lambda w: w.get("hours_to_earliest_risk", -1 if w.get("already_at_risk") else 999))

    # Overall early warning score
    urgent_count = sum(1 for w in warnings if w.get("hours_to_earliest_risk", 999) < 48)
    already_count = sum(1 for w in warnings if w.get("already_at_risk"))

    return {
        "zone_id": zone_id,
        "zone_name": zone["name"],
        "analysis_window": "7 days of trend data",
        "projection_horizon": "7 days forward",
        "warnings": warnings,
        "summary": {
            "total_signals_analyzed": len(signals),
            "signals_trending_to_risk": len(warnings),
            "already_at_risk": already_count,
            "risk_within_48h": urgent_count,
            "overall_urgency": "CRITICAL" if already_count > 1 or urgent_count > 2
                              else "HIGH" if already_count > 0 or urgent_count > 0
                              else "MODERATE" if len(warnings) > 0
                              else "LOW",
        },
    }

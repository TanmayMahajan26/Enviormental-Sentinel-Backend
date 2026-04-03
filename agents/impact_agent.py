"""
💰 IMPACT AGENT — Economic Impact Estimation + Incident Reports + Multi-Language
Converts abstract anomaly scores into real-world ₹ impact numbers.

Features:
1. Economic Impact Estimation — maps anomalies to ₹ crore impact
2. Auto-Generated Incident Reports — structured reports for regulatory filing
3. Multi-Language Briefings — Hindi, Tamil, Marathi, etc. via Gemini
"""
import json
from datetime import datetime, timezone
from typing import Optional
import database as db


# ═══════════════════════════════════════════════════════════
# ECONOMIC DATA PER ZONE
# Based on real Indian maritime economic statistics
# ═══════════════════════════════════════════════════════════

ZONE_ECONOMICS = {
    "zone_mumbai": {
        "annual_fishing_revenue_crore": 850,    # Mumbai-Thane fishing industry
        "daily_shipping_value_crore": 125,       # JNPT port
        "tourism_daily_crore": 45,
        "population_coastal_lakh": 32,
        "fishing_families": 48000,
        "key_industries": ["Fishing", "Shipping (JNPT)", "Coastal Tourism", "Salt Pans"],
        "protected_areas": ["Thane Creek Flamingo Sanctuary"],
        "vulnerability_index": 0.85,
    },
    "zone_goa": {
        "annual_fishing_revenue_crore": 180,
        "daily_shipping_value_crore": 15,
        "tourism_daily_crore": 85,              # Tourism-heavy
        "population_coastal_lakh": 8,
        "fishing_families": 12000,
        "key_industries": ["Tourism", "Fishing", "Iron Ore Export"],
        "protected_areas": ["Dr. Salim Ali Bird Sanctuary", "Cotigao Wildlife Sanctuary"],
        "vulnerability_index": 0.70,
    },
    "zone_kochi": {
        "annual_fishing_revenue_crore": 1200,   # Kerala = India's #1 fish exporter
        "daily_shipping_value_crore": 35,
        "tourism_daily_crore": 30,
        "population_coastal_lakh": 15,
        "fishing_families": 85000,
        "key_industries": ["Marine Fishing", "Seafood Processing", "Coir Industry", "Backwater Tourism"],
        "protected_areas": ["Vembanad-Kol Wetland (Ramsar Site)"],
        "vulnerability_index": 0.80,
    },
    "zone_chennai": {
        "annual_fishing_revenue_crore": 520,
        "daily_shipping_value_crore": 95,       # Chennai Port
        "tourism_daily_crore": 20,
        "population_coastal_lakh": 28,
        "fishing_families": 55000,
        "key_industries": ["Automobile Export", "Fishing", "Desalination Plants"],
        "protected_areas": ["Pulicat Lake Bird Sanctuary"],
        "vulnerability_index": 0.90,  # Cyclone-prone
    },
    "zone_vizag": {
        "annual_fishing_revenue_crore": 380,
        "daily_shipping_value_crore": 45,
        "tourism_daily_crore": 15,
        "population_coastal_lakh": 18,
        "fishing_families": 35000,
        "key_industries": ["Naval Base", "Steel Plant", "Fishing", "Pharma"],
        "protected_areas": [],
        "vulnerability_index": 0.75,
    },
    "zone_sundarbans": {
        "annual_fishing_revenue_crore": 650,
        "daily_shipping_value_crore": 5,
        "tourism_daily_crore": 8,
        "population_coastal_lakh": 45,          # Largest mangrove population
        "fishing_families": 120000,
        "key_industries": ["Mangrove Honey", "Fishing", "Crab Farming", "Eco-Tourism"],
        "protected_areas": ["Sundarbans National Park (UNESCO)", "Sundarbans Tiger Reserve"],
        "vulnerability_index": 0.95,  # Most vulnerable — sea level rise
    },
    "zone_kutch": {
        "annual_fishing_revenue_crore": 220,
        "daily_shipping_value_crore": 80,       # Mundra Port
        "tourism_daily_crore": 10,
        "population_coastal_lakh": 6,
        "fishing_families": 15000,
        "key_industries": ["Mundra Port", "Salt Industry", "Marine National Park"],
        "protected_areas": ["Marine National Park, Gulf of Kutch", "Narayan Sarovar Sanctuary"],
        "vulnerability_index": 0.65,
    },
    "zone_andaman": {
        "annual_fishing_revenue_crore": 95,
        "daily_shipping_value_crore": 3,
        "tourism_daily_crore": 25,
        "population_coastal_lakh": 4,
        "fishing_families": 18000,
        "key_industries": ["Eco-Tourism", "Fishing", "Coconut", "Marine Research"],
        "protected_areas": ["Mahatma Gandhi Marine NP", "Rani Jhansi Marine NP", "Saddle Peak NP"],
        "vulnerability_index": 0.60,
    },
}

# How anomaly types map to economic sectors
ANOMALY_ECONOMIC_MAP = {
    "sst": {
        "affected_sectors": ["fishing", "coral_reefs", "marine_biodiversity"],
        "fishing_impact_multiplier": 0.4,    # 40% of fishing revenue at risk
        "shipping_impact_multiplier": 0.05,  # Minimal shipping impact
        "tourism_impact_multiplier": 0.15,
        "description": "Thermal stress disrupts fish migration patterns and coral health",
    },
    "chlorophyll": {
        "affected_sectors": ["fishing", "tourism", "water_quality"],
        "fishing_impact_multiplier": 0.5,    # Blooms can devastate fisheries
        "shipping_impact_multiplier": 0.02,
        "tourism_impact_multiplier": 0.35,
        "description": "Algal blooms cause oxygen depletion, fish kills, and beach closures",
    },
    "wind_speed": {
        "affected_sectors": ["shipping", "fishing", "coastal_infrastructure"],
        "fishing_impact_multiplier": 0.6,    # Boats can't go out
        "shipping_impact_multiplier": 0.3,   # Port delays
        "tourism_impact_multiplier": 0.2,
        "description": "High winds halt fishing operations and delay shipping",
    },
    "ph": {
        "affected_sectors": ["coral_reefs", "shellfish", "marine_biodiversity"],
        "fishing_impact_multiplier": 0.25,
        "shipping_impact_multiplier": 0.0,
        "tourism_impact_multiplier": 0.10,
        "description": "Ocean acidification threatens shellfish and coral ecosystems",
    },
    "turbidity": {
        "affected_sectors": ["fishing", "coral_reefs", "tourism"],
        "fishing_impact_multiplier": 0.2,
        "shipping_impact_multiplier": 0.1,   # Navigation hazard
        "tourism_impact_multiplier": 0.25,
        "description": "High turbidity reduces visibility, smothers coral, disrupts feeding",
    },
}


# ═══════════════════════════════════════════════════════════
# ECONOMIC IMPACT ESTIMATION
# ═══════════════════════════════════════════════════════════

def estimate_impact(zone_id: str, signals: list = None, severity: float = 0.5,
                    duration_days: int = 7) -> dict:
    """
    Estimate economic impact of an environmental event.

    Args:
        zone_id: The affected zone
        signals: List of affected signals (e.g., ["sst", "chlorophyll"])
        severity: 0-1, how severe the event is
        duration_days: Expected duration

    Returns:
        Detailed economic impact assessment in ₹ crore
    """
    econ = ZONE_ECONOMICS.get(zone_id, {})
    if not econ:
        return {"error": f"No economic data for {zone_id}"}

    if signals is None:
        signals = ["sst"]

    # Calculate impact per sector
    daily_fishing = econ["annual_fishing_revenue_crore"] / 365
    daily_shipping = econ["daily_shipping_value_crore"]
    daily_tourism = econ["tourism_daily_crore"]

    fishing_impact = 0
    shipping_impact = 0
    tourism_impact = 0

    for signal in signals:
        signal_map = ANOMALY_ECONOMIC_MAP.get(signal, {})
        fishing_impact += daily_fishing * signal_map.get("fishing_impact_multiplier", 0.1)
        shipping_impact += daily_shipping * signal_map.get("shipping_impact_multiplier", 0.05)
        tourism_impact += daily_tourism * signal_map.get("tourism_impact_multiplier", 0.1)

    # Scale by severity and duration
    severity_factor = severity * econ.get("vulnerability_index", 0.7)
    fishing_total = round(fishing_impact * severity_factor * duration_days, 2)
    shipping_total = round(shipping_impact * severity_factor * duration_days, 2)
    tourism_total = round(tourism_impact * severity_factor * duration_days, 2)
    total_impact = round(fishing_total + shipping_total + tourism_total, 2)

    # Affected people
    families_affected = int(econ["fishing_families"] * severity_factor * 0.5)
    people_affected_lakh = round(econ["population_coastal_lakh"] * severity_factor * 0.15, 2)

    zone = db.get_zone(zone_id)
    zone_name = zone["name"] if zone else zone_id

    return {
        "zone_id": zone_id,
        "zone_name": zone_name,
        "severity": severity,
        "duration_days": duration_days,
        "signals_analyzed": signals,
        "economic_impact": {
            "total_impact_crore": total_impact,
            "fishing_impact_crore": fishing_total,
            "shipping_impact_crore": shipping_total,
            "tourism_impact_crore": tourism_total,
            "currency": "INR",
            "unit": "crore (1 crore = 10 million)",
        },
        "social_impact": {
            "fishing_families_affected": families_affected,
            "population_affected_lakh": people_affected_lakh,
            "key_industries_at_risk": econ["key_industries"],
            "protected_areas_at_risk": econ.get("protected_areas", []),
        },
        "vulnerability_index": econ["vulnerability_index"],
        "impact_summary": _generate_impact_summary(
            zone_name, total_impact, families_affected, signals, severity
        ),
    }


def _generate_impact_summary(zone_name: str, total_crore: float,
                              families: int, signals: list, severity: float) -> str:
    """Generate human-readable impact summary."""
    severity_word = "minor"
    if severity > 0.7:
        severity_word = "severe"
    elif severity > 0.4:
        severity_word = "moderate"

    signal_names = {
        "sst": "thermal stress", "chlorophyll": "algal bloom",
        "wind_speed": "high wind", "ph": "acidification", "turbidity": "high turbidity"
    }
    signal_desc = " and ".join(signal_names.get(s, s) for s in signals[:2])

    return (
        f"The {severity_word} {signal_desc} event at {zone_name} has an estimated "
        f"economic impact of ₹{total_crore} crore, potentially affecting "
        f"{families:,} fishing families. Immediate advisory recommended."
    )


def estimate_all_active_impacts() -> list:
    """Estimate economic impact for all active alerts."""
    alerts = db.get_alerts(include_suppressed=False, limit=20)
    impacts = []

    for alert in alerts:
        signals = alert.get("signals_involved", "[]")
        if isinstance(signals, str):
            signals = json.loads(signals)

        impact = estimate_impact(
            zone_id=alert["zone_id"],
            signals=signals,
            severity=alert["priority_score"],
            duration_days=7,
        )
        impact["alert_id"] = alert["id"]
        impact["alert_title"] = alert["title"]
        impacts.append(impact)

    # Sort by total impact
    impacts.sort(
        key=lambda i: i.get("economic_impact", {}).get("total_impact_crore", 0),
        reverse=True,
    )
    return impacts


# ═══════════════════════════════════════════════════════════
# INCIDENT REPORT GENERATION
# ═══════════════════════════════════════════════════════════

def generate_incident_report(alert_id: int) -> dict:
    """
    Generate a structured incident report for a specific alert.
    Can be used for regulatory filing and post-event analysis.
    """
    # Get alert details
    conn = db.get_connection()
    alert = conn.execute(
        "SELECT * FROM alerts WHERE id = ?", (alert_id,)
    ).fetchone()

    if not alert:
        conn.close()
        return {"error": f"Alert {alert_id} not found"}

    alert = dict(alert)

    # Get zone info
    zone = db.get_zone(alert["zone_id"])

    # Get related anomalies
    anomalies = db.get_anomalies(zone_id=alert["zone_id"], limit=20)

    # Get recent readings for timeline
    readings = db.get_readings(alert["zone_id"], limit=168)  # Last 7 days

    # Parse signals
    signals = alert.get("signals_involved", "[]")
    if isinstance(signals, str):
        signals = json.loads(signals)

    # Get economic impact
    impact = estimate_impact(
        zone_id=alert["zone_id"],
        signals=signals,
        severity=alert["priority_score"],
    )

    # Get feedback history
    feedback_entries = conn.execute(
        "SELECT * FROM feedback_log WHERE zone_id = ? ORDER BY timestamp DESC LIMIT 10",
        (alert["zone_id"],)
    ).fetchall()
    conn.close()

    # Build timeline from anomalies
    timeline = []
    for a in sorted(anomalies, key=lambda x: x["timestamp"]):
        timeline.append({
            "timestamp": a["timestamp"],
            "event": f"{a['signal'].upper()} anomaly detected: {a['value']:.2f} "
                     f"(expected {a['expected_value']:.2f}, deviation {a['deviation_pct']:.1f}%)",
            "signal": a["signal"],
            "severity": "high" if abs(a["z_score"]) > 2.5 else "medium" if abs(a["z_score"]) > 1.5 else "low",
        })

    # Sensitivity changes
    sensitivity = db.get_zone_sensitivity(alert["zone_id"])

    report_id = f"IR-{datetime.now(timezone.utc).strftime('%Y')}-{alert_id:04d}"
    zone_name = zone["name"] if zone else alert["zone_id"]

    report = {
        "report_id": report_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "classification": alert["severity"].upper(),

        "header": {
            "title": f"INCIDENT REPORT — {report_id}",
            "zone": zone_name,
            "zone_id": alert["zone_id"],
            "region": zone["region"] if zone else "Unknown",
            "coordinates": f"{zone['lat']}°N, {zone['lng']}°E" if zone else "N/A",
            "event_type": alert["title"],
            "severity": alert["severity"],
            "priority_score": alert["priority_score"],
            "alert_timestamp": alert["timestamp"],
        },

        "scoring_breakdown": {
            "magnitude_score": alert["magnitude_score"],
            "recency_score": alert["recency_score"],
            "trajectory_score": alert["trajectory_score"],
            "convergence_score": alert["convergence_score"],
            "overall_priority": alert["priority_score"],
        },

        "signals_involved": signals,
        "signal_analysis": [
            {
                "signal": s,
                "description": ANOMALY_ECONOMIC_MAP.get(s, {}).get("description", ""),
                "affected_sectors": ANOMALY_ECONOMIC_MAP.get(s, {}).get("affected_sectors", []),
            }
            for s in signals
        ],

        "timeline": timeline[:15],  # Cap at 15 events

        "economic_impact": impact.get("economic_impact", {}),
        "social_impact": impact.get("social_impact", {}),
        "impact_summary": impact.get("impact_summary", ""),

        "system_response": {
            "zone_sensitivity_current": sensitivity["sensitivity"] if sensitivity else 1.0,
            "alert_suppressed": bool(alert.get("is_suppressed")),
            "feedback_received": alert.get("feedback"),
            "total_feedback_entries": len(feedback_entries),
            "adaptive_learning": "Memory Agent has processed feedback to adjust zone sensitivity",
        },

        "recommended_actions": _get_incident_recommendations(alert, signals, impact),

        "data_sources": [
            "NOAA ERDDAP (Sea Surface Temperature, Chlorophyll-a)",
            "Open-Meteo (Wind Speed, Weather)",
            "OpenAQ (Air Quality PM2.5)",
            "NASA EONET (Natural Events)",
            "Isolation Forest Anomaly Detection",
            "Holt-Winters Probabilistic Forecasting",
        ],

        "disclaimer": (
            "This report is auto-generated by the Environmental Sentinel AI system. "
            "Economic estimates are based on statistical models and publicly available data. "
            "Verify with ground-truth observations before policy decisions."
        ),
    }

    return report


def _get_incident_recommendations(alert: dict, signals: list, impact: dict) -> list:
    """Generate recommended actions based on the incident type."""
    recommendations = []

    severity = alert.get("severity", "low")
    priority = alert.get("priority_score", 0)

    if "sst" in signals:
        recommendations.append(
            "Issue fishing advisory: elevated SST may alter fish migration and spawning patterns."
        )
        if priority > 0.7:
            recommendations.append(
                "Alert coral reef monitoring stations for potential bleaching event."
            )

    if "chlorophyll" in signals:
        recommendations.append(
            "Deploy water sampling teams to confirm algal bloom species identification."
        )
        recommendations.append(
            "Issue beach advisory if HAB (Harmful Algal Bloom) confirmed."
        )

    if "wind_speed" in signals:
        recommendations.append(
            "Issue small craft advisory for fishing vessels."
        )
        if priority > 0.7:
            recommendations.append(
                "Coordinate with Indian Navy / Coast Guard for maritime safety bulletin."
            )

    if severity in ["high", "critical"]:
        recommendations.append(
            "Notify District Collector and State Disaster Management Authority."
        )
        recommendations.append(
            "Prepare situation report for Ministry of Earth Sciences."
        )

    families = impact.get("social_impact", {}).get("fishing_families_affected", 0)
    if families > 10000:
        recommendations.append(
            f"Coordinate with Fisheries Department: ~{families:,} fishing families may need advisory/support."
        )

    return recommendations


# ═══════════════════════════════════════════════════════════
# MULTI-LANGUAGE BRIEFINGS
# ═══════════════════════════════════════════════════════════

SUPPORTED_LANGUAGES = {
    "english": "English",
    "hindi": "Hindi (हिन्दी)",
    "marathi": "Marathi (मराठी)",
    "tamil": "Tamil (தமிழ்)",
    "telugu": "Telugu (తెలుగు)",
    "bengali": "Bengali (বাংলা)",
    "gujarati": "Gujarati (ગુજરાતી)",
    "malayalam": "Malayalam (മലയാളം)",
    "kannada": "Kannada (ಕನ್ನಡ)",
    "odia": "Odia (ଓଡ଼ିଆ)",
}

# Zone → best regional language
ZONE_LANGUAGE_MAP = {
    "zone_mumbai": "marathi",
    "zone_goa": "marathi",   # Konkani/Marathi
    "zone_kochi": "malayalam",
    "zone_chennai": "tamil",
    "zone_vizag": "telugu",
    "zone_sundarbans": "bengali",
    "zone_kutch": "gujarati",
    "zone_andaman": "hindi",
}


async def generate_multilang_briefing(language: str = "english",
                                       zone_id: str = None) -> dict:
    """
    Generate situational briefing in the specified language.
    Uses Gemini for translation.
    """
    from config import GEMINI_API_KEY

    # Get English briefing content first
    alerts = db.get_alerts(include_suppressed=False, limit=5)
    zones = db.get_all_zones()

    # Build context
    alert_summaries = []
    for a in alerts[:5]:
        signals = a.get("signals_involved", "[]")
        if isinstance(signals, str):
            signals = json.loads(signals)

        impact = estimate_impact(a["zone_id"], signals, a["priority_score"])
        impact_crore = impact.get("economic_impact", {}).get("total_impact_crore", 0)
        families = impact.get("social_impact", {}).get("fishing_families_affected", 0)

        alert_summaries.append(
            f"- [{a['severity'].upper()}] {a['title']} at {a.get('zone_name', a['zone_id'])} "
            f"(priority: {a['priority_score']:.2f}). "
            f"Estimated impact: ₹{impact_crore} crore, {families:,} families affected. "
            f"Signals: {', '.join(signals)}"
        )

    alert_text = "\n".join(alert_summaries) if alert_summaries else "No active alerts."

    lang_name = SUPPORTED_LANGUAGES.get(language, language)

    if GEMINI_API_KEY and language != "english":
        try:
            from google import genai

            client = genai.Client(api_key=GEMINI_API_KEY)

            prompt = f"""You are an environmental monitoring AI assistant. Generate a situational briefing in {lang_name}.

CURRENT ALERTS:
{alert_text}

INSTRUCTIONS:
1. Write the entire briefing in {lang_name} (use the native script, not transliteration)
2. Include severity indicators: 🔴 Critical, 🟠 High, 🟡 Medium, 🟢 Low
3. Include economic impact figures in ₹ (Indian Rupees)
4. Be concise but actionable — this is for field operators
5. Include recommended actions in the local language
6. Start with a greeting and current date/time

Keep the briefing to 200-300 words."""

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )

            return {
                "language": language,
                "language_name": lang_name,
                "briefing": response.text,
                "alerts_count": len(alerts),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "generated_by": "gemini",
            }

        except Exception as e:
            print(f"[Impact Agent] Gemini translation error: {e}")

    # Fallback: English briefing
    summary_lines = [
        f"Environmental Sentinel — Situational Briefing",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Active Alerts: {len(alerts)}",
        "",
    ]
    summary_lines.extend(alert_summaries) if alert_summaries else summary_lines.append("All zones nominal.")

    return {
        "language": "english",
        "language_name": "English",
        "briefing": "\n".join(summary_lines),
        "alerts_count": len(alerts),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "generated_by": "fallback",
    }

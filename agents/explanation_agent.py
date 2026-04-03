"""
🔴 EXPLANATION AGENT — Gemini LLM Integration
Converts raw numbers into human-readable intelligence briefings.

Features:
1. Situational Briefing: "What needs attention right now?"
2. Context-Aware Chat: Follow-up questions with full zone context
3. Alert Narration: Each alert gets a natural language explanation

Uses Google Gemini API (free tier).
"""
import json
import os
from datetime import datetime

from config import GEMINI_API_KEY
import database as db

# Gemini client setup
_client = None

def _get_client():
    global _client
    if _client is None and GEMINI_API_KEY:
        try:
            from google import genai
            _client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as e:
            print(f"[Explanation Agent] Gemini init failed: {e}")
    return _client


SYSTEM_PROMPT = """You are the Environmental Sentinel AI — a smart environmental monitoring assistant for Indian coastal zones.

Your role:
- Analyze environmental sensor data (SST, chlorophyll, wind, pH, turbidity)
- Explain anomalies in clear, action-oriented language
- Prioritize what needs attention based on severity and trajectory
- Recommend specific actions for marine policy analysts

Response style:
- Be concise but thorough
- Use bullet points for multiple items
- Include specific numbers and trends
- Classify urgency: 🔴 CRITICAL, 🟠 HIGH, 🟡 MEDIUM, 🟢 LOW
- Suggest concrete next steps
- Reference specific zones by name

You monitor 8 Indian coastal zones:
Mumbai Coast, Goa Coast, Kochi Coast, Chennai Coast, Visakhapatnam Coast, Sundarbans Delta, Gulf of Kutch, Andaman Islands
"""


def _build_context() -> str:
    """Build current system state context for Gemini."""
    # Get active alerts
    alerts = db.get_alerts(include_suppressed=False, limit=10)
    # Get system stats
    stats = db.get_system_stats()
    # Get zone sensitivities
    zones = db.get_all_zones()

    context_parts = [
        f"Current Time: {datetime.utcnow().isoformat()}",
        f"System Stats: {stats['total_readings']} readings analyzed, "
        f"{stats['total_anomalies']} anomalies detected, "
        f"{stats['total_alerts']} alerts generated, "
        f"{stats['total_suppressed']} alerts suppressed",
        f"Model Accuracy: {stats['model_accuracy']:.1%}",
        "",
        "=== ACTIVE ALERTS (ranked by priority) ===",
    ]

    for i, alert in enumerate(alerts[:10], 1):
        context_parts.append(
            f"{i}. [{alert.get('severity', 'unknown').upper()}] {alert.get('title', 'Unknown')} "
            f"(Priority: {alert.get('priority_score', 0):.3f})\n"
            f"   Zone: {alert.get('zone_name', alert['zone_id'])}\n"
            f"   Details: {alert.get('description', 'No details')}\n"
            f"   Signals: {alert.get('signals_involved', '[]')}"
        )

    if not alerts:
        context_parts.append("No active alerts at this time.")

    context_parts.append("\n=== ZONE SENSITIVITIES (Memory Agent) ===")
    for zone in zones:
        sens = db.get_zone_sensitivity(zone["id"])
        if sens:
            context_parts.append(
                f"  {zone['name']}: sensitivity={sens['sensitivity']:.3f}, "
                f"precision={sens['precision_rate']:.2f}"
            )

    return "\n".join(context_parts)


async def generate_briefing() -> dict:
    """
    Generate a situational briefing: "What needs attention right now?"
    Returns natural language synthesis of all active alerts.
    """
    client = _get_client()
    alerts = db.get_alerts(include_suppressed=False, limit=10)

    if not client:
        # Fallback: generate structured briefing without LLM
        return _generate_fallback_briefing(alerts)

    context = _build_context()

    prompt = f"""Based on the current environmental monitoring data, generate a concise situational briefing.

{context}

Generate a briefing that:
1. Opens with a 1-sentence executive summary
2. Lists the top 3 most critical situations requiring attention
3. For each situation, explain: what's happening, why it matters, what's the trajectory
4. Ends with recommended immediate actions
5. Note any zones where the system has learned to suppress noise (low sensitivity)

Keep it under 300 words. Use emoji for severity indicators."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        zones_mentioned = []
        all_zones = db.get_all_zones()
        for zone in all_zones:
            if zone["name"].lower() in response.text.lower():
                zones_mentioned.append(zone["id"])

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": response.text,
            "top_alerts": alerts[:5],
            "zones_requiring_attention": zones_mentioned,
            "system_confidence": db.get_system_stats()["model_accuracy"],
        }

    except Exception as e:
        print(f"[Explanation Agent] Gemini briefing error: {e}")
        return _generate_fallback_briefing(alerts)


async def chat(message: str, zone_id: str = None) -> dict:
    """
    Context-aware chat. Operator asks questions, gets intelligent answers.
    """
    client = _get_client()

    if not client:
        return _generate_fallback_chat(message, zone_id)

    context = _build_context()

    # Add zone-specific context if provided
    zone_context = ""
    if zone_id:
        zone = db.get_zone(zone_id)
        if zone:
            zone_context = f"\nThe user is asking about: {zone['name']} ({zone['region']})\n"
            zone_context += f"Zone description: {zone['description']}\n"

            # Get recent readings
            readings = db.get_all_readings_for_zone(zone_id)
            if readings:
                last_reading = readings[-1]
                zone_context += (
                    f"Latest readings: SST={last_reading['sst']}°C, "
                    f"Chlorophyll={last_reading['chlorophyll']}mg/m³, "
                    f"Wind={last_reading['wind_speed']}m/s, "
                    f"pH={last_reading['ph']}, "
                    f"Turbidity={last_reading['turbidity']}NTU\n"
                )

    prompt = f"""{SYSTEM_PROMPT}

Current System State:
{context}
{zone_context}

Operator Question: {message}

Provide a clear, actionable response. If the question is about a specific zone, focus on that zone's data. If it's a general question, synthesize across all zones."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        zones_mentioned = []
        all_zones = db.get_all_zones()
        for zone in all_zones:
            if zone["name"].lower() in response.text.lower():
                zones_mentioned.append(zone["id"])

        alerts = db.get_alerts(include_suppressed=False, limit=10)

        return {
            "response": response.text,
            "context_zones": zones_mentioned,
            "alerts_referenced": len([
                a for a in alerts
                if any(z in a.get("zone_name", "").lower()
                       for z in [z_name.lower() for z_name in zones_mentioned])
            ]),
        }

    except Exception as e:
        print(f"[Explanation Agent] Gemini chat error: {e}")
        return _generate_fallback_chat(message, zone_id)


def _generate_fallback_briefing(alerts: list[dict]) -> dict:
    """Generate a structured briefing without LLM (fallback)."""
    if not alerts:
        summary = "✅ All clear. No active alerts across monitored Indian coastal zones."
    else:
        summary_parts = [
            f"⚠️ Environmental Sentinel Briefing — {len(alerts)} active alert(s)\n"
        ]

        for i, alert in enumerate(alerts[:5], 1):
            severity_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }.get(alert.get("severity", "low"), "⚪")

            summary_parts.append(
                f"{i}. {severity_emoji} **{alert.get('title', 'Alert')}** "
                f"(Priority: {alert.get('priority_score', 0):.2f})\n"
                f"   {alert.get('description', 'No description')}\n"
            )

        summary = "\n".join(summary_parts)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "summary": summary,
        "top_alerts": alerts[:5],
        "zones_requiring_attention": list(set(a["zone_id"] for a in alerts[:5])),
        "system_confidence": db.get_system_stats()["model_accuracy"],
    }


def _generate_fallback_chat(message: str, zone_id: str = None) -> dict:
    """Fallback chat without LLM."""
    alerts = db.get_alerts(include_suppressed=False, limit=10)

    if "attention" in message.lower() or "critical" in message.lower():
        if alerts:
            response = "Based on current analysis:\n\n"
            for a in alerts[:3]:
                response += f"• **{a.get('title', 'Alert')}** — Priority: {a.get('priority_score', 0):.2f}\n"
                response += f"  {a.get('description', 'No details')}\n\n"
        else:
            response = "All zones are currently within normal parameters."
    else:
        response = (
            f"System is monitoring 8 Indian coastal zones with {db.get_system_stats()['total_readings']} "
            f"data points. {len(alerts)} active alerts.\n\n"
            "Note: Configure GEMINI_API_KEY for AI-powered responses."
        )

    return {
        "response": response,
        "context_zones": [a["zone_id"] for a in alerts[:3]] if alerts else [],
        "alerts_referenced": min(len(alerts), 3),
    }

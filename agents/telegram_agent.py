"""
📱 TELEGRAM AGENT — Real-Time Alert Delivery via Telegram Bot
Sends priority alerts to operators' phones.

Setup:
1. Message @BotFather on Telegram → /newbot → get token
2. Add TELEGRAM_BOT_TOKEN to .env
3. Message your bot /start to register
4. Alerts auto-send when new critical events detected

Operators can reply with commands:
/status — current system status
/alerts — top 5 alerts
/validate <id> — mark alert as validated
/false_positive <id> — mark as false positive
"""
import httpx
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional
import database as db
from config import GEMINI_API_KEY

# Telegram config
import os
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")  # Set after /start
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Track sent alerts to avoid duplicates
_sent_alert_ids = set()


# ═══════════════════════════════════════════════════════════
# SEND MESSAGES
# ═══════════════════════════════════════════════════════════

async def send_message(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """Send a message via Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN:
        print("[Telegram] No bot token configured. Skipping.")
        return False

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                },
            )
            resp.raise_for_status()
            return True
    except Exception as e:
        print(f"[Telegram] Send error: {e}")
        return False


async def send_alert_notification(alert: dict, chat_id: str = None) -> bool:
    """
    Format and send a single alert notification.
    """
    target_chat = chat_id or TELEGRAM_CHAT_ID
    if not target_chat:
        return False

    # Skip if already sent
    alert_id = alert.get("id")
    if alert_id in _sent_alert_ids:
        return False

    severity_emoji = {
        "critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"
    }
    sev = alert.get("severity", "low")
    emoji = severity_emoji.get(sev, "⚪")

    signals = alert.get("signals_involved", [])
    if isinstance(signals, str):
        signals = json.loads(signals)

    # Get economic impact
    from agents.impact_agent import estimate_impact
    impact = estimate_impact(
        alert["zone_id"], signals, alert["priority_score"]
    )
    impact_crore = impact.get("economic_impact", {}).get("total_impact_crore", 0)
    families = impact.get("social_impact", {}).get("fishing_families_affected", 0)

    message = (
        f"{emoji} <b>{sev.upper()} — {alert.get('zone_name', alert['zone_id'])}</b>\n"
        f"\n"
        f"📌 <b>{alert['title']}</b>\n"
        f"📊 Priority: {alert['priority_score']:.2f}\n"
        f"📡 Signals: {', '.join(s.upper() for s in signals)}\n"
        f"\n"
        f"💰 Est. Impact: ₹{impact_crore} crore\n"
        f"👥 Families at risk: {families:,}\n"
        f"\n"
        f"<i>Scoring: Mag={alert.get('magnitude_score', 0):.2f} | "
        f"Rec={alert.get('recency_score', 0):.2f} | "
        f"Traj={alert.get('trajectory_score', 0):.2f}</i>\n"
        f"\n"
        f"Reply: /validate_{alert_id} or /false_{alert_id}"
    )

    success = await send_message(target_chat, message)
    if success:
        _sent_alert_ids.add(alert_id)
    return success


async def send_priority_alerts(min_severity: str = "high") -> dict:
    """
    Send all priority alerts above threshold to Telegram.
    Called by the scheduler after each ingestion cycle.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {"sent": 0, "status": "no_telegram_config"}

    severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    min_level = severity_order.get(min_severity, 2)

    alerts = db.get_alerts(include_suppressed=False, limit=10)
    sent = 0

    for alert in alerts:
        sev_level = severity_order.get(alert.get("severity", "low"), 0)
        if sev_level >= min_level:
            success = await send_alert_notification(alert)
            if success:
                sent += 1

    if sent > 0:
        print(f"[Telegram] 📱 Sent {sent} alert notifications")

    return {"sent": sent, "total_alerts": len(alerts)}


async def send_daily_summary() -> bool:
    """Send daily summary briefing to Telegram."""
    target_chat = TELEGRAM_CHAT_ID
    if not TELEGRAM_BOT_TOKEN or not target_chat:
        return False

    stats = db.get_system_stats()
    alerts = db.get_alerts(include_suppressed=False, limit=5)

    alert_lines = []
    for a in alerts[:5]:
        sev_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
            a.get("severity", "low"), "⚪"
        )
        alert_lines.append(
            f"  {sev_emoji} {a.get('zone_name', a['zone_id'])}: {a['title']}"
        )

    message = (
        f"🌍 <b>Environmental Sentinel — Daily Summary</b>\n"
        f"📅 {datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')}\n"
        f"\n"
        f"📊 <b>System Status:</b>\n"
        f"  • Zones monitored: {stats['total_zones']}\n"
        f"  • Total readings: {stats['total_readings']:,}\n"
        f"  • Anomalies detected: {stats['total_anomalies']}\n"
        f"  • Active alerts: {stats['total_alerts']}\n"
        f"  • Suppressed: {stats['total_suppressed']}\n"
        f"  • Model accuracy: {stats['model_accuracy']:.1%}\n"
        f"\n"
        f"🚨 <b>Top Alerts:</b>\n"
    )
    message += "\n".join(alert_lines) if alert_lines else "  ✅ All zones nominal."
    message += "\n\nReply /alerts for details | /status for full report"

    return await send_message(target_chat, message)


# ═══════════════════════════════════════════════════════════
# WEBHOOK HANDLER — Process incoming Telegram messages
# ═══════════════════════════════════════════════════════════

async def handle_telegram_update(update: dict) -> Optional[str]:
    """
    Process incoming Telegram message (webhook).
    Supports operator commands.
    """
    message = update.get("message", {})
    text = message.get("text", "").strip()
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not text or not chat_id:
        return None

    # /start — Register
    if text == "/start":
        await send_message(chat_id,
            "🌍 <b>Environmental Sentinel Bot</b>\n\n"
            "You're now registered for alerts.\n\n"
            "Commands:\n"
            "/status — System status\n"
            "/alerts — Top 5 active alerts\n"
            "/briefing — AI situational briefing\n"
            "/validate_ID — Validate alert\n"
            "/false_ID — Mark as false positive\n"
            "/impact — Economic impact summary"
        )
        return chat_id

    # /status
    elif text == "/status":
        stats = db.get_system_stats()
        await send_message(chat_id,
            f"⚙️ <b>System Status</b>\n"
            f"Status: ✅ Operational\n"
            f"Zones: {stats['total_zones']} | Readings: {stats['total_readings']:,}\n"
            f"Anomalies: {stats['total_anomalies']} | Alerts: {stats['total_alerts']}\n"
            f"Model Accuracy: {stats['model_accuracy']:.1%}"
        )

    # /alerts
    elif text == "/alerts":
        alerts = db.get_alerts(include_suppressed=False, limit=5)
        for alert in alerts:
            await send_alert_notification(alert, chat_id)

    # /validate_ID or /false_ID
    elif text.startswith("/validate_") or text.startswith("/false_"):
        try:
            parts = text.split("_")
            alert_id = int(parts[1])
            feedback_type = "validated" if "validate" in text else "false_positive"

            from agents.memory_agent import process_feedback
            result = process_feedback(alert_id, feedback_type)

            if "error" not in result:
                await send_message(chat_id,
                    f"✅ Feedback recorded: Alert #{alert_id} → {feedback_type}\n"
                    f"Zone sensitivity: {result['zone_sensitivity_before']:.2f} → {result['zone_sensitivity_after']:.2f}"
                )
            else:
                await send_message(chat_id, f"❌ {result['error']}")
        except (IndexError, ValueError):
            await send_message(chat_id, "❌ Usage: /validate_ID or /false_ID")

    # /impact
    elif text == "/impact":
        from agents.impact_agent import estimate_all_active_impacts
        impacts = estimate_all_active_impacts()
        total = sum(i["economic_impact"]["total_impact_crore"] for i in impacts)

        msg = f"💰 <b>Economic Impact Summary</b>\n\n"
        for imp in impacts[:3]:
            msg += (
                f"📍 {imp['zone_name']}: ₹{imp['economic_impact']['total_impact_crore']} crore\n"
                f"   👥 {imp['social_impact']['fishing_families_affected']:,} families\n"
            )
        msg += f"\n<b>Total Active Impact: ₹{total:.1f} crore</b>"
        await send_message(chat_id, msg)

    return None


# ═══════════════════════════════════════════════════════════
# STATUS
# ═══════════════════════════════════════════════════════════

def get_telegram_status() -> dict:
    """Get Telegram bot configuration status."""
    return {
        "configured": bool(TELEGRAM_BOT_TOKEN),
        "chat_id_set": bool(TELEGRAM_CHAT_ID),
        "alerts_sent": len(_sent_alert_ids),
        "setup_instructions": (
            "1. Message @BotFather on Telegram → /newbot\n"
            "2. Copy the token to .env as TELEGRAM_BOT_TOKEN\n"
            "3. Message your bot /start\n"
            "4. Get chat ID from the update and add to .env as TELEGRAM_CHAT_ID"
        ) if not TELEGRAM_BOT_TOKEN else "Bot is configured ✅",
    }

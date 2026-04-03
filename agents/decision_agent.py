"""
🟡 DECISION AGENT — Core Differentiator
Multi-signal convergence scoring engine.

This is the INTELLIGENCE layer that most teams won't have.
Instead of simple threshold alerts, it:

1. Scores anomalies on 5 dimensions:
   - Magnitude: How far from normal?
   - Recency: How recent is the deviation?
   - Trajectory: Is it getting worse?
   - Convergence: Do multiple signals agree?
   - Historical: Has this zone had real events before?

2. Applies zone-specific sensitivity from Memory Agent

3. Suppresses low-confidence and redundant alerts

4. Produces ranked, explainable priority queue
"""
import numpy as np
from datetime import datetime, timedelta
import json

from config import (
    DECISION_WEIGHTS,
    ALERT_COOLDOWN_HOURS,
    MIN_CONVERGENCE_SIGNALS,
    CONFIDENCE_FLOOR,
)
import database as db

SIGNALS = ["sst", "chlorophyll", "wind_speed", "ph", "turbidity"]


def _magnitude_score(anomalies: list[dict]) -> float:
    """
    Score based on how extreme the deviations are.
    Higher z-scores = higher magnitude.
    """
    if not anomalies:
        return 0.0

    z_scores = [abs(a["z_score"]) for a in anomalies]
    max_z = max(z_scores)
    avg_z = np.mean(z_scores)

    # Normalize: z-score of 3+ is very significant
    score = min(1.0, (0.6 * max_z + 0.4 * avg_z) / 4.0)
    return round(score, 3)


def _recency_score(anomalies: list[dict], reference_time: datetime = None) -> float:
    """
    Score based on how recent the anomalies are.
    More recent = higher score.
    """
    if not anomalies:
        return 0.0

    if reference_time is None:
        reference_time = datetime.utcnow()

    # Get the most recent anomaly timestamp
    timestamps = []
    for a in anomalies:
        try:
            ts_str = str(a["timestamp"]).replace("Z", "")
            ts = datetime.fromisoformat(ts_str).replace(tzinfo=None)
            timestamps.append(ts)
        except (ValueError, TypeError):
            pass

    if not timestamps:
        return 0.0

    most_recent = max(timestamps)

    # Ensure reference_time is naive
    reference_time = reference_time.replace(tzinfo=None)

    # Use the last data point as reference (since we're working with historical data)
    # Score: 1.0 if within last day, decays exponentially
    hours_ago = max(0, (reference_time - most_recent).total_seconds() / 3600)
    score = np.exp(-hours_ago / 48)  # half-life of 48 hours

    return round(min(1.0, score), 3)


def _trajectory_score(zone_id: str, signal: str) -> float:
    """
    Score based on whether the anomaly is getting WORSE over time.
    Looks at the trend in anomaly scores over recent readings.
    A positive/increasing trend = higher score.
    """
    readings = db.get_all_readings_for_zone(zone_id)
    if len(readings) < 48:
        return 0.0

    # Get last 48 hours of the signal
    recent = readings[-48:]
    values = [r[signal] for r in recent if signal in r]

    if len(values) < 24:
        return 0.0

    # Calculate trend: compare last 12h average to previous 12h average
    recent_avg = np.mean(values[-12:])
    previous_avg = np.mean(values[-24:-12])

    if previous_avg == 0:
        return 0.0

    # Rate of change as percentage
    change_rate = abs(recent_avg - previous_avg) / abs(previous_avg)

    # Is it getting worse? (away from baseline)
    all_avg = np.mean(values)
    getting_worse = abs(recent_avg - all_avg) > abs(previous_avg - all_avg)

    if getting_worse:
        score = min(1.0, change_rate * 5)  # 20% change = 1.0 score
    else:
        score = min(0.3, change_rate * 2)  # recovering, lower score

    return round(score, 3)


def _convergence_score(anomalies: list[dict]) -> float:
    """
    Score based on how many different signals show anomalies simultaneously.
    If SST + wind + chlorophyll all spike = very high convergence.
    Single-signal anomaly = low convergence.
    """
    if not anomalies:
        return 0.0

    # Count unique signals involved
    signals_involved = set(a["signal"] for a in anomalies)
    n_signals = len(signals_involved)

    # 1 signal = 0.2, 2 = 0.5, 3 = 0.75, 4+ = 1.0
    convergence_map = {1: 0.2, 2: 0.5, 3: 0.75, 4: 0.9, 5: 1.0}
    score = convergence_map.get(n_signals, 1.0)

    return round(score, 3)


def _historical_score(zone_id: str) -> float:
    """
    Score based on whether this zone has had validated events before.
    Zones with history of real events get slightly higher priority.
    """
    sensitivity_data = db.get_zone_sensitivity(zone_id)
    if not sensitivity_data:
        return 0.5  # neutral

    validated = sensitivity_data.get("validated_alerts", 0)
    total = sensitivity_data.get("total_alerts", 0)

    if total == 0:
        return 0.5  # no history, neutral

    # More validated events = higher base historical score
    validation_rate = validated / total
    score = 0.3 + 0.7 * validation_rate  # 0.3 to 1.0

    return round(score, 3)


def _get_severity(priority_score: float) -> str:
    """Map priority score to severity level."""
    if priority_score >= 0.8:
        return "critical"
    elif priority_score >= 0.6:
        return "high"
    elif priority_score >= 0.4:
        return "medium"
    else:
        return "low"


def _generate_alert_title(zone_name: str, signals: list[str],
                          anomalies: list[dict]) -> str:
    """Generate a descriptive alert title."""
    primary_signal = signals[0] if signals else "unknown"

    signal_names = {
        "sst": "Thermal",
        "chlorophyll": "Chlorophyll",
        "wind_speed": "Wind",
        "ph": "pH",
        "turbidity": "Turbidity",
    }

    if len(signals) >= 3:
        return f"Multi-Signal Anomaly at {zone_name}"
    elif "sst" in signals and any(a["z_score"] > 2 for a in anomalies):
        return f"Thermal Buildup Detected at {zone_name}"
    elif "chlorophyll" in signals:
        return f"Algal Bloom Risk at {zone_name}"
    elif "ph" in signals:
        return f"Acidification Event at {zone_name}"
    elif "wind_speed" in signals:
        return f"Wind Anomaly at {zone_name}"
    else:
        name = signal_names.get(primary_signal, primary_signal.title())
        return f"{name} Anomaly at {zone_name}"


def _generate_alert_description(anomalies: list[dict], scores: dict) -> str:
    """Generate a human-readable alert description."""
    parts = []

    signals_involved = set(a["signal"] for a in anomalies)
    for signal in signals_involved:
        signal_anomalies = [a for a in anomalies if a["signal"] == signal]
        if signal_anomalies:
            worst = max(signal_anomalies, key=lambda x: abs(x["z_score"]))
            direction = "above" if worst["value"] > worst["expected_value"] else "below"
            parts.append(
                f"{signal.upper().replace('_', ' ')}: {worst['value']:.2f} "
                f"({direction} expected {worst['expected_value']:.2f}, "
                f"deviation: {worst['deviation_pct']:.1f}%)"
            )

    desc = "; ".join(parts)

    if scores["trajectory"] > 0.6:
        desc += " | TREND: Getting worse"
    if scores["convergence"] > 0.7:
        desc += f" | CONVERGENCE: {len(signals_involved)} signals agree"

    return desc


def _should_suppress(zone_id: str, priority_score: float,
                     signals: list[str], recent_alerts: list[dict]) -> bool:
    """
    Determine if an alert should be suppressed.
    Suppression reasons:
    1. Cooldown: Similar alert fired recently for same zone
    2. Low confidence: Below confidence floor
    3. Insufficient convergence: Only 1 signal for low-magnitude anomaly
    """
    # Confidence floor
    if priority_score < CONFIDENCE_FLOOR:
        return True

    # Convergence check for low-magnitude anomalies
    if len(signals) < MIN_CONVERGENCE_SIGNALS and priority_score < 0.6:
        return True

    # Cooldown check
    now = datetime.utcnow()
    for alert in recent_alerts:
        if alert["zone_id"] == zone_id:
            try:
                alert_time = datetime.fromisoformat(
                    str(alert.get("created_at", alert["timestamp"])).replace("Z", "")
                ).replace(tzinfo=None)
                hours_since = (now - alert_time).total_seconds() / 3600
                if hours_since < ALERT_COOLDOWN_HOURS:
                    # Allow if new score is significantly higher
                    if priority_score <= alert.get("priority_score", 0) * 1.2:
                        return True
            except (ValueError, TypeError):
                pass

    return False


def evaluate_and_prioritize() -> list[dict]:
    """
    Main decision engine. Evaluates all anomalies and generates
    ranked, prioritized alerts.

    Returns list of alerts sorted by priority_score (descending).
    """
    print("\n[Decision Agent] 🟡 Evaluating anomalies across all zones...")

    zones = db.get_all_zones()
    recent_alerts = db.get_alerts(include_suppressed=True, limit=50)
    all_new_alerts = []

    for zone in zones:
        zone_id = zone["id"]
        zone_name = zone["name"]

        # Get anomalies for this zone
        anomalies = db.get_anomalies(zone_id=zone_id, limit=50)
        if not anomalies:
            continue

        # Get zone sensitivity from Memory Agent
        sensitivity_data = db.get_zone_sensitivity(zone_id)
        sensitivity_modifier = sensitivity_data["sensitivity"] if sensitivity_data else 1.0

        # Group anomalies by time window (cluster nearby anomalies)
        # Use the most recent cluster
        recent_anomalies = anomalies[:24]  # last 24 anomaly records

        if not recent_anomalies:
            continue

        # Get the last reading timestamp as reference
        readings = db.get_all_readings_for_zone(zone_id)
        if readings:
            ref_time = datetime.fromisoformat(str(readings[-1]["timestamp"])).replace(tzinfo=None)
        else:
            ref_time = datetime.utcnow()

        # ─── Calculate 5 scoring dimensions ───
        signals_involved = list(set(a["signal"] for a in recent_anomalies))
        primary_signal = max(
            signals_involved,
            key=lambda s: max(
                (abs(a["z_score"]) for a in recent_anomalies if a["signal"] == s),
                default=0
            )
        )

        scores = {
            "magnitude": _magnitude_score(recent_anomalies),
            "recency": _recency_score(recent_anomalies, ref_time),
            "trajectory": _trajectory_score(zone_id, primary_signal),
            "convergence": _convergence_score(recent_anomalies),
            "historical": _historical_score(zone_id),
        }

        # ─── Weighted priority score ───
        raw_priority = sum(
            DECISION_WEIGHTS[dim] * scores[dim]
            for dim in scores
        )

        # Apply Memory Agent sensitivity modifier
        priority_score = round(min(1.0, raw_priority * sensitivity_modifier), 3)

        # ─── Suppression check ───
        is_suppressed = _should_suppress(
            zone_id, priority_score, signals_involved, recent_alerts
        )

        # ─── Build alert ───
        alert = {
            "zone_id": zone_id,
            "timestamp": recent_anomalies[0]["timestamp"],
            "severity": _get_severity(priority_score),
            "priority_score": priority_score,
            "title": _generate_alert_title(zone_name, signals_involved, recent_anomalies),
            "description": _generate_alert_description(recent_anomalies, scores),
            "signals_involved": json.dumps(signals_involved),
            "magnitude_score": scores["magnitude"],
            "recency_score": scores["recency"],
            "trajectory_score": scores["trajectory"],
            "convergence_score": scores["convergence"],
            "is_suppressed": 1 if is_suppressed else 0,
        }

        # Store in database
        alert_id = db.insert_alert(alert)
        alert["id"] = alert_id
        alert["zone_name"] = zone_name

        status = "🔕 SUPPRESSED" if is_suppressed else f"🔔 {alert['severity'].upper()}"
        print(f"  [{zone_name}] Priority: {priority_score:.3f} — {status}")
        print(f"    Mag={scores['magnitude']:.2f} Rec={scores['recency']:.2f} "
              f"Traj={scores['trajectory']:.2f} Conv={scores['convergence']:.2f} "
              f"Hist={scores['historical']:.2f} × Sens={sensitivity_modifier:.2f}")

        all_new_alerts.append(alert)

    # Sort by priority
    all_new_alerts.sort(key=lambda x: x["priority_score"], reverse=True)

    active = [a for a in all_new_alerts if not a.get("is_suppressed")]
    suppressed = [a for a in all_new_alerts if a.get("is_suppressed")]

    print(f"\n[Decision Agent] ✅ {len(active)} active alerts, {len(suppressed)} suppressed")
    return all_new_alerts


if __name__ == "__main__":
    alerts = evaluate_and_prioritize()
    print("\n--- Top 5 Alerts ---")
    for a in alerts[:5]:
        print(f"  [{a['severity']}] {a['title']} — Score: {a['priority_score']}")

"""
🟣 MEMORY AGENT — Adaptive Intelligence
Self-correcting feedback loop that makes the system smarter over time.

THIS IS THE KEY DIFFERENTIATOR.

How it works:
1. Operator submits feedback on alerts (validated / false_positive)
2. Memory Agent tracks per-zone accuracy (precision rate)
3. Zones with many false positives → sensitivity DECREASES (less noisy)
4. Zones with undetected events → sensitivity INCREASES (more sensitive)
5. Uses Exponential Moving Average for smooth adaptation

Example from the challenge:
- Sundarbans produces chronic chlorophyll noise that mimics bloom signatures
- Memory Agent observes repeated false positives
- Automatically increases threshold for Sundarbans chlorophyll
- No manual intervention needed
"""
from config import (
    SENSITIVITY_EMA_ALPHA,
    DEFAULT_SENSITIVITY,
    MIN_SENSITIVITY,
    MAX_SENSITIVITY,
)
import database as db


def process_feedback(alert_id: int, feedback: str, notes: str = None) -> dict:
    """
    Process operator feedback on an alert and update zone sensitivity.

    Args:
        alert_id: The alert that received feedback
        feedback: 'validated', 'false_positive', or 'uncertain'
        notes: Optional operator notes

    Returns:
        dict with sensitivity change details
    """
    # Update alert with feedback
    alert = db.update_alert_feedback(alert_id, feedback, notes)
    if not alert:
        return {"error": "Alert not found"}

    zone_id = alert["zone_id"]

    # Get current sensitivity data
    sens_data = db.get_zone_sensitivity(zone_id)
    if not sens_data:
        return {"error": "Zone sensitivity not found"}

    old_sensitivity = sens_data["sensitivity"]
    total = sens_data["total_alerts"] + 1
    validated = sens_data["validated_alerts"]
    false_pos = sens_data["false_positive_alerts"]

    # Update counts based on feedback
    if feedback == "validated":
        validated += 1
    elif feedback == "false_positive":
        false_pos += 1
    # 'uncertain' doesn't change counts

    # ─── Calculate new precision rate ───
    total_decided = validated + false_pos
    if total_decided > 0:
        precision = validated / total_decided
    else:
        precision = 0.5  # neutral

    # ─── Adapt sensitivity using EMA ───
    # High precision → increase sensitivity (system is accurate here)
    # Low precision → decrease sensitivity (too many false alarms)
    #
    # Target sensitivity:
    #   precision=1.0 → target=1.2 (stay sensitive, we're accurate)
    #   precision=0.5 → target=1.0 (neutral)
    #   precision=0.0 → target=0.5 (reduce sensitivity, too noisy)

    target_sensitivity = 0.5 + 0.7 * precision  # maps [0,1] → [0.5, 1.2]

    # EMA update: new = alpha * target + (1 - alpha) * old
    new_sensitivity = (
        SENSITIVITY_EMA_ALPHA * target_sensitivity +
        (1 - SENSITIVITY_EMA_ALPHA) * old_sensitivity
    )

    # Clamp to bounds
    new_sensitivity = max(MIN_SENSITIVITY, min(MAX_SENSITIVITY, new_sensitivity))
    new_sensitivity = round(new_sensitivity, 4)

    # ─── Store updates ───
    db.update_zone_sensitivity(
        zone_id=zone_id,
        new_sensitivity=new_sensitivity,
        total=total,
        validated=validated,
        false_pos=false_pos,
        precision=round(precision, 4),
    )

    # Store feedback log for audit trail
    db.insert_feedback_log({
        "alert_id": alert_id,
        "zone_id": zone_id,
        "feedback": feedback,
        "notes": notes,
        "sensitivity_before": old_sensitivity,
        "sensitivity_after": new_sensitivity,
    })

    direction = "↑" if new_sensitivity > old_sensitivity else "↓"
    print(f"[Memory Agent] {zone_id} sensitivity: {old_sensitivity:.3f} {direction} {new_sensitivity:.3f} "
          f"(precision: {precision:.2f}, feedback: {feedback})")

    return {
        "alert_id": alert_id,
        "zone_id": zone_id,
        "feedback": feedback,
        "zone_sensitivity_before": old_sensitivity,
        "zone_sensitivity_after": new_sensitivity,
        "precision_rate": round(precision, 4),
        "total_feedback": total_decided,
        "message": (
            f"Sensitivity {'increased' if new_sensitivity > old_sensitivity else 'decreased'} "
            f"from {old_sensitivity:.3f} to {new_sensitivity:.3f} for zone {zone_id}. "
            f"Current precision rate: {precision:.1%} ({validated} validated / {false_pos} false positives)"
        ),
    }


def get_all_sensitivities() -> list[dict]:
    """Get sensitivity data for all zones."""
    zones = db.get_all_zones()
    result = []

    for zone in zones:
        sens = db.get_zone_sensitivity(zone["id"])
        if sens:
            result.append({
                "zone_id": zone["id"],
                "zone_name": zone["name"],
                "sensitivity": sens["sensitivity"],
                "total_alerts": sens["total_alerts"],
                "validated_alerts": sens["validated_alerts"],
                "false_positive_alerts": sens["false_positive_alerts"],
                "precision_rate": sens["precision_rate"],
                "last_updated": sens["last_updated"],
            })

    return result


def simulate_feedback_history():
    """
    Simulate operator feedback to demonstrate the Memory Agent's
    adaptive behavior. Used for demo/hackathon presentation.

    Scenario:
    - Sundarbans alerts get marked as false_positive (noisy zone)
    - Mumbai alerts get marked as validated (real thermal event)
    - This should cause Sundarbans sensitivity to DROP and Mumbai to STAY HIGH
    """
    print("\n[Memory Agent] 📝 Simulating operator feedback history...")

    alerts = db.get_alerts(include_suppressed=True, limit=100)

    sundarbans_alerts = [a for a in alerts if a["zone_id"] == "zone_sundarbans"]
    mumbai_alerts = [a for a in alerts if a["zone_id"] == "zone_mumbai"]

    # Mark Sundarbans alerts as false positives (it's a noisy zone)
    for alert in sundarbans_alerts[:5]:
        process_feedback(
            alert["id"], "false_positive",
            "Chronic sediment-driven chlorophyll noise, not a real bloom"
        )

    # Mark Mumbai alerts as validated (real thermal event)
    for alert in mumbai_alerts[:3]:
        process_feedback(
            alert["id"], "validated",
            "Confirmed thermal buildup via satellite imagery"
        )

    print("[Memory Agent] ✅ Feedback simulation complete")
    print("  Sundarbans: sensitivity should have DECREASED (noisy zone)")
    print("  Mumbai: sensitivity should have STAYED HIGH or INCREASED (accurate alerts)")

    # Show results
    sensitivities = get_all_sensitivities()
    for s in sensitivities:
        emoji = "🔴" if s["sensitivity"] < 0.7 else "🟡" if s["sensitivity"] < 1.0 else "🟢"
        print(f"  {emoji} {s['zone_name']}: sensitivity={s['sensitivity']:.3f} "
              f"(precision={s['precision_rate']:.2f})")


if __name__ == "__main__":
    simulate_feedback_history()

"""
🔗 CASCADE AGENT — Cross-Zone Correlation & Cascade Prediction
The killer differentiator: predicts which zones will be affected NEXT.

Uses:
1. Geographic proximity (ocean current adjacency)
2. Historical correlation of anomaly patterns
3. Current anomaly state propagation

Output: "Mumbai thermal buildup → Goa Coast likely affected in 3-5 days (78% probability)"
"""
import numpy as np
from datetime import datetime, timezone, timedelta
import database as db


# ═══════════════════════════════════════════════════════════
# OCEAN CURRENT ADJACENCY MATRIX
# Based on real Indian Ocean circulation patterns
# ═══════════════════════════════════════════════════════════

# How connected are zones via ocean currents?
# 1.0 = same zone, 0.0 = no connection
# These reflect real oceanographic patterns:
# - Arabian Sea zones connect via West Indian Coastal Current
# - Bay of Bengal zones connect via East Indian Coastal Current
# - Andaman connects weakly to Bay of Bengal

ADJACENCY_MATRIX = {
    "zone_mumbai": {
        "zone_goa": 0.85,       # Downstream via WICC
        "zone_kochi": 0.55,     # Further downstream
        "zone_kutch": 0.70,     # Close, shared Arabian Sea
        "zone_chennai": 0.20,   # Different basin
        "zone_vizag": 0.15,
        "zone_sundarbans": 0.10,
        "zone_andaman": 0.05,
    },
    "zone_goa": {
        "zone_mumbai": 0.75,    # Upstream
        "zone_kochi": 0.70,     # Downstream
        "zone_kutch": 0.50,
        "zone_chennai": 0.25,
        "zone_vizag": 0.15,
        "zone_sundarbans": 0.10,
        "zone_andaman": 0.05,
    },
    "zone_kochi": {
        "zone_goa": 0.65,
        "zone_mumbai": 0.45,
        "zone_chennai": 0.50,   # Around the tip
        "zone_kutch": 0.30,
        "zone_vizag": 0.30,
        "zone_sundarbans": 0.15,
        "zone_andaman": 0.20,
    },
    "zone_chennai": {
        "zone_vizag": 0.80,     # Connected via EICC
        "zone_kochi": 0.50,
        "zone_sundarbans": 0.55,
        "zone_andaman": 0.45,
        "zone_mumbai": 0.20,
        "zone_goa": 0.25,
        "zone_kutch": 0.10,
    },
    "zone_vizag": {
        "zone_chennai": 0.75,
        "zone_sundarbans": 0.70,  # Along BoB coast
        "zone_andaman": 0.40,
        "zone_kochi": 0.30,
        "zone_mumbai": 0.15,
        "zone_goa": 0.15,
        "zone_kutch": 0.10,
    },
    "zone_sundarbans": {
        "zone_vizag": 0.65,
        "zone_chennai": 0.50,
        "zone_andaman": 0.35,
        "zone_kochi": 0.15,
        "zone_mumbai": 0.10,
        "zone_goa": 0.10,
        "zone_kutch": 0.05,
    },
    "zone_kutch": {
        "zone_mumbai": 0.75,
        "zone_goa": 0.55,
        "zone_kochi": 0.30,
        "zone_chennai": 0.10,
        "zone_vizag": 0.10,
        "zone_sundarbans": 0.05,
        "zone_andaman": 0.05,
    },
    "zone_andaman": {
        "zone_chennai": 0.45,
        "zone_vizag": 0.35,
        "zone_sundarbans": 0.30,
        "zone_kochi": 0.20,
        "zone_goa": 0.05,
        "zone_mumbai": 0.05,
        "zone_kutch": 0.05,
    },
}

# Propagation speed (days) — how long for effects to travel
PROPAGATION_DAYS = {
    (0.7, 1.0): (1, 3),   # High adjacency → 1-3 days
    (0.4, 0.7): (3, 7),   # Medium → 3-7 days
    (0.2, 0.4): (7, 14),  # Low → 1-2 weeks
    (0.0, 0.2): (14, 30), # Minimal → 2-4 weeks
}


def _get_propagation_window(adjacency: float) -> tuple:
    """Get the expected propagation time window based on adjacency strength."""
    for (low, high), days in PROPAGATION_DAYS.items():
        if low <= adjacency < high:
            return days
    return (14, 30)


# ═══════════════════════════════════════════════════════════
# CROSS-ZONE CORRELATION FROM HISTORICAL DATA
# ═══════════════════════════════════════════════════════════

def compute_historical_correlation() -> dict:
    """
    Compute signal correlation between zones from historical data.
    Uses the actual readings database to find patterns.
    """
    zones = db.get_all_zones()
    correlations = {}

    for zone_a in zones:
        za_id = zone_a["id"]
        readings_a = db.get_readings(za_id, limit=2160)  # Full 90 days
        if not readings_a:
            continue

        sst_a = [r["sst"] for r in readings_a]

        for zone_b in zones:
            zb_id = zone_b["id"]
            if za_id == zb_id:
                continue

            readings_b = db.get_readings(zb_id, limit=2160)
            if not readings_b:
                continue

            sst_b = [r["sst"] for r in readings_b]

            # Compute lagged cross-correlation (0 to 7 days)
            min_len = min(len(sst_a), len(sst_b))
            if min_len < 48:
                continue

            best_corr = 0
            best_lag = 0

            for lag_hours in range(0, min(168, min_len // 2), 6):
                a_slice = sst_a[lag_hours:min_len]
                b_slice = sst_b[:min_len - lag_hours]

                if len(a_slice) < 24 or len(b_slice) < 24:
                    continue

                try:
                    corr = np.corrcoef(a_slice[:len(b_slice)], b_slice[:len(a_slice)])[0, 1]
                    if abs(corr) > abs(best_corr):
                        best_corr = corr
                        best_lag = lag_hours
                except Exception:
                    continue

            correlations[f"{za_id}→{zb_id}"] = {
                "source": za_id,
                "target": zb_id,
                "correlation": round(best_corr, 3),
                "lag_hours": best_lag,
                "lag_days": round(best_lag / 24, 1),
            }

    return correlations


# ═══════════════════════════════════════════════════════════
# CASCADE PREDICTION
# ═══════════════════════════════════════════════════════════

def predict_cascade(source_zone_id: str = None) -> list:
    """
    Predict which zones will be affected next based on current anomalies.

    For each zone with active anomalies, compute:
    1. Which adjacent zones are at risk
    2. Probability of cascade
    3. Expected timeline

    Returns list of cascade predictions.
    """
    # Get current alerts (source of anomalies)
    alerts = db.get_alerts(include_suppressed=False, limit=50)
    if not alerts:
        return []

    # If source specified, filter to that zone
    if source_zone_id:
        alerts = [a for a in alerts if a["zone_id"] == source_zone_id]

    # Group alerts by zone
    zone_alerts = {}
    for alert in alerts:
        zid = alert["zone_id"]
        if zid not in zone_alerts:
            zone_alerts[zid] = []
        zone_alerts[zid].append(alert)

    cascades = []
    zones = {z["id"]: z for z in db.get_all_zones()}

    for source_zone, source_alerts in zone_alerts.items():
        if source_zone not in ADJACENCY_MATRIX:
            continue

        # Get the strongest alert for this zone
        max_priority = max(a["priority_score"] for a in source_alerts)
        max_alert = max(source_alerts, key=lambda a: a["priority_score"])

        # Parse signals involved
        import json
        signals = max_alert.get("signals_involved", "[]")
        if isinstance(signals, str):
            signals = json.loads(signals)

        # Check adjacent zones
        for target_zone, adjacency in ADJACENCY_MATRIX[source_zone].items():
            if adjacency < 0.15:
                continue

            # Calculate cascade probability
            # Factors: adjacency strength, alert severity, number of signals
            base_prob = adjacency * 0.6  # Geography-based probability
            severity_boost = max_priority * 0.25  # Higher severity → more likely to spread
            signal_boost = min(len(signals), 3) * 0.05  # Multi-signal → more systemic

            cascade_probability = min(0.95, base_prob + severity_boost + signal_boost)

            if cascade_probability < 0.20:
                continue

            # Get propagation timeline
            min_days, max_days = _get_propagation_window(adjacency)

            # Determine which signals might cascade
            cascading_signals = []
            for signal in signals:
                if signal in ["sst", "chlorophyll"]:
                    # Ocean-borne signals cascade via currents
                    cascading_signals.append(signal)
                elif signal == "wind_speed":
                    # Wind patterns are regional
                    if adjacency > 0.5:
                        cascading_signals.append(signal)

            if not cascading_signals:
                cascading_signals = signals[:1]  # At least one signal

            # Check if target zone already has anomalies (cascade may be in progress)
            target_alerts = [a for a in alerts if a["zone_id"] == target_zone]
            cascade_in_progress = len(target_alerts) > 0

            source_name = zones.get(source_zone, {}).get("name", source_zone)
            target_name = zones.get(target_zone, {}).get("name", target_zone)

            cascades.append({
                "source_zone_id": source_zone,
                "source_zone_name": source_name,
                "target_zone_id": target_zone,
                "target_zone_name": target_name,
                "cascade_probability": round(cascade_probability, 2),
                "adjacency_strength": adjacency,
                "propagation_days_min": min_days,
                "propagation_days_max": max_days,
                "cascading_signals": cascading_signals,
                "source_severity": max_alert["severity"],
                "source_priority_score": round(max_priority, 3),
                "cascade_in_progress": cascade_in_progress,
                "mechanism": _get_cascade_mechanism(source_zone, target_zone),
                "recommended_action": _get_recommendation(cascade_probability, target_name),
            })

    # Sort by probability
    cascades.sort(key=lambda c: c["cascade_probability"], reverse=True)

    return cascades


def _get_cascade_mechanism(source: str, target: str) -> str:
    """Get human-readable explanation of how the cascade propagates."""
    mechanisms = {
        ("zone_mumbai", "zone_goa"): "West Indian Coastal Current (southward flow)",
        ("zone_goa", "zone_kochi"): "West Indian Coastal Current (monsoon-driven)",
        ("zone_mumbai", "zone_kutch"): "Arabian Sea tidal exchange",
        ("zone_chennai", "zone_vizag"): "East Indian Coastal Current (northward)",
        ("zone_vizag", "zone_sundarbans"): "Bay of Bengal coastal circulation",
        ("zone_chennai", "zone_andaman"): "Bay of Bengal deep water exchange",
        ("zone_vizag", "zone_chennai"): "East Indian Coastal Current (southward, winter)",
        ("zone_sundarbans", "zone_vizag"): "Bay of Bengal counter-current",
    }

    key = (source, target)
    if key in mechanisms:
        return mechanisms[key]

    # Generic mechanism based on regions
    zones = {z["id"]: z for z in db.get_all_zones()}
    src_region = zones.get(source, {}).get("region", "")
    tgt_region = zones.get(target, {}).get("region", "")

    if src_region == tgt_region:
        return f"Shared {src_region} basin circulation"
    return "Cross-basin atmospheric teleconnection"


def _get_recommendation(probability: float, target_name: str) -> str:
    """Generate action recommendation based on cascade probability."""
    if probability >= 0.70:
        return f"URGENT: Deploy monitoring buoys at {target_name}. Issue pre-emptive advisory to local fisheries."
    elif probability >= 0.50:
        return f"WATCH: Increase monitoring frequency at {target_name}. Notify regional coordinator."
    elif probability >= 0.30:
        return f"MONITOR: Track signals at {target_name} for early confirmation."
    return f"LOW RISK: Standard monitoring at {target_name} sufficient."


# ═══════════════════════════════════════════════════════════
# ZONE RISK NETWORK — For visualization
# ═══════════════════════════════════════════════════════════

def get_cascade_network() -> dict:
    """
    Get the full zone connectivity network for visualization.
    Returns nodes (zones) and edges (connections + cascade risk).
    """
    zones = db.get_all_zones()
    cascades = predict_cascade()

    nodes = []
    for z in zones:
        anomalies = db.get_anomalies(zone_id=z["id"], limit=5)
        risk_score = 0
        if anomalies:
            risk_score = min(1.0, sum(abs(a["anomaly_score"]) for a in anomalies) / len(anomalies))

        # Check if this zone is a cascade target
        incoming_risk = sum(
            c["cascade_probability"] for c in cascades
            if c["target_zone_id"] == z["id"]
        )

        nodes.append({
            "id": z["id"],
            "name": z["name"],
            "lat": z["lat"],
            "lng": z["lng"],
            "region": z["region"],
            "own_risk": round(risk_score, 3),
            "incoming_cascade_risk": round(min(1.0, incoming_risk), 3),
            "total_risk": round(min(1.0, risk_score + incoming_risk * 0.5), 3),
        })

    edges = []
    for source in ADJACENCY_MATRIX:
        for target, strength in ADJACENCY_MATRIX[source].items():
            if strength >= 0.3:  # Only significant connections
                # Check if there's an active cascade on this edge
                active = any(
                    c["source_zone_id"] == source and c["target_zone_id"] == target
                    for c in cascades
                )
                edges.append({
                    "source": source,
                    "target": target,
                    "strength": strength,
                    "active_cascade": active,
                })

    return {
        "nodes": nodes,
        "edges": edges,
        "active_cascades": len(cascades),
    }

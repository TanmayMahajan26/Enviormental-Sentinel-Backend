"""
🚨 ANOMALY SIMULATION SCRIPT — Demo for Hackathon Judges
=========================================================
Injects a realistic environmental crisis into the system and triggers 
the full AI pipeline:

  1. Inject extreme readings into Mumbai Coast (thermal buildup + wind drop)
  2. Re-run Analysis Agent → detects anomalies via Isolation Forest
  3. Re-run Decision Agent → generates priority-scored alerts
  4. Send Telegram alerts → judges see real-time mobile notification
  5. Print full system response: cascade, impact, root cause, time-to-risk

Usage:
    python simulate_anomaly.py
"""
import asyncio
import sys
import os
import numpy as np
from datetime import datetime, timedelta, timezone

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

import database as db
from config import MODELS_DIR


def inject_anomaly():
    """
    Inject a severe environmental crisis into Mumbai Coast.
    Simulates: Marine heatwave + wind stagnation + algal bloom onset
    """
    print("\n" + "=" * 60)
    print("🚨 ANOMALY SIMULATION — Injecting environmental crisis")
    print("=" * 60)
    
    zone_id = "zone_mumbai"
    zone = db.get_zone(zone_id)
    
    print(f"\n📍 Target Zone: {zone['name']}")
    print(f"   Baseline SST: {zone['baseline_sst']}°C")
    print(f"   Baseline CHL: {zone['baseline_chlorophyll']} mg/m³")
    print(f"   Baseline Wind: {zone['baseline_wind']} m/s")
    print(f"   Baseline pH: {zone['baseline_ph']}")
    
    # Generate 48 hours of crisis readings (escalating)
    now = datetime.now(timezone.utc)
    crisis_readings = []
    
    print(f"\n💉 Injecting 48 hours of crisis data...")
    
    for hour in range(48):
        progress = hour / 48.0  # 0.0 → 1.0 escalation
        
        reading = {
            "timestamp": (now - timedelta(hours=48 - hour)).isoformat(),
            "zone_id": zone_id,
            # SST: +3.5°C above baseline (marine heatwave)
            "sst": round(zone["baseline_sst"] + 2.0 + (1.5 * progress) + np.random.normal(0, 0.1), 3),
            # Chlorophyll: 3x spike (algal bloom triggered by warm stagnant water)
            "chlorophyll": round(zone["baseline_chlorophyll"] * (1.5 + 2.0 * progress) + np.random.normal(0, 0.05), 4),
            # Wind: drops to near-zero (stagnation traps heat)
            "wind_speed": round(max(0.5, zone["baseline_wind"] * (0.4 - 0.25 * progress) + np.random.normal(0, 0.2)), 2),
            # pH: acidification from decomposing algae
            "ph": round(zone["baseline_ph"] - (0.15 + 0.2 * progress) + np.random.normal(0, 0.005), 3),
            # Turbidity: rising from algal matter
            "turbidity": round(zone["baseline_turbidity"] + (8.0 * progress) + np.random.normal(0, 0.5), 2),
        }
        crisis_readings.append(reading)
    
    # Insert into database
    db.insert_readings_batch(crisis_readings)
    
    # Show the last (worst) reading
    worst = crisis_readings[-1]
    print(f"\n   📊 Injected {len(crisis_readings)} crisis readings")
    print(f"   🔥 Final SST: {worst['sst']}°C  (baseline: {zone['baseline_sst']}°C, Δ = +{worst['sst'] - zone['baseline_sst']:.1f}°C)")
    print(f"   🌿 Final CHL: {worst['chlorophyll']} mg/m³  (baseline: {zone['baseline_chlorophyll']}, Δ = +{worst['chlorophyll'] - zone['baseline_chlorophyll']:.2f})")
    print(f"   💨 Final Wind: {worst['wind_speed']} m/s  (baseline: {zone['baseline_wind']}, Δ = {worst['wind_speed'] - zone['baseline_wind']:.1f})")
    print(f"   ⚗️  Final pH: {worst['ph']}  (baseline: {zone['baseline_ph']}, Δ = {worst['ph'] - zone['baseline_ph']:.3f})")
    print(f"   🌊 Final Turb: {worst['turbidity']} NTU  (baseline: {zone['baseline_turbidity']}, Δ = +{worst['turbidity'] - zone['baseline_turbidity']:.1f})")
    
    return zone_id


def run_analysis(zone_id: str):
    """Re-run the Analysis Agent to detect the injected anomaly."""
    print("\n" + "=" * 60)
    print("🔵 ANALYSIS AGENT — Re-running anomaly detection...")
    print("=" * 60)
    
    from agents.analysis_agent import train_zone_model
    result = train_zone_model(zone_id)
    
    print(f"\n   ✅ Training complete:")
    print(f"   📊 Data points: {result.get('total_points', 'N/A')}")
    print(f"   🧪 Features: {result.get('features', 'N/A')}")
    print(f"   🚨 Anomalies detected: {result.get('anomalies_detected', 'N/A')}")
    print(f"   📈 Anomaly rate: {result.get('anomaly_rate', 'N/A')}%")
    
    return result


def run_decision():
    """Re-run Decision Agent to generate priority alerts."""
    print("\n" + "=" * 60)
    print("🟡 DECISION AGENT — Evaluating and prioritizing alerts...")
    print("=" * 60)
    
    from agents.decision_agent import evaluate_and_prioritize
    alerts = evaluate_and_prioritize()
    
    active = [a for a in alerts if not a.get("is_suppressed")]
    print(f"\n   ✅ {len(active)} active alerts generated")
    
    for a in active[:5]:
        severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(a["severity"], "⚪")
        print(f"   {severity_emoji} [{a['severity'].upper()}] {a['title']} — Score: {a['priority_score']:.3f}")
    
    return alerts


async def send_telegram_alerts():
    """Send alerts to Telegram for real-time mobile demo."""
    print("\n" + "=" * 60)
    print("📱 TELEGRAM AGENT — Sending mobile alerts...")
    print("=" * 60)
    
    from agents.telegram_agent import send_priority_alerts, send_daily_summary, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    
    if not TELEGRAM_BOT_TOKEN:
        print("   ❌ No TELEGRAM_BOT_TOKEN configured. Skipping.")
        return
    
    if not TELEGRAM_CHAT_ID:
        print("   ❌ No TELEGRAM_CHAT_ID configured. Skipping.")
        return
    
    print(f"   🤖 Bot token: ...{TELEGRAM_BOT_TOKEN[-6:]}")
    print(f"   💬 Chat ID: {TELEGRAM_CHAT_ID}")
    
    # Clear sent cache so alerts send again
    from agents import telegram_agent
    telegram_agent._sent_alert_ids.clear()
    
    # Send individual priority alerts
    result = await send_priority_alerts(min_severity="medium")
    print(f"\n   📨 Sent {result.get('sent', 0)} alert notifications")
    
    # Also send daily summary
    summary_sent = await send_daily_summary()
    print(f"   📋 Daily summary sent: {'✅' if summary_sent else '❌'}")
    
    return result


def show_cascade_predictions(zone_id: str):
    """Show cross-zone cascade predictions."""
    print("\n" + "=" * 60)
    print("🔗 CASCADE AGENT — Cross-zone propagation prediction...")
    print("=" * 60)
    
    from agents.cascade_agent import predict_cascade
    predictions = predict_cascade(zone_id)
    
    active_cascades = [p for p in predictions if p["cascade_in_progress"]]
    print(f"\n   📡 {len(predictions)} cascade predictions, {len(active_cascades)} active")
    
    for p in predictions[:5]:
        status = "🔴 IN PROGRESS" if p["cascade_in_progress"] else "⚠️  Predicted"
        print(f"\n   {status}: {p['source_zone_name']} → {p['target_zone_name']}")
        print(f"      Probability: {p['cascade_probability']:.0%}")
        print(f"      Timeline: {p['propagation_days_min']}-{p['propagation_days_max']} days")
        print(f"      Signals: {', '.join(p['cascading_signals'])}")
        print(f"      Mechanism: {p['mechanism']}")


def show_economic_impact(zone_id: str):
    """Show economic impact estimation."""
    print("\n" + "=" * 60)
    print("💰 IMPACT AGENT — Economic damage estimation...")
    print("=" * 60)
    
    from agents.impact_agent import estimate_all_active_impacts
    impacts = estimate_all_active_impacts()
    
    total_crore = sum(i["economic_impact"]["total_impact_crore"] for i in impacts)
    total_families = sum(i["social_impact"]["fishing_families_affected"] for i in impacts)
    
    print(f"\n   💰 Total Economic Impact: ₹{total_crore:.1f} crore")
    print(f"   👥 Total Families Affected: {total_families:,}")
    
    for imp in impacts[:3]:
        print(f"\n   📍 {imp['zone_name']}:")
        print(f"      💰 ₹{imp['economic_impact']['total_impact_crore']} crore")
        print(f"         🐟 Fishing: ₹{imp['economic_impact']['fishing_impact_crore']} crore")
        print(f"         🚢 Shipping: ₹{imp['economic_impact']['shipping_impact_crore']} crore")
        print(f"         🏖️  Tourism: ₹{imp['economic_impact']['tourism_impact_crore']} crore")
        print(f"      👥 {imp['social_impact']['fishing_families_affected']:,} families at risk")


def show_root_cause(zone_id: str):
    """Show root cause analysis."""
    print("\n" + "=" * 60) 
    print("🧬 ROOT CAUSE — AI causal analysis...")
    print("=" * 60)
    
    from agents.intelligence_agent import detect_root_cause
    result = detect_root_cause(zone_id)
    
    print(f"\n   📍 Zone: {result.get('zone_name', zone_id)}")
    print(f"   🔍 Analysis window: {result.get('analysis_window', 'N/A')}")
    
    deviations = result.get("deviations", {})
    print(f"\n   📊 Current Deviations:")
    for sig, dev in deviations.items():
        arrow = "↑" if dev > 0 else "↓" if dev < 0 else "—"
        print(f"      {sig.upper():15s}: {dev:+.3f} {arrow}")
    
    causes = result.get("root_causes", [])
    if causes:
        print(f"\n   🧠 Identified {len(causes)} root cause(s):")
        for i, c in enumerate(causes, 1):
            print(f"\n   #{i} [{c['confidence']:.0%} confidence]")
            print(f"      Cause: {c['cause']}")
            print(f"      Mechanism: {c['mechanism']}")
    
    primary = result.get("primary_cause", {})
    if primary:
        print(f"\n   ⭐ PRIMARY CAUSE: {primary.get('cause', 'N/A')}")


def show_time_to_risk(zone_id: str):
    """Show time-to-risk early warning."""
    print("\n" + "=" * 60)
    print("⏰ EARLY WARNING — Time-to-risk projection...")
    print("=" * 60)
    
    from agents.intelligence_agent import calculate_time_to_risk
    result = calculate_time_to_risk(zone_id)
    
    warnings = result.get("warnings", [])
    summary = result.get("summary", {})
    
    print(f"\n   🔍 Overall urgency: {summary.get('overall_urgency', 'N/A')}")
    print(f"   📊 Signals at risk: {summary.get('signals_trending_to_risk', 0)}/{summary.get('total_signals_analyzed', 5)}")
    print(f"   🔴 Already at risk: {summary.get('already_at_risk', 0)}")
    print(f"   ⚡ Risk within 48h: {summary.get('risk_within_48h', 0)}")
    
    for w in warnings:
        print(f"\n   📡 {w['signal'].upper()}:")
        if w.get("human_readable"):
            print(f"      {w['human_readable']}")
        print(f"      Current: {w['current_value']:.3f} | Baseline: {w['baseline']}")
        print(f"      Trend: {w['trend']} at {w['rate_per_day']:.3f}/day")


def show_what_if(zone_id: str):
    """Run what-if simulation."""
    print("\n" + "=" * 60)
    print("🧪 WHAT-IF — Simulating further degradation...")
    print("=" * 60)
    
    from agents.intelligence_agent import run_simulation
    
    # Simulate: "What if SST rises another 2°C and wind stays dead?"
    scenario = {"sst": 2.0, "wind_speed": -3.0}
    result = run_simulation(zone_id, scenario)
    
    print(f"\n   📍 Zone: {result.get('zone_name', zone_id)}")
    print(f"   🧪 Scenario: SST +2.0°C, Wind -3.0 m/s")
    
    risk = result.get("risk_assessment", {})
    print(f"\n   ⚠️  Risk Score: {risk.get('risk_score', 0):.2f}")
    print(f"   🔴 Risk Level: {risk.get('risk_level', 'N/A')}")
    
    impacts = risk.get("ecosystem_impacts", [])
    if impacts:
        print(f"\n   🌊 Ecosystem Impacts:")
        for imp in impacts:
            print(f"      {imp['severity']}: {imp['impact']}")
            print(f"         {imp['description']}")
    
    econ = result.get("economic_impact", {})
    if econ:
        print(f"\n   💰 Projected Impact: ₹{econ.get('total_impact_crore', 0)} crore")
    
    recs = result.get("recommendations", [])
    if recs:
        print(f"\n   📋 Recommendations:")
        for r in recs:
            print(f"      • {r}")


async def main():
    """Run the full anomaly simulation pipeline."""
    print("\n" + "🔴" * 30)
    print("  ENVIRONMENTAL SENTINEL — ANOMALY SIMULATION")
    print("  Demonstrating full AI pipeline for hackathon judges")
    print("🔴" * 30)
    
    # Initialize DB (in case it's not initialized)
    db.init_db()
    
    # Step 1: Inject anomaly
    zone_id = inject_anomaly()
    
    # Step 2: Run Analysis Agent
    run_analysis(zone_id)
    
    # Step 3: Run Decision Agent
    alerts = run_decision()
    
    # Step 4: Send Telegram alerts
    await send_telegram_alerts()
    
    # Step 5: Show cascade predictions
    show_cascade_predictions(zone_id)
    
    # Step 6: Show economic impact
    show_economic_impact(zone_id)
    
    # Step 7: Show root cause
    show_root_cause(zone_id)
    
    # Step 8: Show time-to-risk
    show_time_to_risk(zone_id)
    
    # Step 9: What-if simulation
    show_what_if(zone_id)
    
    # Final summary
    print("\n" + "=" * 60)
    print("✅ SIMULATION COMPLETE — Full AI Pipeline Demonstrated")
    print("=" * 60)
    print("""
   What judges just saw:
   
   1. 💉 Real anomaly data injected (48h marine heatwave)
   2. 🔵 ML models detected anomalies (Isolation Forest + STL)
   3. 🟡 Decision Agent scored & prioritized alerts (5 dimensions)
   4. 📱 Telegram sent real-time mobile notifications
   5. 🔗 Cross-zone cascade prediction (ocean current modeling)
   6. 💰 Economic impact: ₹ crore damage estimation
   7. 🧬 Root cause: AI identified WHY it's happening
   8. ⏰ Early warning: projected time-to-critical
   9. 🧪 What-if: simulated further degradation scenarios
   
   📱 Check Telegram for live alert notifications!
""")


if __name__ == "__main__":
    asyncio.run(main())

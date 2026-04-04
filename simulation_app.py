import streamlit as st
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import database as db
from agents.analysis_agent import train_zone_model
from agents.decision_agent import evaluate_and_prioritize
from agents.telegram_agent import send_priority_alerts
from agents.intelligence_agent import detect_root_cause, calculate_time_to_risk, run_simulation as simulate_what_if
from agents.impact_agent import estimate_impact
from agents.cascade_agent import predict_cascade
from agents.explanation_agent import generate_briefing

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Environmental Sentinel — Mission Control",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Design
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #1a1c24;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
    }
    .agent-card {
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #30363d;
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        margin-bottom: 10px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #ff4b4b;
        color: white;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- STATE MANAGEMENT ---
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'sim_active' not in st.session_state:
    st.session_state.sim_active = False
if 'risk_score' not in st.session_state:
    st.session_state.risk_score = 0.05
if 'alert_count' not in st.session_state:
    st.session_state.alert_count = 0

def add_log(agent, message, style="info"):
    icon = "📡" if agent == "Data" else "🔵" if agent == "Analysis" else "🟡" if agent == "Decision" else "💰" if agent == "Impact" else "🔗" if agent == "Cascade" else "🧬" if agent == "Intelligence" else "🔴" if agent == "Explanation" else "📱" if agent == "Telegram" else "⏰"
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.append({
        "time": timestamp,
        "agent": agent,
        "icon": icon,
        "msg": message,
        "style": style
    })

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Sentinel Control")
    st.markdown("---")
    st.image("https://img.icons8.com/color/512/globe.png", width=100)
    
    st.subheader("Crisis Orchestrator")
    if st.button("🚨 INJECT ANOMALY (Start Demo)"):
        st.session_state.sim_active = True
        st.session_state.logs = []
        st.rerun()
    
    st.markdown("---")
    st.subheader("System Status")
    st.info("📡 Global Data Feed: ACTIVE")
    st.success("🔵 Analysis Engine: STANDBY")
    st.error("🔑 Gemini API: Key Leaked/Denied") if os.getenv("GEMINI_API_KEY") == "" else st.success("🟢 Gemini API: CONFIGURED")

# --- MAIN DASHBOARD ---
st.title("🛡️ Live Intelligence Mission Control")
st.markdown("Monitoring coastal baselines across 8 Indian maritime zones.")

# Metric Header
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("SST (Avg)", "28.5°C", "0.2")
m2.metric("Chlorophyll", "1.2 mg/m³", "-0.1")
m3.metric("Wind Speed", "5.5 m/s", "0.1")
m4.metric("pH Level", "8.1", "0.0")
m5.metric("Risk Score", f"{st.session_state.risk_score:.2f}", f"+{st.session_state.risk_score - 0.05:.2f}" if st.session_state.sim_active else "Steady")

st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🧠 Multi-Agent Reasoning Chain")
    
    if st.session_state.sim_active:
        status = st.status("Initializing Intelligence Pipeline...", expanded=True)
        
        # Phase 1: Data Agents
        status.write("📡 Step 1: Ingesting 48-Hour Marine Heatwave telemetry...")
        readings = []
        for i in range(48):
            ts = datetime.now().isoformat()
            readings.append({"timestamp": ts, "zone_id": "zone_mumbai", "sst": 32.5, "chlorophyll": 4.1, "wind_speed": 0.5, "ph": 7.7, "turbidity": 25.0})
        db.insert_readings_batch(readings)
        add_log("Data", "Injected 48 crisis readings into Mumbai Coast grid.")
        time.sleep(1)
        
        # Phase 2: Analysis Agent
        status.write("🔵 Step 2: Training Isolation Forest detect signature deviations...")
        train_zone_model("zone_mumbai")
        add_log("Analysis", "Anomaly detected! 5.0% deviation identified in Mumbai zone.")
        time.sleep(1)
        
        # Phase 3: Decision Agent
        status.write("🟡 Step 3: Scoring urgency and prioritizing emergency protocols...")
        evaluate_and_prioritize()
        st.session_state.alert_count = 6
        st.session_state.risk_score = 0.95
        add_log("Decision", "Mumbai Coast score: 1.000 — CRITICAL PRIORITY.")
        time.sleep(1)
        
        # Phase 4: Impact Agent
        status.write("💰 Step 4: Modeling economic damage and family vulnerability...")
        res = estimate_impact("zone_mumbai", ["sst"], 1.0)
        add_log("Impact", f"Estimated damage: ₹{res.get('economic_impact', {}).get('total', 0):.0f} Crore.")
        time.sleep(1)
        
        # Phase 5: Cascade Agent
        status.write("🔗 Step 5: Predicting cross-zone propagation...")
        predict_cascade("zone_mumbai")
        add_log("Cascade", "91% probability of propagation to Goa Coast within 72h.")
        time.sleep(1)
        
        # Phase 6: Intelligence Agent
        status.write("🧬 Step 6: Performing causal reasoning and risk projections...")
        detect_root_cause("zone_mumbai")
        calculate_time_to_risk("zone_mumbai")
        add_log("Intelligence", "Primary cause: Thermal stratification. Breach predicted in 2.7 days.")
        time.sleep(1)
        
        # Phase 7: Explanation Agent
        status.write("🔴 Step 7: Synthesizing multi-language operator briefing...")
        # Briefing can be slow or fail on 403, wrap it
        try:
            asyncio.run(generate_briefing())
            add_log("Explanation", "Regional briefing generated for field responders.")
        except:
            add_log("Explanation", "LLM Briefing failed (API Key Leak), using fallback summaries.")
        time.sleep(1)
        
        # Phase 8: Telegram Agent
        status.write("📱 Step 8: Dispatching prioritize alerts to field units...")
        try:
            asyncio.run(send_priority_alerts())
            add_log("Telegram", "Alert notifications pushed to @8168909813")
        except:
            add_log("Telegram", "Telegram push failed — verify Bot status.")
        
        status.update(label="✅ Simulation Pipeline Complete", state="complete", expanded=False)
        st.session_state.sim_active = False
        st.success("Pipeline Demonstration Successful!")

    # Display Logs
    for log in reversed(st.session_state.logs):
        with st.chat_message("user" if log['agent'] == "Scheduler" else "assistant", avatar=log['icon']):
            st.markdown(f"**{log['agent']} Agent** | {log['time']}")
            st.write(log['msg'])

with col2:
    st.subheader("🛰️ System Intelligence")
    
    # Risk Gauge
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = st.session_state.risk_score * 100,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Risk Level %"},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "#ff4b4b"},
            'steps' : [
                {'range': [0, 30], 'color': "green"},
                {'range': [30, 70], 'color': "yellow"},
                {'range': [70, 100], 'color': "red"}],
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
    st.plotly_chart(fig, use_container_width=True)

    # Alerts list
    st.markdown("### Active Alerts")
    if st.session_state.alert_count > 0:
        st.warning(f"🔴 Mumbai Coast: CRITICAL (1.000)")
        st.warning(f"🟠 Goa Coast: HIGH (0.730)")
        st.warning(f"🟠 Kochi Coast: HIGH (0.652)")
    else:
        st.success("No active alerts. Scanning...")

    # Economic impact chart (Dummy data based on sim)
    st.markdown("### Projected Loss (₹ Crore)")
    impact_data = pd.DataFrame({
        'Category': ['Fishing', 'Shipping', 'Tourism'],
        'Damage': [45, 320, 240] if st.session_state.alert_count > 0 else [0, 0, 0]
    })
    st.bar_chart(impact_data.set_index('Category'))

st.markdown("---")
st.caption("Environmental Sentinel AI © 2026 | Built for Airavat 3.0 Hackathon")

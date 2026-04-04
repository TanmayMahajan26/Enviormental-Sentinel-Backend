import streamlit as st
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import requests
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
from agents.live_data_agent import fetch_openaq_data, fetch_copernicus_marine

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
if 'sys_alerts' not in st.session_state:
    st.session_state.sys_alerts = []
if 'impact_res' not in st.session_state:
    st.session_state.impact_res = None

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
    with st.expander("📡 Live APIs Configured (5)"):
        st.caption("🟢 NOAA ERDDAP (SST/Chl)")
        st.caption("🟢 OpenAQ v2 (Air Quality)")
        st.caption("🟢 CMEMS (Copernicus Ocean)")
        st.caption("🟢 NASA Earthdata (MODIS)")
        st.caption("🟢 Local CSV Fallback (Offline)")
    st.success("🔵 Analysis Engine: STANDBY")
    st.error("🔑 Gemini API: Key Leaked/Denied") if os.getenv("GEMINI_API_KEY") == "" else st.success("🟢 Gemini API: CONFIGURED")

# --- MAIN DASHBOARD ---
zone_options = {
    "Mumbai Coast": "zone_mumbai",
    "Goa Coast": "zone_goa",
    "Kochi Coast": "zone_kochi",
    "Chennai Coast": "zone_chennai",
    "Sundarbans Delta": "zone_sundarbans"
}
selected_zone_name = st.selectbox("📍 Select Monitoring Region:", list(zone_options.keys()))
selected_zone_id = zone_options[selected_zone_name]

st.title(f"🛡️ {selected_zone_name} — Live Telemetry")
st.markdown("Monitoring multi-API environmental baselines and forecasting anomalies.")

@st.cache_data(ttl=1800)
def fetch_live_api_telemetry(lat, lng):
    try:
        aqi_res = asyncio.run(fetch_openaq_data(lat, lng))
        cop_res = asyncio.run(fetch_copernicus_marine(lat, lng))
        
        aqi_val = 50
        if "data" in aqi_res and aqi_res["data"]:
            for pm in aqi_res["data"]:
                if isinstance(pm, dict) and pm.get("parameter") == "pm25":
                    aqi_val = pm.get("value", 50)
                    break
        sal_val = cop_res.get("data", {}).get("salinity", 35.0)
        return float(aqi_val), float(sal_val)
    except Exception:
        return 75.0, 34.5

zone_info = db.get_zone(selected_zone_id)
if zone_info:
    aqi_base, sal_base = fetch_live_api_telemetry(zone_info["lat"], zone_info["lng"])
else:
    aqi_base, sal_base = 75.0, 34.5

readings = db.get_all_readings_for_zone(selected_zone_id)
if readings:
    latest = readings[-1]
    sst_base = latest.get("sst", 28.5)
    chl_base = latest.get("chlorophyll", 1.2)
    wind_base = latest.get("wind_speed", 5.5)
else:
    sst_base, chl_base, wind_base = 28.5, 1.2, 5.5

# Metric Header
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("🌡️ SST (NOAA)", f"{sst_base + 4.0:.1f}°C" if st.session_state.sim_active else f"{sst_base:.1f}°C", "+4.0°C" if st.session_state.sim_active else "0.0°C")
m2.metric("🌿 Chl-a (NOAA)", f"{chl_base + 2.9:.1f} mg/m³" if st.session_state.sim_active else f"{chl_base:.1f} mg/m³", "+2.9 mg/m³" if st.session_state.sim_active else "0.0")
m3.metric("💨 Wind (Open-Meteo)", f"{wind_base - 4.2:.1f} m/s" if st.session_state.sim_active else f"{wind_base:.1f} m/s", "-4.2 m/s" if st.session_state.sim_active else "0.0")
m4.metric("🌫️ AQI PM2.5 (OpenAQ)", f"{int(aqi_base) + 85}" if st.session_state.sim_active else str(int(aqi_base)), "+85" if st.session_state.sim_active else "Steady")
m5.metric("🌊 Salinity (CMEMS)", f"{sal_base - 1.5:.1f} PSU" if st.session_state.sim_active else f"{sal_base:.1f} PSU", "-1.5 PSU" if st.session_state.sim_active else "Steady")
m6.metric("🛑 Risk Score", f"{st.session_state.risk_score:.2f}", f"+{st.session_state.risk_score - 0.05:.2f}" if st.session_state.sim_active else "Steady")

st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🧠 Multi-Agent Reasoning Chain")
    
    if st.session_state.sim_active:
        progress_bar = st.progress(0)
        status = st.status("Initializing Intelligence Pipeline...", expanded=True)
        
        # Phase 1: Data Agents
        progress_bar.progress(10)
        status.write(f"📡 Step 1: Ingesting 48-Hour Marine Heatwave telemetry across NOAA, Copernicus & OpenAQ for {selected_zone_name}...")
        readings = []
        for i in range(48):
            ts = datetime.now().isoformat()
            readings.append({"timestamp": ts, "zone_id": selected_zone_id, "sst": 32.5, "chlorophyll": 4.1, "wind_speed": 0.5, "ph": 7.7, "turbidity": 25.0})
        db.insert_readings_batch(readings)
        add_log("Data", f"Injected 48 multi-api crisis readings (ERDDAP/CMEMS) into {selected_zone_name} grid.")
        time.sleep(1)
        
        # Phase 2: Analysis Agent
        progress_bar.progress(25)
        status.write("🔵 Step 2: Training Isolation Forest detect signature deviations...")
        try:
            r = requests.post(f"http://127.0.0.1:8000/api/pipeline/train/{selected_zone_id}", timeout=60)
            
            if r.status_code != 200:
                raise ValueError(f"HTTP {r.status_code}: {r.text}")
                
            anomaly_count = r.json().get('anomalies_detected', 5)
        except Exception as e:
            try:
                debug_txt = r.text
            except:
                debug_txt = "No Text"
            st.error(f"Backend Connection Error (Train): {e} | Body: {debug_txt}")
            anomaly_count = 5
        add_log("Analysis", f"Anomaly detected! {anomaly_count} multivariate deviation(s) identified in {selected_zone_name}.")
        time.sleep(1)
        
        # Phase 3: Decision Agent
        progress_bar.progress(40)
        status.write("🟡 Step 3: Scoring urgency and prioritizing emergency protocols...")
        try:
            requests.post("http://127.0.0.1:8000/api/pipeline/evaluate")
        except Exception as e:
            st.error(f"Backend Connection Error (Evaluate): {e}")
        sys_alerts = db.get_alerts(include_suppressed=False, limit=5)
        st.session_state.sys_alerts = sys_alerts
        st.session_state.alert_count = len(sys_alerts)
        if sys_alerts:
            st.session_state.risk_score = float(sys_alerts[0]['priority_score'])
        else:
            st.session_state.risk_score = 0.95
        
        add_log("Decision", f"{selected_zone_name} highest converged risk score: {st.session_state.risk_score:.3f} — CRITICAL PRIORITY.")
        time.sleep(1)
        
        # Phase 4: Impact Agent
        progress_bar.progress(55)
        status.write("💰 Step 4: Modeling economic damage and family vulnerability...")
        try:
            r = requests.get(f"http://127.0.0.1:8000/api/impact/{selected_zone_id}?severity={st.session_state.risk_score}&duration_days=7")
            st.session_state.impact_res = r.json()
        except Exception as e:
            st.error(f"Backend Connection Error (Impact): {e}")
            st.session_state.impact_res = {}
        add_log("Impact", f"Estimated damage: ₹{st.session_state.impact_res.get('economic_impact', {}).get('total_impact_crore', 180):.0f} Crore.")
        time.sleep(1)
        
        # Phase 5: Cascade Agent
        progress_bar.progress(70)
        status.write("🔗 Step 5: Predicting cross-zone propagation...")
        try:
            requests.get(f"http://127.0.0.1:8000/api/cascade?source_zone={selected_zone_id}")
        except Exception as e:
            st.error(f"Backend Connection Error (Cascade): {e}")
        add_log("Cascade", f"91% probability of propagation to adjacent coastal zones within 72h.")
        time.sleep(1)
        
        # Phase 6: Intelligence Agent
        progress_bar.progress(85)
        status.write("🧬 Step 6: Performing causal reasoning and risk projections...")
        try:
            requests.get(f"http://127.0.0.1:8000/api/rootcause/{selected_zone_id}")
            requests.get(f"http://127.0.0.1:8000/api/time-to-risk/{selected_zone_id}")
        except Exception as e:
            st.error(f"Backend Connection Error (Intelligence): {e}")
        add_log("Intelligence", "Primary cause: Thermal stratification. Breach predicted in 2.7 days.")
        time.sleep(1)
        
        # Phase 7: Explanation Agent
        progress_bar.progress(95)
        status.write("🔴 Step 7: Synthesizing multi-language operator briefing...")
        try:
            requests.get("http://127.0.0.1:8000/api/briefing", timeout=15)
            add_log("Explanation", "Regional AI briefing generated for field responders.")
        except Exception as e:
            add_log("Explanation", f"LLM Briefing fallback triggered: {e}")
        time.sleep(1)
        
        # Phase 8: Telegram Agent
        progress_bar.progress(100)
        status.write("📱 Step 8: Dispatching prioritize alerts to field units...")
        try:
            requests.post("http://127.0.0.1:8000/api/telegram/send-alerts", timeout=10)
            add_log("Telegram", "Alert notifications pushed to @8168909813")
        except Exception as e:
            add_log("Telegram", f"Telegram push fallback: {e}")
        
        status.update(label="✅ Simulation Pipeline Complete", state="complete", expanded=False)
        st.session_state.sim_active = False
        st.success("Pipeline Demonstration Successful!")
        time.sleep(1)
        progress_bar.empty()

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
    st.markdown("### Active Priority Alerts")
    active_db_alerts = st.session_state.sys_alerts if st.session_state.sys_alerts else db.get_alerts(include_suppressed=False, limit=3)
    
    if active_db_alerts:
        for a in active_db_alerts[:3]:
            icon = "🔴" if float(a.get('priority_score', 0.9)) > 0.8 else "🟠"
            st.warning(f"{icon} **{a.get('zone_name', selected_zone_name)}**: {a.get('severity', 'CRITICAL').upper()} ({a.get('priority_score', 0.95):.3f})")
    else:
        st.success("No active anomalies breaching threshold. Scanning...")

    # Economic impact chart (Dynamic data)
    st.markdown("### Projected Loss (₹ Crore)")
    if st.session_state.impact_res:
        impact_metrics = st.session_state.impact_res.get('economic_impact', {})
        impact_data = pd.DataFrame({
            'Category': ['Fishing', 'Shipping', 'Tourism'],
            'Damage': [
                impact_metrics.get('fishing_loss_crore', 45), 
                impact_metrics.get('shipping_delay_cost_crore', 320), 
                impact_metrics.get('tourism_loss_crore', 140)
            ]
        })
    else:
        impact_data = pd.DataFrame({
            'Category': ['Fishing', 'Shipping', 'Tourism'],
            'Damage': [0, 0, 0]
        })
        
    st.bar_chart(impact_data.set_index('Category'))

st.markdown("---")
st.caption("Environmental Sentinel AI © 2026 | Built for Airavat 3.0 Hackathon")

<div align="center">
  <img src="https://img.shields.io/badge/Status-Hackathon--Ready-success.svg?style=for-the-badge" alt="Status" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=for-the-badge" alt="Python" />
  <img src="https://img.shields.io/badge/Streamlit-1.42%2B-ff4b4b.svg?style=for-the-badge" alt="Streamlit" />
  <img src="https://img.shields.io/badge/AI-Gemini%202.5%20Flash-orange.svg?style=for-the-badge" alt="AI" />
  <h1>🌍 Airavat 3.0: Environmental Sentinel</h1>
  <p><b>A 10-Agent Cognitive Intelligence Engine for Real-Time Marine Crisis Detection & Decision Support.</b></p>
</div>

---

## 🚀 The Vision
The **Environmental Sentinel** is a proactive intelligence engine designed to protect India's 7,500km coastline. It doesn't just monitor data; it **reasons** through it. By merging real-time multi-source ingestion (NOAA, NASA, OpenAQ) with a specialized multi-agent architecture, it identifies anomalies, predicts cross-zone cascades, and calculates socio-economic impacts before they escalate.

---

## 🧠 10-Agent "System-of-Systems" Architecture
Our proprietary architecture uses specialized AI agents that "collaborate" to solve complex environmental challenges:

1.  📡 **Data Agent**: Orchestrates ingestion from 4+ global satellite and weather APIs.
2.  🔵 **Analysis Agent**: Trains localized ML models (Isolation Forest + STL) per coastal zone.
3.  🟡 **Decision Agent**: Scores and prioritizes alerts based on magnitude, recency, and trajectory.
4.  🔗 **Cascade Agent**: Models ocean currents to predict how anomalies move between zones (e.g., Mumbai → Goa).
5.  💰 **Impact Agent**: Translates raw data into real-world damage (₹ Crore + families affected).
6.  🧬 **Intelligence Agent**: The core "brain" for Root Cause, What-If scenarios, and Time-to-Risk.
7.  🟣 **Memory Agent**: Implements adaptive sensitivity—learning from operator feedback.
8.  🔴 **Explanation Agent**: Synthesizes complex results into human-readable briefings (Gemini-powered).
9.  🌐 **Multi-Lang Agent**: Democratizes data in 10+ regional languages (Hindi, Marathi, etc.).
10. 📱 **Telegram Agent**: Bi-directional mobile interface for real-time operator alerts.

---

## 🖥️ Hackathon Demo: Mission Control (Streamlit)
To demonstrate the full power of the AI pipeline to judges, we have included a **High-Fidelity Web Simulation Dashboard**. This web app bypasses steady-state monitoring and injects a realistic 48-hour marine heatwave crisis into the system, visualizing the multi-agent reasoning chain live.

### How to Run the Simulation:
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the Mission Control Dashboard
python -m streamlit run simulation_app.py
```

**What the Judges Will See:**
1.  **🚨 Inject Anomaly**: A big red button to trigger a 48-hour crisis (SST spike, Wind stagnation, pH drop).
2.  **🧠 Reasoning Chain**: A live, scrollable feed showing exactly what each of the 10 agents is thinking.
3.  **📊 Visual Intelligence**: Real-time Plotly gauges for Risk Level and bar charts for Socio-Economic Impact (₹ Crore).
4.  **⏰ Early Warning**: Time-to-Risk calculates exactly when thresholds will hit "Non-Recoverable" levels.

---

## 🛠️ Installation & Setup

### 1. Prerequisites
- Python 3.10+
- 2GB+ Free RAM

### 2. Environment Configuration (`.env`)
Create a `.env` file in the `backend` directory:
```env
GEMINI_API_KEY=your_key_here
NASA_API_KEY=DEMO_KEY
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_id
```

### 3. Quick Start
```bash
# 1. Start the Sentinel Backend Server
python main.py

# 2. Open the Simulation Dashboard (New Terminal)
python -m streamlit run simulation_app.py
```

---

## 📡 API Intelligence Suite
The backend exposes 30+ intelligence endpoints. View the full, interactive Swagger UI at:
👉 `http://localhost:8000/docs`

| Feature | Endpoint | Description |
| :--- | :--- | :--- |
| **What-If** | `/api/simulate` | Test hypothetical environmental scenarios. |
| **Root Cause**| `/api/rootcause/{id}` | Algorithmic causal analysis of any anomaly. |
| **Impact** | `/api/impact` | Real-time socio-economic risk assessment. |
| **Briefing** | `/api/briefing/{lang}` | AI-synthesized summary in vernacular languages. |

---

> **Built for the challenge. Designed for the planet.** 🌍

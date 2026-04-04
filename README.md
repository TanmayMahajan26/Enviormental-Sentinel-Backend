<div align="center">
  <img src="https://img.shields.io/badge/Status-Hackathon--Ready-success.svg?style=for-the-badge" alt="Status" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=for-the-badge" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.115%2B-00a393.svg?style=for-the-badge" alt="FastAPI" />
  <img src="https://img.shields.io/badge/AI-Gemini%203%20Flash-orange.svg?style=for-the-badge" alt="AI" />
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

## 🧪 Hackathon Demo: The Anomaly Simulation
To demonstrate the full power of the AI pipeline to judges, we have included a **Simulation Engine**. This bypasses steady-state monitoring and injects a realistic 48-hour marine heatwave crisis into the system.

### How to Run the Demo:
```bash
python simulate_anomaly.py
```

**What the Judges Will See:**
1.  **Injection**: 48 hours of escalating crisis data (SST spike, Wind stagnation, pH drop).
2.  **Detection**: Analysis Agents immediately flags the signatures as high-z-score anomalies.
3.  **Prioritization**: Decision Agent generates a **CRITICAL** alert with a 1.0/1.0 priority score.
4.  **Propagation**: Cascade Agent predicts risk to neighboring zones (Goa, Gulf of Kutch).
5.  **Impact**: Impact Agent estimates ₹ Crore damage and fishing family vulnerability.
6.  **Reasoning**: Root Cause Agent identifies the "WHY" (e.g., Solar heating + Wind nullification).
7.  **Early Warning**: Time-to-Risk calculates exactly when thresholds will hit "Non-Recoverable" levels.

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
# Install dependencies
pip install -r requirements.txt

# Start the Sentinel Server
python main.py
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

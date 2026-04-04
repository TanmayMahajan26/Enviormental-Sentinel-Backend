<div align="center">

  <h1>🌍 EcoSentinel — AI Environmental Intelligence</h1>
  <p><b>An Autonomous 9-Agent Geospatial Intelligence Engine for Coastal Environmental Monitoring</b></p>

  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Gemini_AI-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License" />

</div>

---

## 📋 Overview

EcoSentinel is a **full-stack AI-powered environmental monitoring platform** that autonomously ingests satellite data, detects anomalies using ML, and delivers actionable intelligence for **8 Indian coastal zones** — spanning the Arabian Sea, Bay of Bengal, and Indian Ocean.

The system runs **9 specialized AI agents** that work together in a pipeline: from raw data ingestion → anomaly detection → root cause analysis → cascade prediction → economic impact estimation → natural language briefings.

### Key Features

| Feature | Description |
|---------|-------------|
| 🔬 **ML Anomaly Detection** | STL Decomposition + Isolation Forest on 90-day rolling baselines |
| 🧠 **9 Autonomous Agents** | Data, Analysis, Decision, Memory, Intelligence, Cascade, Impact, Explanation, Telegram |
| 🧪 **What-If Simulation** | Inject hypothetical stressors and visualize cascading environmental risks |
| 🔍 **Root Cause Analysis** | Probabilistic attribution of anomaly drivers |
| 💰 **Economic Impact Engine** | Damage estimation in ₹ Crore across fishing, shipping, and tourism sectors |
| 🔗 **Cascade Prediction** | Cross-zone propagation modeling using ocean current adjacency |
| 🌐 **Multilingual Briefings** | AI-generated summaries in 10+ Indian languages via Gemini |
| 📱 **Telegram Integration** | Bi-directional bot for remote alerting and queries |
| 🧬 **Adaptive Self-Correction** | Memory Agent recalibrates sensitivity based on operator feedback |
| ⏱️ **Time-to-Risk Warnings** | Early warning system predicting when parameters will reach critical thresholds |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │  Data Agent       │    │  Live Data Agent  │               │
│  │  90-day synthetic │    │  NOAA · Open-Meteo │               │
│  │  baseline         │    │  OpenAQ · NASA     │               │
│  └────────┬─────────┘    └────────┬─────────┘               │
│           └────────────┬──────────┘                          │
├────────────────────────┼────────────────────────────────────┤
│                  ANALYSIS LAYER                              │
│           ┌────────────▼─────────────┐                       │
│           │    Analysis Agent         │                       │
│           │  STL → Isolation Forest   │                       │
│           │  → Holt-Winters Forecast  │                       │
│           └────────────┬─────────────┘                       │
├────────────────────────┼────────────────────────────────────┤
│               CORE INTELLIGENCE                              │
│  ┌─────────────┐ ┌────▼────────┐ ┌──────────────┐          │
│  │ Memory Agent │ │Decision Agent│ │ Impact Agent  │          │
│  │ Self-correct │ │ 4D Scoring   │ │ ₹ Estimation  │          │
│  └─────────────┘ └─────────────┘ └──────────────┘          │
├─────────────────────────────────────────────────────────────┤
│                  DISTRIBUTION                                │
│  ┌──────────────┐ ┌───────────────┐ ┌────────────────┐     │
│  │ Cascade Agent │ │ Intel Agent    │ │ Explanation    │     │
│  │ Zone spread   │ │ Root cause/sim │ │ Agent (Gemini) │     │
│  └──────────────┘ └───────────────┘ └───────┬────────┘     │
│                                              │               │
│                                    ┌─────────▼──────────┐   │
│                                    │  Telegram Agent     │   │
│                                    └────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start — Run Locally

### Prerequisites

- **Python 3.10+**
- **pip** (Python package manager)
- **Gemini API Key** — free from [Google AI Studio](https://aistudio.google.com/)

### 1. Clone the Repository

```bash
git clone https://github.com/TanmayMahajan26/Enviormental-Sentinel-Backend.git
cd Enviormental-Sentinel-Backend
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# Required — for AI Explanation Agent (Gemini LLM briefings & chat)
GEMINI_API_KEY=your_gemini_api_key_here

# Optional — for Telegram alert delivery
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Optional — NASA EONET natural events (DEMO_KEY works)
NASA_API_KEY=DEMO_KEY
```

> **Note:** The system works fully without Telegram keys. The Gemini key is required for the AI Chat and Briefing features; all other features (anomaly detection, simulations, alerts, etc.) work without it.

### 4. Start the Server

```bash
python main.py
```

On first launch, the system will:
1. Generate a **90-day synthetic baseline** for all 8 coastal zones (~19,000 readings)
2. Train **ML models** (Isolation Forest + Holt-Winters) per zone
3. Run the first **live data ingestion** from NOAA, Open-Meteo, and OpenAQ
4. Start the autonomous **agent pipeline**

This takes about **30–60 seconds** on first run.

### 5. Open the Application

| URL | Description |
|-----|-------------|
| **http://localhost:8000/** | 🏠 Landing page with project overview |
| **http://localhost:8000/app** | 📊 Live dashboard with all features |
| **http://localhost:8000/docs** | 📖 Swagger API documentation (30+ endpoints) |
| **http://localhost:8000/redoc** | 📚 ReDoc API documentation |

---

## 🖥️ Application Pages

The dashboard at `/app` contains **6 interactive sections**:

| Tab | Features |
|-----|----------|
| **Dashboard** | System stats, 8 zone cards with live anomaly scores, priority alerts, AI briefing |
| **Alerts** | Decision Agent–ranked alerts with ✅ Validated / ❌ False Positive feedback buttons |
| **Incidents** | Auto-generated structured incident reports (IR-2026-XXXX format) |
| **AI Chat** | Natural language queries about environmental conditions (powered by Gemini) |
| **Simulation** | What-If engine: adjust 5 environmental parameters and see cascading impacts |
| **Agent Logs** | Real-time multi-agent reasoning chain and processing history |

---

## 📁 Project Structure

```
.
├── main.py                 # FastAPI application with 30+ endpoints
├── config.py               # Configuration and environment variables
├── database.py             # SQLite ORM with SQLAlchemy
├── schemas.py              # Pydantic request/response models
├── scheduler.py            # Background task scheduler
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
│
├── agents/                 # 9 autonomous AI agents
│   ├── data_agent.py       # Synthetic baseline data generation
│   ├── live_data_agent.py  # NOAA, Open-Meteo, OpenAQ ingestion
│   ├── analysis_agent.py   # STL + Isolation Forest + Holt-Winters
│   ├── decision_agent.py   # 4D priority scoring & alert suppression
│   ├── memory_agent.py     # Adaptive sensitivity recalibration
│   ├── intelligence_agent.py # Root cause, simulation, pattern memory
│   ├── cascade_agent.py    # Cross-zone propagation prediction
│   ├── impact_agent.py     # Economic damage estimation
│   ├── explanation_agent.py # Gemini LLM briefings & multilingual
│   └── telegram_agent.py   # Telegram bot integration
│
├── frontend/               # Static frontend (served by FastAPI)
│   ├── index.html          # Landing page
│   ├── dashboard.html      # Live dashboard SPA
│   ├── style.css           # Dashboard styles
│   ├── app.js              # Dashboard API client
│   ├── landing.css         # Landing page styles
│   └── landing.js          # Landing page scripts
│
└── data/                   # Auto-generated at runtime
    ├── zones.json          # Zone configurations
    └── models/             # Trained ML models (.pkl)
```

---

## 🔌 API Endpoints (Selection)

The full API is documented at `/docs`. Key endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/zones` | List all 8 monitored coastal zones |
| `GET` | `/api/zones/{id}` | Zone detail with latest readings |
| `GET` | `/api/alerts` | Priority-ranked alerts from Decision Agent |
| `POST` | `/api/alerts/{id}/feedback` | Submit Validated/False Positive feedback |
| `GET` | `/api/anomalies` | Detected anomalies with z-scores |
| `GET` | `/api/forecast/{zone_id}` | 7-day SST forecast with confidence intervals |
| `GET` | `/api/rootcause/{zone_id}` | Probabilistic root cause analysis |
| `GET` | `/api/cascade/{zone_id}` | Cross-zone propagation predictions |
| `GET` | `/api/economic-impact/{zone_id}` | Economic damage in ₹ Crore |
| `GET` | `/api/time-to-risk/{zone_id}` | Early warning time estimates |
| `POST` | `/api/simulate` | What-If simulation engine |
| `GET` | `/api/briefing` | AI-generated executive summary |
| `POST` | `/api/chat` | Natural language environmental queries |
| `GET` | `/api/agent-logs` | Multi-agent reasoning chain |
| `GET` | `/api/incident-report/{alert_id}` | Structured incident report |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python, FastAPI, Uvicorn |
| **Database** | SQLite (local) / PostgreSQL (production) |
| **ML/AI** | scikit-learn (Isolation Forest), statsmodels (STL, Holt-Winters) |
| **LLM** | Google Gemini (Explanation Agent) |
| **Frontend** | Vanilla HTML/CSS/JS with glassmorphism design |
| **Data Sources** | NOAA ERDDAP, Open-Meteo, OpenAQ, NASA EONET |
| **Alerting** | Telegram Bot API |

---

## 📊 Data Sources

All data sources are **free and require no API keys**:

| Source | Data | Frequency |
|--------|------|-----------|
| [NOAA ERDDAP](https://coastwatch.pfeg.noaa.gov/erddap/) | Sea Surface Temperature, Chlorophyll-a | Every 6 hours |
| [Open-Meteo](https://open-meteo.com/) | Wind speed, weather conditions | Every 6 hours |
| [OpenAQ](https://openaq.org/) | PM2.5 air quality | Every 6 hours |
| [NASA EONET](https://eonet.gsfc.nasa.gov/) | Natural events (wildfires, storms) | Every 6 hours |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

<div align="center">
  <p><b>Built for the IEEE CS S.P.I.T Challenge | Empowering Environmental Policy through Cognitive AI 🌍</b></p>
</div>

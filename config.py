"""
Configuration for Environmental Sentinel backend.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")  # free demo key works

# --- Database ---
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "sentinel.db")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "data", "models")

# --- Zone Configuration ---
ZONES_PATH = os.path.join(os.path.dirname(__file__), "data", "zones.json")

# --- ML Configuration ---
ISOLATION_FOREST_CONTAMINATION = 0.05
ISOLATION_FOREST_N_ESTIMATORS = 200
STL_PERIOD = 24  # hourly data, 24-hour seasonality
FORECAST_HORIZON_HOURS = 168  # 7 days ahead
ROLLING_WINDOW = 12  # 12-hour rolling stats

# --- Decision Agent ---
DECISION_WEIGHTS = {
    "magnitude": 0.30,
    "recency": 0.20,
    "trajectory": 0.20,
    "convergence": 0.20,
    "historical": 0.10,
}
ALERT_COOLDOWN_HOURS = 6
MIN_CONVERGENCE_SIGNALS = 2
CONFIDENCE_FLOOR = 0.40

# --- Memory Agent ---
SENSITIVITY_EMA_ALPHA = 0.15  # how fast sensitivity adapts
DEFAULT_SENSITIVITY = 1.0
MIN_SENSITIVITY = 0.3
MAX_SENSITIVITY = 2.0

# --- Data Generation ---
DATA_DAYS = 90
READINGS_PER_HOUR = 1  # hourly readings
TOTAL_READINGS = DATA_DAYS * 24 * READINGS_PER_HOUR

# --- Server ---
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

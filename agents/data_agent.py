"""
🟢 DATA AGENT — Collector
Generates 90 days of realistic synthetic environmental data for 8 Indian coastal zones.
Also fetches live NASA EONET events.

Data is modeled on real NOAA/INCOIS baselines for Indian Ocean waters:
- Sea Surface Temperature (SST): Indian Ocean averages 26-31°C with monsoon seasonality
- Chlorophyll-a: 0.1-5.0 mg/m³, higher near river discharge zones
- Wind Speed: 2-15 m/s, monsoon-driven
- pH: 7.8-8.3 with natural variation
- Turbidity: 1-50 NTU, sediment-dependent

Anomaly injection:
1. Mumbai: 8-day slow thermal buildup (days 70-78)
2. Chennai: Sudden algal bloom (days 60-63)
3. Sundarbans: Chronic chlorophyll noise (throughout — for Memory Agent testing)
4. Gulf of Kutch: pH acidification event (days 80-83)
5. Andaman: Multi-signal cyclone precursor (days 85-88)
"""
import numpy as np
import pandas as pd
import json
import httpx
from datetime import datetime, timedelta
from config import ZONES_PATH, DATA_DAYS, NASA_API_KEY
import database as db


def load_zones() -> list[dict]:
    with open(ZONES_PATH, "r") as f:
        return json.load(f)


def _generate_seasonal_component(n_points: int, period: int = 24,
                                  amplitude: float = 1.0, phase: float = 0.0) -> np.ndarray:
    """Generate a sinusoidal seasonal pattern (daily cycle)."""
    t = np.arange(n_points)
    return amplitude * np.sin(2 * np.pi * t / period + phase)


def _generate_monsoon_component(n_points: int, day_start: int = 0) -> np.ndarray:
    """
    Simulate Indian monsoon influence.
    Southwest monsoon: June-September (days ~150-270 of year)
    We create a broader seasonal envelope.
    """
    t = np.arange(n_points)
    days = t / 24.0 + day_start
    # Monsoon peaks around day 60 of our 90-day window if starting in April
    monsoon_envelope = 0.5 * np.sin(2 * np.pi * days / 180 - np.pi / 3)
    return np.clip(monsoon_envelope, -0.5, 1.0)


def _generate_trend(n_points: int, slope: float = 0.001) -> np.ndarray:
    """Slight linear trend (e.g., warming)."""
    return slope * np.arange(n_points)


def generate_zone_data(zone: dict, n_points: int = 2160) -> pd.DataFrame:
    """
    Generate 90 days of hourly data for one zone.
    n_points = 90 days * 24 hours = 2160
    """
    zone_id = zone["id"]
    np.random.seed(hash(zone_id) % (2**31))

    timestamps = [
        (datetime(2026, 1, 5) + timedelta(hours=i)).isoformat()
        for i in range(n_points)
    ]

    # Base seasonal patterns
    daily_cycle = _generate_seasonal_component(n_points, period=24, amplitude=1.0)
    multi_day_cycle = _generate_seasonal_component(n_points, period=24 * 7, amplitude=0.3)
    monsoon = _generate_monsoon_component(n_points, day_start=5)
    trend = _generate_trend(n_points, slope=0.0005)

    # --- SST ---
    sst_base = zone["baseline_sst"]
    sst = (sst_base
           + daily_cycle * 0.8           # ±0.8°C daily cycle
           + multi_day_cycle * 0.4       # ±0.4°C weekly
           + monsoon * 1.5              # monsoon cooling/warming
           + trend * 5                  # slight warming trend
           + np.random.normal(0, 0.2, n_points))  # noise

    # --- Chlorophyll-a ---
    chl_base = zone["baseline_chlorophyll"]
    chl = (chl_base
           + daily_cycle * 0.15 * chl_base
           + multi_day_cycle * 0.1 * chl_base
           + monsoon * 0.3 * chl_base    # monsoon nutrient upwelling
           + np.random.normal(0, 0.08 * chl_base, n_points))
    chl = np.maximum(chl, 0.05)  # can't go negative

    # --- Wind Speed ---
    wind_base = zone["baseline_wind"]
    wind = (wind_base
            + daily_cycle * 1.2           # morning calm, afternoon wind
            + monsoon * 3.0              # monsoon wind surge
            + np.random.normal(0, 0.8, n_points))
    wind = np.maximum(wind, 0.5)

    # --- pH ---
    ph_base = zone["baseline_ph"]
    ph = (ph_base
          + daily_cycle * 0.02           # slight daily variation
          + multi_day_cycle * 0.01
          + np.random.normal(0, 0.015, n_points))

    # --- Turbidity ---
    turb_base = zone["baseline_turbidity"]
    turb = (turb_base
            + daily_cycle * 0.05 * turb_base
            + monsoon * 0.4 * turb_base   # monsoon runoff
            + np.random.normal(0, 0.1 * turb_base, n_points))
    turb = np.maximum(turb, 0.5)

    # ═══════════════════════════════════════════════════
    # ANOMALY INJECTION — specific events per zone
    # ═══════════════════════════════════════════════════

    if zone_id == "zone_mumbai":
        # 🔥 8-day slow thermal buildup (days 70-78, hours 1680-1872)
        for h in range(1680, 1872):
            day_in_event = (h - 1680) / 24.0
            sst[h] += 0.25 * day_in_event  # +0.25°C per day buildup
            wind[h] *= 0.7  # wind dies down (traps heat)

    elif zone_id == "zone_chennai":
        # 🌿 Sudden algal bloom (days 60-63, hours 1440-1512)
        bloom_profile = np.concatenate([
            np.linspace(0, 3.0, 24),    # rapid rise over 1 day
            np.ones(24) * 3.5,           # peak for 1 day
            np.linspace(3.5, 2.0, 24),   # slow decline
        ])
        chl[1440:1440 + len(bloom_profile)] += bloom_profile * chl_base

    elif zone_id == "zone_sundarbans":
        # 📢 Chronic noisy chlorophyll — Memory Agent should learn to suppress
        # High variance throughout, mimicking sediment/algae mixing
        chl += np.random.normal(0, 0.5 * chl_base, n_points)
        # Add periodic fake "bloom" spikes every ~10 days
        for day in range(10, 90, 10):
            h_start = day * 24
            h_end = min(h_start + 36, n_points)
            chl[h_start:h_end] += chl_base * 1.5
        chl = np.maximum(chl, 0.05)

    elif zone_id == "zone_kutch":
        # ⚗️ pH acidification event (days 80-83, hours 1920-1992)
        acid_profile = np.concatenate([
            np.linspace(0, -0.35, 36),   # pH drops by 0.35 over 1.5 days
            np.ones(12) * -0.35,         # stays low for half a day
            np.linspace(-0.35, -0.1, 24) # partial recovery
        ])
        ph[1920:1920 + len(acid_profile)] += acid_profile

    elif zone_id == "zone_andaman":
        # 🌀 Multi-signal cyclone precursor (days 85-88, hours 2040-2112)
        for h in range(2040, min(2112, n_points)):
            progress = (h - 2040) / 72.0
            sst[h] += 1.5 * progress         # SST rises (warm ocean fuels cyclone)
            wind[h] += 8.0 * progress         # wind intensifies
            turb[h] += 15.0 * progress        # turbidity spikes
            ph[h] -= 0.1 * progress           # slight pH drop

    elif zone_id == "zone_goa":
        # 🐟 Moderate fishing season anomaly (days 40-45)
        for h in range(960, min(1080, n_points)):
            chl[h] += 0.4 * chl_base  # mild chlorophyll increase
            turb[h] += 3.0             # mild turbidity

    elif zone_id == "zone_vizag":
        # 🌊 Upwelling event (days 50-54, hours 1200-1296)
        for h in range(1200, min(1296, n_points)):
            progress = (h - 1200) / 96.0
            sst[h] -= 2.0 * progress          # cold water upwelling
            chl[h] += 1.5 * chl_base * progress  # nutrient-rich = more chlorophyll

    elif zone_id == "zone_kochi":
        # 🌧️ Monsoon river discharge pulse (days 55-60)
        for h in range(1320, min(1440, n_points)):
            turb[h] += 20.0  # massive turbidity from river
            ph[h] -= 0.15     # freshwater lowers pH

    # Build DataFrame
    df = pd.DataFrame({
        "timestamp": timestamps,
        "zone_id": zone_id,
        "sst": np.round(sst, 3),
        "chlorophyll": np.round(chl, 4),
        "wind_speed": np.round(wind, 2),
        "ph": np.round(ph, 3),
        "turbidity": np.round(turb, 2),
    })

    return df


def generate_all_zones_data() -> pd.DataFrame:
    """Generate 90 days of data for all 8 Indian coastal zones."""
    zones = load_zones()
    all_data = []

    for zone in zones:
        print(f"  [Data Agent] Generating 90-day data for {zone['name']}...")
        df = generate_zone_data(zone)
        all_data.append(df)

    combined = pd.concat(all_data, ignore_index=True)
    print(f"  [Data Agent] Total data points generated: {len(combined)}")
    return combined


def seed_readings():
    """Generate and store all readings in database."""
    # Check if data already exists
    count = db.get_readings_count("zone_mumbai")
    if count > 0:
        print("[Data Agent] Readings already seeded, skipping.")
        return

    print("[Data Agent] Generating 90-day India coastal dataset...")
    df = generate_all_zones_data()

    # Convert to list of dicts and insert
    readings = df.to_dict(orient="records")

    # Insert in batches of 1000 for performance
    batch_size = 1000
    for i in range(0, len(readings), batch_size):
        batch = readings[i:i + batch_size]
        db.insert_readings_batch(batch)

    print(f"[Data Agent] ✅ Seeded {len(readings)} readings across 8 zones.")


async def fetch_nasa_eonet_events(limit: int = 20) -> list[dict]:
    """Fetch live natural events from NASA EONET API v3."""
    url = "https://eonet.gsfc.nasa.gov/api/v3/events"
    params = {
        "limit": limit,
        "status": "open",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        events = []
        for event in data.get("events", []):
            # Get the most recent geometry
            geom = event.get("geometry", [{}])
            latest_geom = geom[-1] if geom else {}
            coords = latest_geom.get("coordinates", [None, None])

            categories = event.get("categories", [{}])
            category = categories[0].get("title", "Unknown") if categories else "Unknown"

            sources = event.get("sources", [{}])
            source_url = sources[0].get("url", None) if sources else None

            events.append({
                "id": event.get("id", ""),
                "title": event.get("title", ""),
                "description": event.get("description"),
                "category": category,
                "source": "NASA EONET",
                "lat": coords[1] if len(coords) > 1 else None,
                "lng": coords[0] if coords else None,
                "date": latest_geom.get("date", ""),
                "link": source_url,
            })

        return events

    except Exception as e:
        print(f"[Data Agent] NASA EONET fetch failed: {e}")
        return []


if __name__ == "__main__":
    # Test data generation
    zones = load_zones()
    df = generate_zone_data(zones[0])
    print(f"\nSample data for {zones[0]['name']}:")
    print(df.describe())
    print(f"\nShape: {df.shape}")

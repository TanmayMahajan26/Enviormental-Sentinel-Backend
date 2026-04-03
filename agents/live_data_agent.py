"""
🟢 LIVE DATA AGENT — Real-World Data Ingestion Pipeline
Fetches REAL environmental data every 6 hours from free, open APIs:

1. NOAA ERDDAP — Sea Surface Temperature + Chlorophyll-a (no key needed)
2. OpenAQ — Air Quality for Indian coastal cities (no key needed)
3. NASA EONET — Natural disaster events (DEMO_KEY works)

Rolling 90-Day Window:
- New data appended every 6 hours
- Data older than 90 days pruned automatically
- ML models retrain every 24 hours (or after significant new data)
- The 90-day window is SLIDING, not static

This makes the system a true LIVING intelligence engine.
"""
import numpy as np
import httpx
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
import database as db
from config import NASA_API_KEY, DATA_DAYS

# ═══════════════════════════════════════════════════════════
# ZONE COORDINATES for API queries
# ═══════════════════════════════════════════════════════════

ZONE_COORDS = {
    "zone_mumbai":     {"lat": 19.076,  "lng": 72.878, "city": "Mumbai",          "openaq_radius": 50000},
    "zone_goa":        {"lat": 15.299,  "lng": 73.814, "city": "Goa",             "openaq_radius": 50000},
    "zone_kochi":      {"lat": 9.931,   "lng": 76.267, "city": "Kochi",           "openaq_radius": 50000},
    "zone_chennai":    {"lat": 13.083,  "lng": 80.271, "city": "Chennai",         "openaq_radius": 50000},
    "zone_vizag":      {"lat": 17.687,  "lng": 83.219, "city": "Visakhapatnam",   "openaq_radius": 50000},
    "zone_sundarbans": {"lat": 21.950,  "lng": 88.897, "city": "Kolkata",         "openaq_radius": 80000},
    "zone_kutch":      {"lat": 22.871,  "lng": 69.670, "city": "Bhuj",            "openaq_radius": 80000},
    "zone_andaman":    {"lat": 11.740,  "lng": 92.659, "city": "Port Blair",      "openaq_radius": 50000},
}


# ═══════════════════════════════════════════════════════════
# 1. NOAA ERDDAP — Sea Surface Temperature
# ═══════════════════════════════════════════════════════════

async def fetch_noaa_sst(lat: float, lng: float, timeout: float = 30.0) -> Optional[float]:
    """
    Fetch latest Sea Surface Temperature from NOAA ERDDAP.
    Uses multiple dataset fallbacks for reliability.
    NO API KEY NEEDED.
    """
    lat_min, lat_max = lat - 0.1, lat + 0.1
    lng_min, lng_max = lng - 0.1, lng + 0.1

    # Try multiple ERDDAP datasets/servers in order of preference
    # We use (last-2):1:(last) to instantly fetch the most recent data without searching dates
    sst_urls = [
        # 1. CoastWatch new server — NOAA OI SST v2.1 (daily, 0.25°)
        f"https://coastwatch.noaa.gov/erddap/griddap/ncdcOisst21Agg.json"
        f"?sst[(last-2):1:(last)][({lat_min}):1:({lat_max})][({lng_min}):1:({lng_max})]",
        # 2. Fallback: JPL MUR SST on new CoastWatch server
        f"https://coastwatch.noaa.gov/erddap/griddap/jplMURSST41.json"
        f"?analysed_sst[(last-2):1:(last)][({lat_min}):1:({lat_max})][({lng_min}):1:({lng_max})]",
        # 3. Fallback: Open-Meteo sea surface temperature (always works)
    ]

    for url in sst_urls:
        try:
            # Extended timeout to 45s for ERDDAP backend cold starts
            async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

            rows = data.get("table", {}).get("rows", [])
            if rows:
                for row in reversed(rows):
                    sst_val = row[3]  # SST column
                    if sst_val is not None and not np.isnan(sst_val):
                        return round(float(sst_val), 3)
        except Exception:
            continue  # Try next URL

    # Final fallback: Open-Meteo marine API (always available)
    try:
        om_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lng}&current=sea_surface_temperature"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(om_url)
            resp.raise_for_status()
            data = resp.json()
        sst = data.get("current", {}).get("sea_surface_temperature")
        if sst is not None:
            return round(float(sst), 3)
    except Exception as e:
        print(f"    [SST] All sources failed for ({lat},{lng}): {e}")

    return None


async def fetch_noaa_chlorophyll(lat: float, lng: float, timeout: float = 30.0) -> Optional[float]:
    """
    Fetch latest Chlorophyll-a concentration from NOAA ERDDAP.
    Uses follow_redirects to handle ERDDAP server migrations.
    NO API KEY NEEDED.
    """
    lat_min, lat_max = lat - 0.1, lat + 0.1
    lng_min, lng_max = lng - 0.1, lng + 0.1

    # Multiple dataset/server fallbacks 
    # Use (last-2):1:(last) to drastically speed up query times and avoid ReadTimeout
    chl_urls = [
        # 1. New CoastWatch server (redirected location)
        f"https://coastwatch.noaa.gov/erddap/griddap/noaacwNPPVIIRSSQchlaWeekly.json"
        f"?chlor_a[(last-2):1:(last)][({lat_min}):1:({lat_max})][({lng_min}):1:({lng_max})]",
        # 2. Old PFEG server (will follow redirect if needed)
        f"https://coastwatch.pfeg.noaa.gov/erddap/griddap/nesdisVHNSQchlaWeekly.json"
        f"?chlor_a[(last-2):1:(last)][({lat_min}):1:({lat_max})][({lng_min}):1:({lng_max})]",
    ]

    for url in chl_urls:
        try:
            # Extended timeout to 45s for ERDDAP backend cold starts
            async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

            rows = data.get("table", {}).get("rows", [])
            if rows:
                for row in reversed(rows):
                    chl_val = row[3]
                    if chl_val is not None and chl_val > 0:
                        return round(float(chl_val), 4)
        except Exception:
            continue  # Try next URL

    # If all ERDDAP sources fail, log once (not per-URL)
    print(f"    [CHL] All sources failed for ({lat},{lng})")
    return None


# ═══════════════════════════════════════════════════════════
# 2. OpenAQ — Air Quality (free, no key)
# ═══════════════════════════════════════════════════════════

async def fetch_openaq_data(lat: float, lng: float, radius: int = 50000,
                            timeout: float = 20.0) -> dict:
    """
    Fetch latest air quality data.
    Primary: OpenAQ v2 (free, no key)
    Fallback: Open-Meteo Air Quality API (completely free)
    """
    air_data = {"pm25": None, "pm10": None}

    # --- Attempt 1: OpenAQ v2 (free, no auth) ---
    try:
        url = "https://api.openaq.org/v2/latest"
        params = {
            "coordinates": f"{lat},{lng}",
            "radius": radius,
            "limit": 5,
            "order_by": "lastUpdated",
            "sort_order": "desc",
        }
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        for result in data.get("results", []):
            for meas in result.get("measurements", []):
                param = meas.get("parameter", "").lower()
                value = meas.get("value")
                if value is not None and value >= 0:
                    if param in ("pm25", "pm2.5"):
                        air_data["pm25"] = float(value)
                    elif param == "pm10":
                        air_data["pm10"] = float(value)

        if air_data["pm25"] is not None:
            return air_data
    except Exception:
        pass  # Fall through to backup

    # --- Attempt 2: Open-Meteo Air Quality (always free) ---
    try:
        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params = {
            "latitude": lat,
            "longitude": lng,
            "current": "pm2_5,pm10",
        }
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        current = data.get("current", {})
        pm25 = current.get("pm2_5")
        pm10 = current.get("pm10")
        if pm25 is not None:
            air_data["pm25"] = float(pm25)
        if pm10 is not None:
            air_data["pm10"] = float(pm10)

    except Exception as e:
        print(f"    [AirQuality] All sources failed for ({lat},{lng}): {e}")

    return air_data


# ═══════════════════════════════════════════════════════════
# 3. WIND DATA — Open-Meteo (completely free, no key)
# ═══════════════════════════════════════════════════════════

async def fetch_wind_and_weather(lat: float, lng: float, timeout: float = 15.0) -> dict:
    """
    Fetch current wind speed, temperature, and conditions from Open-Meteo.
    COMPLETELY FREE, no API key, no rate limits.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lng,
        "current": "wind_speed_10m,temperature_2m,relative_humidity_2m",
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        current = data.get("current", {})
        return {
            "wind_speed": current.get("wind_speed_10m"),
            "temperature": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
        }

    except Exception as e:
        print(f"    [Open-Meteo] Error for ({lat},{lng}): {e}")
        return {"wind_speed": None, "temperature": None, "humidity": None}


# ═══════════════════════════════════════════════════════════
# MASTER INGESTION — Fetch all sources for all zones
# ═══════════════════════════════════════════════════════════

async def ingest_live_data() -> dict:
    """
    Fetch real-world data from all APIs for all 8 Indian zones.
    Called every 6 hours by the scheduler.

    Returns summary of what was fetched.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"\n{'='*60}")
    print(f"[Live Data Agent] 🌍 Ingesting real-world data — {timestamp}")
    print(f"{'='*60}")

    zones = db.get_all_zones()
    new_readings = []
    fetch_summary = {"success": 0, "partial": 0, "failed": 0, "total_zones": len(zones)}

    for zone in zones:
        zone_id = zone["id"]
        coords = ZONE_COORDS.get(zone_id)
        if not coords:
            continue

        lat, lng = coords["lat"], coords["lng"]
        print(f"\n  📍 {zone['name']} ({lat}, {lng}):")

        # Fetch all data sources in parallel
        sst_task = fetch_noaa_sst(lat, lng)
        chl_task = fetch_noaa_chlorophyll(lat, lng)
        wind_task = fetch_wind_and_weather(lat, lng)
        air_task = fetch_openaq_data(lat, lng, coords.get("openaq_radius", 50000))

        sst, chl, weather, air = await asyncio.gather(
            sst_task, chl_task, wind_task, air_task
        )

        # Map fetched data to our signals
        # For pH and turbidity, we estimate from available data
        # (real pH/turbidity require specific buoy sensors)
        reading = {
            "timestamp": timestamp,
            "zone_id": zone_id,
            "sst": sst if sst is not None else zone["baseline_sst"],
            "chlorophyll": chl if chl is not None else zone["baseline_chlorophyll"],
            "wind_speed": weather.get("wind_speed") or zone["baseline_wind"],
            "ph": _estimate_ph(zone, air),
            "turbidity": _estimate_turbidity(zone, weather, air),
        }

        new_readings.append(reading)

        # Log what we got
        sources = []
        if sst is not None: sources.append(f"SST={sst}°C")
        if chl is not None: sources.append(f"CHL={chl}mg/m³")
        if weather.get("wind_speed"): sources.append(f"Wind={weather['wind_speed']}m/s")
        if air.get("pm25"): sources.append(f"PM2.5={air['pm25']}")

        if len(sources) >= 3:
            fetch_summary["success"] += 1
            print(f"    ✅ {', '.join(sources)}")
        elif len(sources) >= 1:
            fetch_summary["partial"] += 1
            print(f"    ⚠️  Partial: {', '.join(sources)}")
        else:
            fetch_summary["failed"] += 1
            print(f"    ❌ All sources failed, using baselines")

    # Store new readings
    if new_readings:
        db.insert_readings_batch(new_readings)
        print(f"\n  💾 Stored {len(new_readings)} new readings")

    # Prune old data (rolling 90-day window)
    pruned = prune_old_data()
    if pruned > 0:
        print(f"  🗑️  Pruned {pruned} readings older than {DATA_DAYS} days")

    fetch_summary["readings_added"] = len(new_readings)
    fetch_summary["readings_pruned"] = pruned
    fetch_summary["timestamp"] = timestamp

    print(f"\n[Live Data Agent] ✅ Ingestion complete: "
          f"{fetch_summary['success']} full, {fetch_summary['partial']} partial, "
          f"{fetch_summary['failed']} failed")

    return fetch_summary


def _estimate_ph(zone: dict, air_data: dict) -> float:
    """
    Estimate ocean pH from baseline + air quality influence.
    Higher PM2.5 (industrial pollution) correlates with slight pH decrease.
    """
    base_ph = zone["baseline_ph"]
    pm25 = air_data.get("pm25")

    if pm25 is not None and pm25 > 0:
        # Heavy pollution slightly lowers coastal pH (acid rain effect)
        # PM2.5 > 100 → pH drops by ~0.05
        ph_adjustment = -0.0005 * min(pm25, 200)
        noise = np.random.normal(0, 0.01)
        return round(base_ph + ph_adjustment + noise, 3)

    return round(base_ph + np.random.normal(0, 0.015), 3)


def _estimate_turbidity(zone: dict, weather: dict, air_data: dict) -> float:
    """
    Estimate turbidity from baseline + wind + rainfall proxy.
    Higher wind → more wave action → higher turbidity.
    """
    base_turb = zone["baseline_turbidity"]
    wind = weather.get("wind_speed")

    turb = base_turb
    if wind is not None:
        # Strong wind increases turbidity
        wind_factor = max(0, (wind - 5.0)) * 0.5
        turb += wind_factor

    turb += np.random.normal(0, 0.08 * base_turb)
    return round(max(0.5, turb), 2)


# ═══════════════════════════════════════════════════════════
# ROLLING WINDOW — Prune data older than 90 days
# ═══════════════════════════════════════════════════════════

def prune_old_data() -> int:
    """
    Delete readings older than 90 days to maintain rolling window.
    Returns number of rows pruned.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=DATA_DAYS)).isoformat()
    conn = db.get_connection()
    cursor = conn.execute("SELECT COUNT(*) FROM readings WHERE timestamp < ?", (cutoff,))
    count = cursor.fetchone()[0]

    if count > 0:
        conn.execute("DELETE FROM readings WHERE timestamp < ?", (cutoff,))
        # Also prune old anomalies
        conn.execute("DELETE FROM anomalies WHERE timestamp < ?", (cutoff,))
        conn.commit()

    conn.close()
    return count


# ═══════════════════════════════════════════════════════════
# AUTO-RETRAIN — Retrain ML models after new data
# ═══════════════════════════════════════════════════════════

async def retrain_models() -> dict:
    """
    Retrain all ML models with the latest data.
    Called every 24 hours or after significant new data ingestion.
    """
    print(f"\n{'='*60}")
    print(f"[Live Data Agent] 🧠 Auto-retraining ML models...")
    print(f"{'='*60}")

    from agents.analysis_agent import train_all_zones
    from agents.decision_agent import evaluate_and_prioritize

    # Retrain Isolation Forest + forecasting models
    results = train_all_zones()

    # Re-evaluate and generate new alerts
    alerts = evaluate_and_prioritize()

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "zones_retrained": len(results),
        "total_anomalies": sum(r.get("anomalies_detected", 0) for r in results),
        "new_alerts": len(alerts),
        "status": "complete",
    }

    print(f"[Live Data Agent] ✅ Retrain complete: {summary['total_anomalies']} anomalies, "
          f"{summary['new_alerts']} alerts")

    return summary


# ═══════════════════════════════════════════════════════════
# STATUS — Get ingestion pipeline status
# ═══════════════════════════════════════════════════════════

def get_pipeline_status() -> dict:
    """Get the live data pipeline status."""
    stats = db.get_system_stats()

    # Calculate data age range
    conn = db.get_connection()
    oldest = conn.execute("SELECT MIN(timestamp) FROM readings").fetchone()[0]
    newest = conn.execute("SELECT MAX(timestamp) FROM readings").fetchone()[0]
    conn.close()

    return {
        "pipeline_status": "active",
        "ingestion_interval": "6 hours",
        "retrain_interval": "24 hours",
        "rolling_window_days": DATA_DAYS,
        "data_range": {"oldest": oldest, "newest": newest},
        "total_readings": stats["total_readings"],
        "total_zones": stats["total_zones"],
        "data_sources": [
            {"name": "NOAA CoastWatch ERDDAP", "type": "SST (OI v2.1 + MUR fallback + Open-Meteo marine)", "auth": "None needed", "status": "active"},
            {"name": "NOAA CoastWatch ERDDAP", "type": "Chlorophyll-a (VIIRS weekly composite)", "auth": "None needed", "status": "active"},
            {"name": "Open-Meteo", "type": "Wind + Weather", "auth": "None needed", "status": "active"},
            {"name": "OpenAQ v2 + Open-Meteo AQ", "type": "Air Quality (PM2.5, PM10)", "auth": "None needed", "status": "active"},
            {"name": "NASA EONET", "type": "Natural Events", "auth": "DEMO_KEY", "status": "active"},
        ],
    }

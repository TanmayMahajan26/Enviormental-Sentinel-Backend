"""
⏰ SCHEDULER — Background Task Engine
Runs the live data pipeline automatically:

- Every 6 HOURS: Fetch real-world data from NOAA, OpenAQ, Open-Meteo
- Every 24 HOURS: Retrain ML models on the rolling 90-day window
- Continuous: Rolling window pruning (data > 90 days is deleted)

Uses asyncio background tasks (no external dependencies needed).
"""
import asyncio
from datetime import datetime, timezone

# Track last run times and status
_scheduler_status = {
    "running": False,
    "last_ingestion": None,
    "last_retrain": None,
    "next_ingestion": None,
    "next_retrain": None,
    "ingestion_count": 0,
    "retrain_count": 0,
    "errors": [],
}

# Intervals in seconds
INGEST_INTERVAL = 6 * 3600    # 6 hours
RETRAIN_INTERVAL = 24 * 3600  # 24 hours


async def _ingestion_loop():
    """Background loop: fetch real-world data every 6 hours."""
    from agents.live_data_agent import ingest_live_data

    while True:
        try:
            _scheduler_status["last_ingestion"] = datetime.now(timezone.utc).isoformat()
            _scheduler_status["ingestion_count"] += 1

            result = await ingest_live_data()
            print(f"[Scheduler] ✅ Ingestion #{_scheduler_status['ingestion_count']} complete")

        except Exception as e:
            error_msg = f"Ingestion error at {datetime.now(timezone.utc).isoformat()}: {str(e)}"
            print(f"[Scheduler] ❌ {error_msg}")
            _scheduler_status["errors"].append(error_msg)
            # Keep only last 10 errors
            _scheduler_status["errors"] = _scheduler_status["errors"][-10:]

        _scheduler_status["next_ingestion"] = (
            datetime.now(timezone.utc).isoformat()
        )
        await asyncio.sleep(INGEST_INTERVAL)


async def _retrain_loop():
    """Background loop: retrain ML models every 24 hours."""
    from agents.live_data_agent import retrain_models

    # Wait 1 hour before first retrain (let some data accumulate)
    await asyncio.sleep(3600)

    while True:
        try:
            _scheduler_status["last_retrain"] = datetime.now(timezone.utc).isoformat()
            _scheduler_status["retrain_count"] += 1

            result = await retrain_models()
            print(f"[Scheduler] ✅ Retrain #{_scheduler_status['retrain_count']} complete")

        except Exception as e:
            error_msg = f"Retrain error at {datetime.now(timezone.utc).isoformat()}: {str(e)}"
            print(f"[Scheduler] ❌ {error_msg}")
            _scheduler_status["errors"].append(error_msg)
            _scheduler_status["errors"] = _scheduler_status["errors"][-10:]

        _scheduler_status["next_retrain"] = (
            datetime.now(timezone.utc).isoformat()
        )
        await asyncio.sleep(RETRAIN_INTERVAL)


async def start_scheduler():
    """
    Start background scheduler tasks.
    Called from FastAPI lifespan.
    """
    if _scheduler_status["running"]:
        print("[Scheduler] Already running, skipping.")
        return

    _scheduler_status["running"] = True
    print("\n[Scheduler] ⏰ Starting background tasks:")
    print(f"  📡 Data ingestion: every {INGEST_INTERVAL // 3600} hours")
    print(f"  🧠 Model retraining: every {RETRAIN_INTERVAL // 3600} hours")

    # Run first ingestion immediately
    asyncio.create_task(_ingestion_loop())
    asyncio.create_task(_retrain_loop())

    print("[Scheduler] ✅ Background tasks started\n")


def get_scheduler_status() -> dict:
    """Get current scheduler status."""
    return {
        **_scheduler_status,
        "ingest_interval_hours": INGEST_INTERVAL // 3600,
        "retrain_interval_hours": RETRAIN_INTERVAL // 3600,
    }

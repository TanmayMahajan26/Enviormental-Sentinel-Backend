"""
Database setup and operations for Environmental Sentinel.
Uses SQLite for zero-config hackathon deployment.
"""
import sqlite3
import os
import json
from config import DB_PATH


def get_db_path():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return DB_PATH


def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create all tables."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        -- Monitored zones
        CREATE TABLE IF NOT EXISTS zones (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            region TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            description TEXT,
            baseline_sst REAL,
            baseline_chlorophyll REAL,
            baseline_wind REAL,
            baseline_ph REAL,
            baseline_turbidity REAL
        );

        -- Time-series sensor readings (90 days * 24 hours * 8 zones)
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            zone_id TEXT NOT NULL,
            sst REAL,
            chlorophyll REAL,
            wind_speed REAL,
            ph REAL,
            turbidity REAL,
            FOREIGN KEY (zone_id) REFERENCES zones(id)
        );

        -- Detected anomalies from Analysis Agent
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            signal TEXT NOT NULL,
            anomaly_score REAL,
            z_score REAL,
            value REAL,
            expected_value REAL,
            deviation_pct REAL,
            is_processed INTEGER DEFAULT 0,
            FOREIGN KEY (zone_id) REFERENCES zones(id)
        );

        -- Prioritized alerts from Decision Agent
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            severity TEXT NOT NULL,
            priority_score REAL NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            signals_involved TEXT,
            magnitude_score REAL,
            recency_score REAL,
            trajectory_score REAL,
            convergence_score REAL,
            is_suppressed INTEGER DEFAULT 0,
            feedback TEXT,
            feedback_notes TEXT,
            feedback_timestamp TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (zone_id) REFERENCES zones(id)
        );

        -- Zone sensitivity (Memory Agent adaptive thresholds)
        CREATE TABLE IF NOT EXISTS zone_sensitivity (
            zone_id TEXT PRIMARY KEY,
            sensitivity REAL DEFAULT 1.0,
            total_alerts INTEGER DEFAULT 0,
            validated_alerts INTEGER DEFAULT 0,
            false_positive_alerts INTEGER DEFAULT 0,
            precision_rate REAL DEFAULT 0.5,
            last_updated TEXT,
            FOREIGN KEY (zone_id) REFERENCES zones(id)
        );

        -- Feedback log for audit trail
        CREATE TABLE IF NOT EXISTS feedback_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id INTEGER NOT NULL,
            zone_id TEXT NOT NULL,
            feedback TEXT NOT NULL,
            notes TEXT,
            sensitivity_before REAL,
            sensitivity_after REAL,
            timestamp TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (alert_id) REFERENCES alerts(id),
            FOREIGN KEY (zone_id) REFERENCES zones(id)
        );

        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_readings_zone_time ON readings(zone_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_anomalies_zone ON anomalies(zone_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_alerts_zone ON alerts(zone_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_alerts_priority ON alerts(priority_score DESC);
    """)

    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully.")


def seed_zones():
    """Load zone definitions from zones.json into database."""
    from config import ZONES_PATH
    conn = get_connection()
    cursor = conn.cursor()

    # Check if zones already seeded
    count = cursor.execute("SELECT COUNT(*) FROM zones").fetchone()[0]
    if count > 0:
        conn.close()
        return

    with open(ZONES_PATH, "r") as f:
        zones = json.load(f)

    for z in zones:
        cursor.execute("""
            INSERT OR IGNORE INTO zones (id, name, region, lat, lng, description,
                baseline_sst, baseline_chlorophyll, baseline_wind, baseline_ph, baseline_turbidity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            z["id"], z["name"], z["region"], z["lat"], z["lng"], z["description"],
            z["baseline_sst"], z["baseline_chlorophyll"], z["baseline_wind"],
            z["baseline_ph"], z["baseline_turbidity"]
        ))

    # Initialize zone sensitivity for Memory Agent
    for z in zones:
        cursor.execute("""
            INSERT OR IGNORE INTO zone_sensitivity (zone_id, sensitivity, last_updated)
            VALUES (?, 1.0, datetime('now'))
        """, (z["id"],))

    conn.commit()
    conn.close()
    print(f"[DB] Seeded {len(zones)} Indian coastal zones.")


def get_all_zones():
    conn = get_connection()
    zones = conn.execute("SELECT * FROM zones").fetchall()
    conn.close()
    return [dict(z) for z in zones]


def get_zone(zone_id: str):
    conn = get_connection()
    zone = conn.execute("SELECT * FROM zones WHERE id = ?", (zone_id,)).fetchone()
    conn.close()
    return dict(zone) if zone else None


def insert_readings_batch(readings: list[dict]):
    conn = get_connection()
    conn.executemany("""
        INSERT INTO readings (timestamp, zone_id, sst, chlorophyll, wind_speed, ph, turbidity)
        VALUES (:timestamp, :zone_id, :sst, :chlorophyll, :wind_speed, :ph, :turbidity)
    """, readings)
    conn.commit()
    conn.close()


def get_readings(zone_id: str, limit: int = 2160, offset: int = 0):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM readings WHERE zone_id = ?
        ORDER BY timestamp ASC LIMIT ? OFFSET ?
    """, (zone_id, limit, offset)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_readings_count(zone_id: str):
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM readings WHERE zone_id = ?", (zone_id,)
    ).fetchone()[0]
    conn.close()
    return count


def get_all_readings_for_zone(zone_id: str):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM readings WHERE zone_id = ? ORDER BY timestamp ASC
    """, (zone_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_anomalies_batch(anomalies: list[dict]):
    conn = get_connection()
    conn.executemany("""
        INSERT INTO anomalies (zone_id, timestamp, signal, anomaly_score, z_score,
            value, expected_value, deviation_pct)
        VALUES (:zone_id, :timestamp, :signal, :anomaly_score, :z_score,
            :value, :expected_value, :deviation_pct)
    """, anomalies)
    conn.commit()
    conn.close()


def get_anomalies(zone_id: str = None, limit: int = 100):
    conn = get_connection()
    if zone_id:
        rows = conn.execute("""
            SELECT a.*, z.name as zone_name FROM anomalies a
            JOIN zones z ON a.zone_id = z.id
            WHERE a.zone_id = ?
            ORDER BY a.timestamp DESC LIMIT ?
        """, (zone_id, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT a.*, z.name as zone_name FROM anomalies a
            JOIN zones z ON a.zone_id = z.id
            ORDER BY a.timestamp DESC LIMIT ?
        """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_alert(alert: dict):
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO alerts (zone_id, timestamp, severity, priority_score, title,
            description, signals_involved, magnitude_score, recency_score,
            trajectory_score, convergence_score, is_suppressed)
        VALUES (:zone_id, :timestamp, :severity, :priority_score, :title,
            :description, :signals_involved, :magnitude_score, :recency_score,
            :trajectory_score, :convergence_score, :is_suppressed)
    """, alert)
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return alert_id


def get_alerts(include_suppressed: bool = False, limit: int = 50):
    conn = get_connection()
    if include_suppressed:
        rows = conn.execute("""
            SELECT a.*, z.name as zone_name FROM alerts a
            JOIN zones z ON a.zone_id = z.id
            ORDER BY a.priority_score DESC LIMIT ?
        """, (limit,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT a.*, z.name as zone_name FROM alerts a
            JOIN zones z ON a.zone_id = z.id
            WHERE a.is_suppressed = 0
            ORDER BY a.priority_score DESC LIMIT ?
        """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_alert_feedback(alert_id: int, feedback: str, notes: str = None):
    conn = get_connection()
    conn.execute("""
        UPDATE alerts SET feedback = ?, feedback_notes = ?,
            feedback_timestamp = datetime('now')
        WHERE id = ?
    """, (feedback, notes, alert_id))
    conn.commit()

    # Get the alert for zone info
    alert = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
    conn.close()
    return dict(alert) if alert else None


def get_zone_sensitivity(zone_id: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM zone_sensitivity WHERE zone_id = ?", (zone_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_zone_sensitivity(zone_id: str, new_sensitivity: float,
                            total: int, validated: int, false_pos: int, precision: float):
    conn = get_connection()
    conn.execute("""
        UPDATE zone_sensitivity
        SET sensitivity = ?, total_alerts = ?, validated_alerts = ?,
            false_positive_alerts = ?, precision_rate = ?, last_updated = datetime('now')
        WHERE zone_id = ?
    """, (new_sensitivity, total, validated, false_pos, precision, zone_id))
    conn.commit()
    conn.close()


def insert_feedback_log(log: dict):
    conn = get_connection()
    conn.execute("""
        INSERT INTO feedback_log (alert_id, zone_id, feedback, notes,
            sensitivity_before, sensitivity_after)
        VALUES (:alert_id, :zone_id, :feedback, :notes,
            :sensitivity_before, :sensitivity_after)
    """, log)
    conn.commit()
    conn.close()


def get_system_stats():
    conn = get_connection()
    stats = {
        "total_zones": conn.execute("SELECT COUNT(*) FROM zones").fetchone()[0],
        "total_readings": conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0],
        "total_anomalies": conn.execute("SELECT COUNT(*) FROM anomalies").fetchone()[0],
        "total_alerts": conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0],
        "total_suppressed": conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE is_suppressed = 1"
        ).fetchone()[0],
        "total_feedback": conn.execute("SELECT COUNT(*) FROM feedback_log").fetchone()[0],
        "validated_count": conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE feedback = 'validated'"
        ).fetchone()[0],
        "false_pos_count": conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE feedback = 'false_positive'"
        ).fetchone()[0],
    }
    conn.close()
    total_with_feedback = stats["validated_count"] + stats["false_pos_count"]
    stats["model_accuracy"] = (
        stats["validated_count"] / total_with_feedback
        if total_with_feedback > 0
        else 0.5
    )
    return stats

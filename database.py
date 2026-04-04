"""
Database setup and operations for Environmental Sentinel.
Uses SQLite for local dev and PostgreSQL (Neon) for production.
"""
import sqlite3
import os
import json
import re
from config import DB_PATH, DATABASE_URL

# Optional PostgreSQL support
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import psycopg2.extensions
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False


def get_db_path():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return DB_PATH


def get_connection():
    """Returns a connection to either SQLite or PostgreSQL based on environment."""
    if DATABASE_URL and (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")):
        if not HAS_POSTGRES:
            print("[DB] WARNING: DATABASE_URL provided but psycopg2-binary not installed. Falling back to SQLite.")
        else:
            try:
                # Support the 'postgres://' schema which some providers use but psycopg2 prefers 'postgresql://'
                url = DATABASE_URL.replace("postgres://", "postgresql://")
                conn = psycopg2.connect(url)
                conn.autocommit = True
                return conn
            except Exception as e:
                print(f"[DB] ERROR connecting to PostgreSQL: {e}. Falling back to SQLite.")

    # Default to SQLite
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def is_postgres(conn):
    """Check if the connection is a PostgreSQL connection."""
    return HAS_POSTGRES and isinstance(conn, psycopg2.extensions.connection)


def init_db():
    """Create all tables with cross-compatible syntax."""
    conn = get_connection()
    is_pg = is_postgres(conn)
    cursor = conn.cursor()
    
    # Text/String type and ID Auto-increment differ
    STR_TYPE = "TEXT"
    ID_TYPE = "SERIAL PRIMARY KEY" if is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    
    # Base schema
    queries = [
        f"""
        CREATE TABLE IF NOT EXISTS zones (
            id {STR_TYPE} PRIMARY KEY,
            name {STR_TYPE} NOT NULL,
            region {STR_TYPE} NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            description {STR_TYPE},
            baseline_sst REAL,
            baseline_chlorophyll REAL,
            baseline_wind REAL,
            baseline_ph REAL,
            baseline_turbidity REAL
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS readings (
            id {ID_TYPE},
            timestamp {STR_TYPE} NOT NULL,
            zone_id {STR_TYPE} NOT NULL,
            sst REAL,
            chlorophyll REAL,
            wind_speed REAL,
            ph REAL,
            turbidity REAL,
            FOREIGN KEY (zone_id) REFERENCES zones(id)
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS anomalies (
            id {ID_TYPE},
            zone_id {STR_TYPE} NOT NULL,
            timestamp {STR_TYPE} NOT NULL,
            signal {STR_TYPE} NOT NULL,
            anomaly_score REAL,
            z_score REAL,
            value REAL,
            expected_value REAL,
            deviation_pct REAL,
            is_processed INTEGER DEFAULT 0,
            FOREIGN KEY (zone_id) REFERENCES zones(id)
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS alerts (
            id {ID_TYPE},
            zone_id {STR_TYPE} NOT NULL,
            timestamp {STR_TYPE} NOT NULL,
            severity {STR_TYPE} NOT NULL,
            priority_score REAL NOT NULL,
            title {STR_TYPE} NOT NULL,
            description {STR_TYPE},
            signals_involved {STR_TYPE},
            magnitude_score REAL,
            recency_score REAL,
            trajectory_score REAL,
            convergence_score REAL,
            is_suppressed INTEGER DEFAULT 0,
            feedback {STR_TYPE},
            feedback_notes {STR_TYPE},
            feedback_timestamp {STR_TYPE},
            created_at {STR_TYPE} DEFAULT {'CURRENT_TIMESTAMP' if is_pg else "(datetime('now'))"},
            FOREIGN KEY (zone_id) REFERENCES zones(id)
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS zone_sensitivity (
            zone_id {STR_TYPE} PRIMARY KEY,
            sensitivity REAL DEFAULT 1.0,
            total_alerts INTEGER DEFAULT 0,
            validated_alerts INTEGER DEFAULT 0,
            false_positive_alerts INTEGER DEFAULT 0,
            precision_rate REAL DEFAULT 0.5,
            last_updated {STR_TYPE},
            FOREIGN KEY (zone_id) REFERENCES zones(id)
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS feedback_log (
            id {ID_TYPE},
            alert_id INTEGER NOT NULL,
            zone_id {STR_TYPE} NOT NULL,
            feedback {STR_TYPE} NOT NULL,
            notes {STR_TYPE},
            sensitivity_before REAL,
            sensitivity_after REAL,
            timestamp {STR_TYPE} DEFAULT {'CURRENT_TIMESTAMP' if is_pg else "(datetime('now'))"},
            FOREIGN KEY (alert_id) REFERENCES alerts(id),
            FOREIGN KEY (zone_id) REFERENCES zones(id)
        )"""
    ]
    
    for q in queries:
        try:
            cursor.execute(q)
        except Exception as e:
            # If workers race to create tables, ignore "already exists" or concurrency errors
            if "already exists" in str(e).lower() or "unique_violation" in str(e).lower():
                continue
            raise e

    # Indexes
    if not is_pg:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_zone_time ON readings(zone_id, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_zone ON anomalies(zone_id, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_zone ON alerts(zone_id, timestamp)")
        conn.commit()

    conn.close()
    print(f"[DB] Initialized successfully on {'PostgreSQL' if is_pg else 'SQLite'}.")


def seed_zones():
    """Load zone definitions from zones.json into database."""
    from config import ZONES_PATH
    conn = get_connection()
    is_pg = is_postgres(conn)
    cursor = conn.cursor()

    # Check if zones already seeded
    cursor.execute("SELECT COUNT(*) FROM zones")
    count = cursor.fetchone()[0]
    if count > 0:
        conn.close()
        return

    with open(ZONES_PATH, "r") as f:
        zones = json.load(f)

    for z in zones:
        if is_pg:
            query = """
                INSERT INTO zones (id, name, region, lat, lng, description,
                    baseline_sst, baseline_chlorophyll, baseline_wind, baseline_ph, baseline_turbidity)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """
        else:
            query = """
                INSERT OR IGNORE INTO zones (id, name, region, lat, lng, description,
                    baseline_sst, baseline_chlorophyll, baseline_wind, baseline_ph, baseline_turbidity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
        cursor.execute(query, (
            z["id"], z["name"], z["region"], z["lat"], z["lng"], z["description"],
            z["baseline_sst"], z["baseline_chlorophyll"], z["baseline_wind"],
            z["baseline_ph"], z["baseline_turbidity"]
        ))

    # Initialize zone sensitivity
    now = "CURRENT_TIMESTAMP" if is_pg else "datetime('now')"
    for z in zones:
        if is_pg:
            query = f"INSERT INTO zone_sensitivity (zone_id, sensitivity, last_updated) VALUES (%s, 1.0, {now}) ON CONFLICT (zone_id) DO NOTHING"
        else:
            query = f"INSERT OR IGNORE INTO zone_sensitivity (zone_id, sensitivity, last_updated) VALUES (?, 1.0, {now})"
        cursor.execute(query, (z["id"],))

    if not is_pg:
        conn.commit()
    conn.close()
    print(f"[DB] Seeded {len(zones)} Indian coastal zones.")


def get_all_zones():
    conn = get_connection()
    is_pg = is_postgres(conn)
    cursor = conn.cursor(cursor_factory=RealDictCursor) if is_pg else conn.cursor()
    cursor.execute("SELECT * FROM zones")
    zones = cursor.fetchall()
    conn.close()
    return [dict(z) for z in zones]


def get_zone(zone_id: str):
    conn = get_connection()
    is_pg = is_postgres(conn)
    cursor = conn.cursor(cursor_factory=RealDictCursor) if is_pg else conn.cursor()
    query = "SELECT * FROM zones WHERE id = %s" if is_pg else "SELECT * FROM zones WHERE id = ?"
    cursor.execute(query, (zone_id,))
    zone = cursor.fetchone()
    conn.close()
    return dict(zone) if zone else None


def insert_readings_batch(readings: list[dict]):
    conn = get_connection()
    is_pg = is_postgres(conn)
    cursor = conn.cursor()
    if is_pg:
        query = """
            INSERT INTO readings (timestamp, zone_id, sst, chlorophyll, wind_speed, ph, turbidity)
            VALUES (%(timestamp)s, %(zone_id)s, %(sst)s, %(chlorophyll)s, %(wind_speed)s, %(ph)s, %(turbidity)s)
        """
    else:
        query = """
            INSERT INTO readings (timestamp, zone_id, sst, chlorophyll, wind_speed, ph, turbidity)
            VALUES (:timestamp, :zone_id, :sst, :chlorophyll, :wind_speed, :ph, :turbidity)
        """
    cursor.executemany(query, readings)
    if not is_pg:
        conn.commit()
    conn.close()


def get_readings(zone_id: str, limit: int = 2160, offset: int = 0):
    conn = get_connection()
    is_pg = is_postgres(conn)
    cursor = conn.cursor(cursor_factory=RealDictCursor) if is_pg else conn.cursor()
    query = "SELECT * FROM readings WHERE zone_id = %s ORDER BY timestamp ASC LIMIT %s OFFSET %s" if is_pg else "SELECT * FROM readings WHERE zone_id = ? ORDER BY timestamp ASC LIMIT ? OFFSET ?"
    cursor.execute(query, (zone_id, limit, offset))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_readings_count(zone_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT COUNT(*) FROM readings WHERE zone_id = %s" if is_postgres(conn) else "SELECT COUNT(*) FROM readings WHERE zone_id = ?"
    cursor.execute(query, (zone_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count


def insert_anomalies_batch(anomalies: list[dict]):
    conn = get_connection()
    is_pg = is_postgres(conn)
    cursor = conn.cursor()
    if is_pg:
        query = "INSERT INTO anomalies (zone_id, timestamp, signal, anomaly_score, z_score, value, expected_value, deviation_pct) VALUES (%(zone_id)s, %(timestamp)s, %(signal)s, %(anomaly_score)s, %(z_score)s, %(value)s, %(expected_value)s, %(deviation_pct)s)"
    else:
        query = "INSERT INTO anomalies (zone_id, timestamp, signal, anomaly_score, z_score, value, expected_value, deviation_pct) VALUES (:zone_id, :timestamp, :signal, :anomaly_score, :z_score, :value, :expected_value, :deviation_pct)"
    cursor.executemany(query, anomalies)
    if not is_pg:
        conn.commit()
    conn.close()


def get_anomalies(zone_id: str = None, limit: int = 100):
    conn = get_connection()
    is_pg = is_postgres(conn)
    cursor = conn.cursor(cursor_factory=RealDictCursor) if is_pg else conn.cursor()
    if zone_id:
        query = "SELECT a.*, z.name as zone_name FROM anomalies a JOIN zones z ON a.zone_id = z.id WHERE a.zone_id = %s ORDER BY a.timestamp DESC LIMIT %s" if is_pg else "SELECT a.*, z.name as zone_name FROM anomalies a JOIN zones z ON a.zone_id = z.id WHERE a.zone_id = ? ORDER BY a.timestamp DESC LIMIT ?"
        cursor.execute(query, (zone_id, limit))
    else:
        query = "SELECT a.*, z.name as zone_name FROM anomalies a JOIN zones z ON a.zone_id = z.id ORDER BY a.timestamp DESC LIMIT %s" if is_pg else "SELECT a.*, z.name as zone_name FROM anomalies a JOIN zones z ON a.zone_id = z.id ORDER BY a.timestamp DESC LIMIT ?"
        cursor.execute(query, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_alert(alert: dict):
    conn = get_connection()
    is_pg = is_postgres(conn)
    cursor = conn.cursor()
    if is_pg:
        query = "INSERT INTO alerts (zone_id, timestamp, severity, priority_score, title, description, signals_involved, magnitude_score, recency_score, trajectory_score, convergence_score, is_suppressed) VALUES (%(zone_id)s, %(timestamp)s, %(severity)s, %(priority_score)s, %(title)s, %(description)s, %(signals_involved)s, %(magnitude_score)s, %(recency_score)s, %(trajectory_score)s, %(convergence_score)s, %(is_suppressed)s) RETURNING id"
        cursor.execute(query, alert)
        alert_id = cursor.fetchone()[0]
    else:
        query = "INSERT INTO alerts (zone_id, timestamp, severity, priority_score, title, description, signals_involved, magnitude_score, recency_score, trajectory_score, convergence_score, is_suppressed) VALUES (:zone_id, :timestamp, :severity, :priority_score, :title, :description, :signals_involved, :magnitude_score, :recency_score, :trajectory_score, :convergence_score, :is_suppressed)"
        cursor.execute(query, alert)
        alert_id = cursor.lastrowid
        conn.commit()
    conn.close()
    return alert_id


def get_alerts(include_suppressed: bool = False, limit: int = 50):
    conn = get_connection()
    is_pg = is_postgres(conn)
    cursor = conn.cursor(cursor_factory=RealDictCursor) if is_pg else conn.cursor()
    base = "SELECT a.*, z.name as zone_name FROM alerts a JOIN zones z ON a.zone_id = z.id"
    filt = "" if include_suppressed else "WHERE a.is_suppressed = 0"
    order = "ORDER BY a.priority_score DESC LIMIT %s" if is_pg else "ORDER BY a.priority_score DESC LIMIT ?"
    cursor.execute(f"{base} {filt} {order}", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_alert_feedback(alert_id: int, feedback: str, notes: str = None):
    conn = get_connection()
    is_pg = is_postgres(conn)
    cursor = conn.cursor(cursor_factory=RealDictCursor) if is_pg else conn.cursor()
    now = "CURRENT_TIMESTAMP" if is_pg else "datetime('now')"
    query = f"UPDATE alerts SET feedback = %s, feedback_notes = %s, feedback_timestamp = {now} WHERE id = %s" if is_pg else f"UPDATE alerts SET feedback = ?, feedback_notes = ?, feedback_timestamp = {now} WHERE id = ?"
    cursor.execute(query, (feedback, notes, alert_id))
    cursor.execute("SELECT * FROM alerts WHERE id = %s" if is_pg else "SELECT * FROM alerts WHERE id = ?", (alert_id,))
    alert = cursor.fetchone()
    if not is_pg: conn.commit()
    conn.close()
    return dict(alert) if alert else None


def get_zone_sensitivity(zone_id: str):
    conn = get_connection()
    is_pg = is_postgres(conn)
    cursor = conn.cursor(cursor_factory=RealDictCursor) if is_pg else conn.cursor()
    query = "SELECT * FROM zone_sensitivity WHERE zone_id = %s" if is_pg else "SELECT * FROM zone_sensitivity WHERE zone_id = ?"
    cursor.execute(query, (zone_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_zone_sensitivity(zone_id: str, new_sensitivity: float, total: int, validated: int, false_pos: int, precision: float):
    conn = get_connection()
    is_pg = is_postgres(conn)
    cursor = conn.cursor()
    now = "CURRENT_TIMESTAMP" if is_pg else "datetime('now')"
    query = f"UPDATE zone_sensitivity SET sensitivity = %s, total_alerts = %s, validated_alerts = %s, false_positive_alerts = %s, precision_rate = %s, last_updated = {now} WHERE zone_id = %s" if is_pg else f"UPDATE zone_sensitivity SET sensitivity = ?, total_alerts = ?, validated_alerts = ?, false_positive_alerts = ?, precision_rate = ?, last_updated = {now} WHERE zone_id = ?"
    cursor.execute(query, (new_sensitivity, total, validated, false_pos, precision, zone_id))
    if not is_pg: conn.commit()
    conn.close()


def insert_feedback_log(log: dict):
    conn = get_connection()
    is_pg = is_postgres(conn)
    cursor = conn.cursor()
    if is_pg:
        query = "INSERT INTO feedback_log (alert_id, zone_id, feedback, notes, sensitivity_before, sensitivity_after, timestamp) VALUES (%(alert_id)s, %(zone_id)s, %(feedback)s, %(notes)s, %(sensitivity_before)s, %(sensitivity_after)s, CURRENT_TIMESTAMP)"
    else:
        query = "INSERT INTO feedback_log (alert_id, zone_id, feedback, notes, sensitivity_before, sensitivity_after) VALUES (:alert_id, :zone_id, :feedback, :notes, :sensitivity_before, :sensitivity_after)"
    cursor.execute(query, log)
    if not is_pg: conn.commit()
    conn.close()


def get_system_stats():
    conn = get_connection()
    cursor = conn.cursor()
    stats = {
        "total_zones": cursor.execute("SELECT COUNT(*) FROM zones").fetchone()[0],
        "total_readings": cursor.execute("SELECT COUNT(*) FROM readings").fetchone()[0],
        "total_anomalies": cursor.execute("SELECT COUNT(*) FROM anomalies").fetchone()[0],
        "total_alerts": cursor.execute("SELECT COUNT(*) FROM alerts").fetchone()[0],
        "total_suppressed": cursor.execute("SELECT COUNT(*) FROM alerts WHERE is_suppressed = 1").fetchone()[0],
        "total_feedback": cursor.execute("SELECT COUNT(*) FROM feedback_log").fetchone()[0],
        "validated_count": cursor.execute("SELECT COUNT(*) FROM alerts WHERE feedback = 'validated'").fetchone()[0],
        "false_pos_count": cursor.execute("SELECT COUNT(*) FROM alerts WHERE feedback = 'false_positive'").fetchone()[0],
    }
    conn.close()
    total_with_feedback = stats["validated_count"] + stats["false_pos_count"]
    stats["model_accuracy"] = stats["validated_count"] / total_with_feedback if total_with_feedback > 0 else 0.5
    return stats

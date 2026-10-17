"""Migrate existing AirPurify AI data from SQLite to MongoDB Atlas."""

import os
import sqlite3
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment configuration
load_dotenv()

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "..", "airpurify.db")
MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://francisjaison2005_db_user:VKi8KDDqGchXfDKS@cluster0.9tdvmma.mongodb.net/?retryWrites=true&w=majority",
)
DB_NAME = os.getenv("MONGODB_DB_NAME", "airpurify_db")


def parse_dt(dt_str):
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return dt_str


def run_migration():
    print("=" * 60)
    print("AirPurify AI — SQLite to MongoDB Atlas Migration")
    print("=" * 60)
    print(f"Source SQLite DB: {SQLITE_PATH}")
    print(f"Target MongoDB DB: {DB_NAME}")

    if not os.path.exists(SQLITE_PATH):
        print(f"Error: Source database '{SQLITE_PATH}' not found.")
        return False

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
    # Test connection
    mongo_client.admin.command("ping")
    print("MongoDB Atlas connection established successfully.")

    db = mongo_client[DB_NAME]

    # 1. Migrate Devices
    print("\n[1/4] Migrating Devices...")
    cur = sqlite_conn.execute("SELECT * FROM devices ORDER BY id ASC")
    device_rows = cur.fetchall()
    devices_migrated = 0
    max_device_id = 0
    for row in device_rows:
        d = dict(row)
        max_device_id = max(max_device_id, d["id"])
        doc = {
            "id": d["id"],
            "device_id": d["device_id"],
            "device_name": d["device_name"],
            "location_id": d["location_id"],
            "last_seen": parse_dt(d["last_seen"]),
            "status": d["status"],
            "firmware_version": d.get("firmware_version"),
        }
        db["devices"].replace_one({"id": d["id"]}, doc, upsert=True)
        devices_migrated += 1
    db["counters"].update_one(
        {"_id": "devices_id"},
        {"$max": {"seq": max_device_id}},
        upsert=True,
    )
    print(f"  -> Migrated {devices_migrated} devices (Max ID: {max_device_id}).")

    # 2. Migrate Sensor Readings
    print("\n[2/4] Migrating Sensor Readings...")
    cur = sqlite_conn.execute("SELECT * FROM sensor_readings ORDER BY id ASC")
    reading_rows = cur.fetchall()
    readings_migrated = 0
    max_reading_id = 0
    for row in reading_rows:
        r = dict(row)
        max_reading_id = max(max_reading_id, r["id"])
        doc = {
            "id": r["id"],
            "device_id": r["device_id"],
            "location_id": r["location_id"],
            "timestamp": parse_dt(r["timestamp"]),
            "received_at": parse_dt(r["received_at"]),
            "pm1_0": r["pm1_0"],
            "pm2_5": r["pm2_5"],
            "pm10": r["pm10"],
            "data_quality_status": r["data_quality_status"],
        }
        db["sensor_readings"].replace_one({"id": r["id"]}, doc, upsert=True)
        readings_migrated += 1
    db["counters"].update_one(
        {"_id": "readings_id"},
        {"$max": {"seq": max_reading_id}},
        upsert=True,
    )
    print(f"  -> Migrated {readings_migrated} sensor readings (Max ID: {max_reading_id}).")

    # 3. Migrate Alerts
    print("\n[3/4] Migrating Alerts...")
    cur = sqlite_conn.execute("SELECT * FROM alerts ORDER BY id ASC")
    alert_rows = cur.fetchall()
    alerts_migrated = 0
    max_alert_id = 0
    for row in alert_rows:
        a = dict(row)
        max_alert_id = max(max_alert_id, a["id"])
        doc = {
            "id": a["id"],
            "device_id": a["device_id"],
            "location_id": a["location_id"],
            "alert_type": a["alert_type"],
            "severity": a["severity"],
            "message": a["message"],
            "triggered_at": parse_dt(a["triggered_at"]),
            "status": a["status"],
        }
        db["alerts"].replace_one({"id": a["id"]}, doc, upsert=True)
        alerts_migrated += 1
    db["counters"].update_one(
        {"_id": "alerts_id"},
        {"$max": {"seq": max_alert_id}},
        upsert=True,
    )
    print(f"  -> Migrated {alerts_migrated} alerts (Max ID: {max_alert_id}).")

    # 4. Migrate Forecasts
    print("\n[4/4] Migrating Forecasts...")
    cur = sqlite_conn.execute("SELECT * FROM forecasts ORDER BY id ASC")
    forecast_rows = cur.fetchall()
    forecasts_migrated = 0
    max_forecast_id = 0
    for row in forecast_rows:
        f = dict(row)
        max_forecast_id = max(max_forecast_id, f["id"])
        doc = {
            "id": f["id"],
            "location_id": f["location_id"],
            "model_name": f["model_name"],
            "model_version": f["model_version"],
            "issued_at": parse_dt(f["issued_at"]),
            "target_time": parse_dt(f["target_time"]),
            "horizon_hours": f["horizon_hours"],
            "predicted_aqi": f["predicted_aqi"],
            "predicted_pm25": f.get("predicted_pm25"),
            "predicted_pm10": f.get("predicted_pm10"),
            "confidence_interval_lower": f.get("confidence_interval_lower"),
            "confidence_interval_upper": f.get("confidence_interval_upper"),
            "status": f["status"],
        }
        db["forecasts"].replace_one({"id": f["id"]}, doc, upsert=True)
        forecasts_migrated += 1
    db["counters"].update_one(
        {"_id": "forecasts_id"},
        {"$max": {"seq": max_forecast_id}},
        upsert=True,
    )
    print(f"  -> Migrated {forecasts_migrated} forecasts (Max ID: {max_forecast_id}).")

    # 5. Create Indexes
    print("\n[5/5] Ensuring MongoDB Collection Indexes...")
    db["devices"].create_index("device_id", unique=True)
    db["devices"].create_index("id", unique=True)
    db["sensor_readings"].create_index([("device_id", 1), ("timestamp", -1)])
    db["sensor_readings"].create_index([("location_id", 1), ("timestamp", -1)])
    db["sensor_readings"].create_index([("timestamp", -1)])
    db["sensor_readings"].create_index("id", unique=True)
    db["alerts"].create_index([("device_id", 1), ("alert_type", 1), ("status", 1)])
    db["alerts"].create_index([("triggered_at", -1)])
    db["alerts"].create_index("id", unique=True)
    db["forecasts"].create_index([("location_id", 1), ("target_time", 1)])
    db["forecasts"].create_index("id", unique=True)
    print("  -> All indexes verified.")

    print("\n" + "=" * 60)
    print("MIGRATION COMPLETED SUCCESSFULLY!")
    print(f"Summary: {devices_migrated} devices, {readings_migrated} readings, {alerts_migrated} alerts, {forecasts_migrated} forecasts.")
    print("=" * 60)
    sqlite_conn.close()
    return True


if __name__ == "__main__":
    run_migration()

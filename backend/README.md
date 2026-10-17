# AirPurify AI - Backend Service

High-performance, modular backend service for the AirPurify AI platform built with **FastAPI**, **SQLAlchemy**, and **Pydantic**. Ingests real-time particulate matter telemetry from ESP32 edge sensor nodes, manages device lifecycles, tracks environmental thresholds, enforces regulatory EPA AQI standards, and prepares deep learning interfaces for predictive forecasting.

---

## 1. Project Structure

```text
backend/
├── app/
│   ├── __init__.py               # App package initialization
│   ├── main.py                   # FastAPI application factory, CORS, lifespan & health check
│   ├── database.py               # SQLAlchemy database engine, session factory & Base
│   ├── models.py                 # Database models (SensorReading, Device, Forecast, Alert)
│   ├── schemas.py                # Pydantic validation and serialization schemas
│   ├── routes/
│   │   ├── __init__.py           # Routes package initialization
│   │   ├── readings.py           # Ingestion (POST) & queries (latest, history)
│   │   ├── devices.py            # Device registration and status management
│   │   ├── forecasts.py          # Predictive forecast endpoints & model status
│   │   └── alerts.py             # System & environmental alert management
│   └── services/
│       ├── __init__.py           # Services package initialization
│       ├── aqi.py                # EPA AQI calculation & averaging period validation
│       ├── forecasting.py        # 1D-CNN–BiGRU deep learning forecasting interface
│       └── alerts.py             # Threshold evaluation, stale detection & deduplication
├── tests/
│   ├── __init__.py               # Test package initialization
│   └── test_readings.py          # Automated test suite (15 unit & integration tests)
├── .env.example                  # Safe configuration template
├── requirements.txt              # Production and development dependencies
└── README.md                     # Backend service documentation
```

---

## 2. Installation Instructions

### Prerequisites
- **Python**: Version `3.12.x`
- PowerShell or bash terminal

### Step 1: Navigate to the backend directory
```powershell
cd backend
```

### Step 2: Create a virtual environment (if not already created)
```powershell
py -m venv .venv
```

### Step 3: Activate the virtual environment
- **Windows (PowerShell)**:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt)**:
  ```cmd
  .\.venv\Scripts\activate.bat
  ```
- **macOS / Linux**:
  ```bash
  source .venv/bin/activate
  ```

### Step 4: Upgrade pip and install dependencies
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 5: Configure Environment Variables
Copy the example configuration to `.env`:
```powershell
cp .env.example .env
```

---

## 3. How to Start the Backend

### Development Mode
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```
- In development mode (`APP_ENV=development`), SQLite database tables are auto-initialized at `./airpurify.db`.
- Default dev API keys (`airpurify-dev-key-2026` / `airpurify-admin-dev-key-2026`) are enabled for testing.

### Production Startup Command
In production, run Uvicorn with multiple workers behind an SSL-terminating reverse proxy (e.g. NGINX, Cloudflare):
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips='*'
```

---

## 4. API Documentation & Probes

- **Interactive Swagger UI**: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)
- **ReDoc**: [http://127.0.0.1:8001/redoc](http://127.0.0.1:8001/redoc)
- **Liveness Probe**: `GET /api/health` — Returns process and database connectivity status.
- **Readiness Probe**: `GET /api/ready` — Evaluates database connectivity and 1D-CNN–BiGRU model artifact readiness (returns 503 if weights missing).

---

## 5. Security & Authentication Model

### Header Authentication
AirPurify AI uses constant-time header verification:
- `X-API-Key`: Required for telemetry ingestion (`POST /api/readings`).
- `X-Admin-Key`: Required for device registration (`POST /api/devices`), alert state modification (`PATCH /api/alerts/{id}`), and on-demand model inference (`POST /api/forecasts/predict`).

### Rate Limiting & Protection
- Sliding-window rate limiting per IP: 60 req/min for telemetry ingestion, 20 req/min for AI inference, 120 req/min general.
- Maximum payload size limit: 1 MB enforced by `RequestSizeLimitMiddleware` (HTTP 413 Payload Too Large).
- Production Error Sanitization: Internal stack traces and raw database dumps are suppressed when `DEBUG=false`.
- Safe Audit Logging: `AuditLoggingMiddleware` redacts `Authorization`, `X-API-Key`, `X-Admin-Key`, and cookies.

---

## 6. Database Backups & Recovery

### Automated Online Backup
Non-blocking online backup using SQLite Online Backup API (`sqlite3.backup`):
```bash
python scripts/backup_db.py --retentions 7
```
Backups are saved to `backend/backups/airpurify_backup_YYYYMMDD_HHMMSS.db`.

### Disaster Recovery
1. Stop backend service: `systemctl stop airpurify-backend`
2. Archive damaged database: `mv airpurify.db airpurify.db.broken`
3. Restore from verified backup: `cp backups/airpurify_backup_LATEST.db airpurify.db`
4. Verify SQLite integrity: `sqlite3 airpurify.db "PRAGMA integrity_check;"`
5. Restart service: `systemctl start airpurify-backend`

---

## 7. Available Endpoints

### System & Health (Public)
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/health` | None | Service liveness and database connectivity check |
| `GET` | `/api/ready` | None | Readiness probe checking database and ML model weights |

### Sensor Telemetry
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/readings` | `X-API-Key` | Ingest particulate telemetry from ESP32 edge node |
| `GET` | `/api/readings/latest` | None | Retrieve latest reading (`device_id`, `location_id`) |
| `GET` | `/api/readings/history` | None | Historical telemetry records with time window |

### Devices
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/devices` | None | List registered edge sensor nodes |
| `POST` | `/api/devices` | `X-Admin-Key` | Manually provision a new sensor device |
| `GET` | `/api/devices/{device_id}` | None | Retrieve device details and liveness status |

### Predictive Forecasting (1D-CNN–BiGRU)
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/forecasts` | None | Retrieve forecast records for a location |
| `GET` | `/api/forecasts/status` | None | Check operational status of 1D-CNN–BiGRU model |
| `POST` | `/api/forecasts/predict` | `X-Admin-Key` | Trigger on-demand deep learning inference |

### Alerts
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/alerts` | None | Retrieve alerts (`device_id`, `status`, `severity`) |
| `PATCH` | `/api/alerts/{alert_id}` | `X-Admin-Key` | Acknowledge or resolve an active alert |

---

## 8. How to Run Automated Tests

Run the full pytest suite (40 tests across readings, ML pipeline, and security):
```powershell
python -m pytest -v
```

All 40 automated test cases pass with zero failures:
- 20 readings, devices, alerts, AQI calculation tests (`test_readings.py`)
- 8 chronological splitting, training and 1D-CNN–BiGRU forecasting tests (`test_forecasting.py`)
- 12 authentication, authorization, rate limiting, payload size, error sanitization, and backup tests (`test_security.py`)

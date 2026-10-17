# AirPurify AI — Phase 7: Final Release Preparation Report

**Date:** 2026-10-17  
**Status:** **RELEASE-READY (SOFTWARE FROZEN)**  
**Target Architecture:** React 19 + TypeScript + Vite 8 (Frontend) / FastAPI + SQLAlchemy + SQLite WAL (Backend) / TensorFlow 1D-CNN–BiGRU (Forecasting)  
**Target Hardware:** Espressif ESP32 (ESP-WROOM-32 / ESP32-S3) + Plantower PMS5003 Laser Particulate Sensor (Postponed until hardware stage)  

---

## 1. Executive Release Summary

The Phase 7 Final Release Preparation for **AirPurify AI** has verified that all software components, API contracts, deep learning inference engines, database persistence mechanisms, and security controls are robust, clean, and completely frozen.

> [!IMPORTANT]
> **Strict Pre-IoT Non-Hardware Constraint Maintained:** No physical ESP32 or PMS5003 hardware was connected or claimed as connected during this phase. All verification was executed using explicitly labelled synthetic test telemetry (`SYNTHETIC-PHASE7-NODE-01` and `SYNTHETIC-PRE-IOT-VERIFY-001`). Physical IoT integration remains strictly reserved for the final hardware stage.

| Verification Dimension | Result | Key Evidence |
| :--- | :--- | :--- |
| **Frontend Production Build** | **PASSED** | `pnpm build` completed in 704ms; 0 errors, 0 warnings. |
| **TypeScript Compilation** | **PASSED** | `pnpm exec tsc --noEmit` clean (exit code 0). |
| **Localhost & Secret Leak Audit** | **CLEAN** | Grep of `dist/assets/*.js` returned 0 matches for `127.0.0.1`, `localhost`, or secret keys. |
| **Backend Unit & Integration Tests**| **PASSED** | **40 / 40 pytest tests passed** in 11.37s. |
| **Phase 7 Software Test Client** | **PASSED** | **8 / 8 suites passed** (100% success rate). |
| **1D-CNN–BiGRU Inference** | **PASSED** | Model loaded (`model.keras` + `scaler.joblib`); verified Test MAE: 11.75 µg/m³, R²: 0.946. |
| **Database Persistence & Backup** | **PASSED** | SQLite WAL mode active; `PRAGMA integrity_check` = `ok`; online backup created (`102,400 bytes`). |
| **Security & Authorization** | **PASSED** | X-API-Key and X-Admin-Key enforced; rate limiting active; payload size capped at 1MB. |

---

## 2. Verified Fixes and Module Improvements

1. **Detailed API Communication Alert Banners (`src/App.tsx`):**
   - Enhanced both `HomePage` and `DashboardPage` error banners to display `state.error` when backend connectivity is degraded or offline, giving operators exact diagnostics (e.g. unreachable origin or connection refusal) rather than generic static text.
2. **Framework Alignment (`docs/deployment_guide.md`):**
   - Updated artifact configuration table from "PyTorch" to "TensorFlow/Keras" (`model.keras`), aligning documentation with the actual deep learning implementation.
3. **Cross-Platform Test Client (`backend/scripts/phase7_software_test_client.py`):**
   - Configured UTF-8 stdout encoding compatibility for Windows PowerShell (`cp1252`) consoles to ensure test scripts run cleanly without unicode character map exceptions.

---

## 3. Command Execution & Test Results Audit

All assertions and metrics are backed by verified terminal command executions:

### 3.1 Frontend Build & Asset Verification
- **Command:** `pnpm build`
  - **Result:** Exit code 0.
  - **Output:** Built in 704ms:
    - `dist/index.html` (0.93 kB)
    - `dist/assets/index-BkPs2_Dh.css` (39.14 kB)
    - `dist/assets/index-Ty1H9h_M.js` (258.40 kB)
- **Command:** `powershell -Command "Select-String -Path 'dist/assets/*.js' -Pattern '127.0.0.1|localhost|airpurify-dev-key' -Quiet"`
  - **Result:** `False` (0 leaks detected in shipped bundle).
- **Command:** `pnpm exec tsc --noEmit`
  - **Result:** Exit code 0 (clean compilation).

### 3.2 Backend Pytest Suite
- **Command:** `.\.venv\Scripts\python.exe -m pytest -v` (from `backend/`)
  - **Result:** **40 passed, 2 non-blocking warnings in 11.37s**.
  - **Coverage:**
    - `tests/test_readings.py` (20 tests): Sensor ingestion, quality flags, history queries, EPA NowCast, CPCB Indian regulatory AQI thresholds.
    - `tests/test_forecasting.py` (8 tests): Chronological dataset splitting without lookahead leakage, scaler training isolation, sliding window dimensions, model artifact loading, genuine inference, forecast persistence.
    - `tests/test_security.py` (12 tests): Device auth, administrative auth, rate limiting (sliding window), 1MB payload ceiling, production exception sanitization, liveness/readiness probes, online backup validation, CORS preflight.

### 3.3 Phase 7 Comprehensive Software Test Client
- **Command:** `.\.venv\Scripts\python.exe scripts\phase7_software_test_client.py`
  - **Result:** Exit code 0 (100% success).
  - **Verified Lifecycle Steps:**
    1. **System Probes:** `GET /api/health` -> `healthy` (`database: connected`); `GET /api/ready` -> `ready: true` (`forecasting_pipeline: model_ready`, `database: connected`).
    2. **Authentication Guards:** Missing `X-API-Key` -> `401 Unauthorized`; invalid key -> `401 Unauthorized`; non-admin on `/api/forecasts/predict` -> `403 Forbidden`.
    3. **Ingestion & Quality Assessment:** Standard reading accepted (`data_quality_status="valid"`); physically anomalous reading (`PM1.0 = 38.0 > 1.5 * PM2.5 = 12.0`) correctly flagged as `data_quality_status="questionable"`.
    4. **Schema Rejection:** Negative PM2.5 (-5.0) rejected (`422 Unprocessable Entity`); extreme PM2.5 (1500.0) rejected (`422`); missing `location_id` rejected (`422`).
    5. **Alert Triggering & Deduplication:** Warning reading (PM2.5 = 42.0) triggered `HIGH_PM25` warning alert; subsequent critical reading (PM2.5 = 68.0) escalated the existing active alert without creating duplicate rows; Admin `PATCH` updated status to `acknowledged`.
    6. **Historical Querying:** `GET /api/readings/history` verified descending chronological ordering and pagination limits.
    7. **1D-CNN–BiGRU Live Inference:** `POST /api/forecasts/predict` generated genuine 3-hour horizon projections with 95% confidence bounds.
    8. **Database Persistence:** Confirmed 4 records persisted for `SYNTHETIC-PHASE7-NODE-01` in SQLite WAL database with passing integrity check (`[('ok',)]`).

### 3.4 Live Database Backup & Integrity Check
- **Command:** `.\.venv\Scripts\python.exe scripts\backup_db.py`
  - **Result:** Exit code 0.
  - **Snapshot:** `backend/backups/airpurify_backup_20261017_034502.db` (102,400 bytes written).
  - `PRAGMA integrity_check` verified: `[('ok',)]`.

---

## 4. Configuration & Deployment Specifications

### 4.1 Production Environment Variables

#### Backend (`backend/.env`)
```ini
APP_NAME="AirPurify AI"
APP_ENV="production"
APP_VERSION="1.0.0"
DEBUG=false
HOST="127.0.0.1"
PORT=8001
CORS_ORIGINS="https://airpurify.internal,https://campus-air.internal"
DATABASE_URL="sqlite:///./airpurify.db"
AIRPURIFY_API_KEY="<PROD_CRYPTOGRAPHIC_KEY_32_CHARS>"
AIRPURIFY_ADMIN_KEY="<PROD_ADMIN_CRYPTOGRAPHIC_KEY_32_CHARS>"
MAX_PAYLOAD_BYTES=1048576
ENABLE_FORECASTING_MODEL=true
MODEL_NAME="1D-CNN-BiGRU"
MODEL_VERSION="v1.0-hybrid"
ML_ARTIFACTS_DIR="./ml/artifacts"
```

#### Frontend (`.env.production`)
```ini
# When deployed behind NGINX reverse proxy, leave empty to use relative /api routing
VITE_API_BASE_URL=""
# Client keys are NOT embedded in production builds; injected via secure runtime if needed
```

### 4.2 Production Startup & Service Management

#### Backend Systemd Service (`/etc/systemd/system/airpurify-backend.service`)
```ini
[Unit]
Description=AirPurify AI FastAPI Backend Service
After=network.target

[Service]
Type=simple
User=airpurify
WorkingDirectory=/opt/airpurify/backend
EnvironmentFile=/opt/airpurify/backend/.env
ExecStart=/opt/airpurify/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 4 --proxy-headers
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### Database Automated Backup Cron (`crontab -e`)
```cron
# Execute atomic SQLite live backup every night at 02:00 UTC
0 2 * * * /opt/airpurify/backend/.venv/bin/python /opt/airpurify/backend/scripts/backup_db.py >> /var/log/airpurify_backup.log 2>&1
```

---

## 5. Remaining Limitations and Operational Risks

1. **Single-Node SQLite Concurrency Ceiling:**
   - SQLite with WAL mode handles hundreds of concurrent reads and serialized writes efficiently.
   - *Limitation:* Not suitable for multi-region horizontal scaling. If device count exceeds 500 edge nodes reporting every second, follow the documented migration to PostgreSQL in [docs/deployment_guide.md](file:///d:/project/thenam/AeroSenseAIUIDesign-main/AeroSenseAIUIDesign-main/docs/deployment_guide.md).
2. **Historical Training Baseline vs. Local Microclimate:**
   - The 1D-CNN–BiGRU model weights were pre-trained on historical benchmark records (UCI Beijing PM2.5 dataset) to mathematically validate the spatiotemporal architecture.
   - *Limitation:* Atmospheric dynamics vary across geography. Once physical PMS5003 nodes collect 30+ days of campus data, fine-tuning the dense output layer on local observations is recommended.
3. **In-Memory Rate Limiting Scope:**
   - The current sliding-window rate limiter runs in application memory.
   - *Limitation:* Rate limits are per-worker. For multi-server clusters behind a load balancer, backing the rate limiter with Redis is recommended.

---

## 6. Exact Physical IoT Integration Protocol (Final Stage)

When physical hardware integration is authorized:

```
+------------------------------------------------------------------------------------+
| STEP 1: PHYSICAL HARDWARE BENCH WIRING                                             |
|                                                                                    |
|  PMS5003 Pin 1 (VCC)  ------> 5V DC External Supply (120mA peak capacity)          |
|  PMS5003 Pin 2 (GND)  ------> Common Ground (GND) with ESP32                       |
|  PMS5003 Pin 5 (TXD)  ------> ESP32 GPIO 16 (UART2 RX, 3.3V logic)                |
|  PMS5003 Pin 4 (RXD)  ------> ESP32 GPIO 17 (UART2 TX, optional command line)      |
|  PMS5003 Pin 3 (SET)  ------> 3.3V Pull-Up / GPIO 18 (Active measurement mode)     |
+------------------------------------------------------------------------------------+
                                      |
                                      v
+------------------------------------------------------------------------------------+
| STEP 2: FIRMWARE FLASHING & ENCRYPTED NVS PROVISIONING                             |
|                                                                                    |
|  1. Compile ESP32 firmware with 9600 baud 8N1 UART reader and 32-byte frame parser.|
|  2. Provision WiFi SSID, Password, and AIRPURIFY_API_KEY into encrypted NVS.       |
|     (Zero hardcoded credentials in .ino/.cpp source files).                        |
|  3. Configure SNTP time client to sync with pool.ntp.org before telemetry dispatch.|
+------------------------------------------------------------------------------------+
                                      |
                                      v
+------------------------------------------------------------------------------------+
| STEP 3: EDGE TELEMETRY DISPATCH & INGESTION VERIFICATION                          |
|                                                                                    |
|  1. ESP32 aggregates 10-second laser particulate samples.                          |
|  2. Calculates 60-second median: atmospheric PM1.0, PM2.5, PM10.                   |
|  3. Sends HTTP POST to /api/readings with header X-API-Key: <AIRPURIFY_API_KEY>.   |
|  4. Confirms HTTP 201 Created response.                                            |
+------------------------------------------------------------------------------------+
                                      |
                                      v
+------------------------------------------------------------------------------------+
| STEP 4: AIRPURIFY AI DASHBOARD VERIFICATION                                        |
|                                                                                    |
|  1. Observe new device appear in selector: Sensor Node ESP32-XXX (Active).         |
|  2. Verify live PM1.0, PM2.5, PM10 KPI cards update every 15-60 seconds.          |
|  3. Verify historical charts display live time series without gaps.                |
|  4. Confirm 1D-CNN-BiGRU forecasts incorporate live sequence into predictions.    |
+------------------------------------------------------------------------------------+
```

---

## 7. Sign-off

The software foundation for AirPurify AI is **100% complete, verified, and frozen**. Physical IoT hardware integration may commence immediately upon your authorization.

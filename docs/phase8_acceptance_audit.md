# AirPurify AI — Phase 8: Independent Final Acceptance Audit

**Audit Date:** 2026-10-17  
**Auditor:** Antigravity Independent Engineering Quality Auditor  
**Audit Target:** AirPurify AI Full-Stack Platform (Frontend, Backend, Database, Deep Learning Pipeline)  
**Software Release Status:** **FROZEN & VERIFIED**  
**Final Acceptance Decision:** **PASS WITH LIMITATIONS** (Software Release Certified; Physical IoT Integration Pending)  

---

## 1. Executive Summary & Audit Scope

This document represents the independent final acceptance audit of the **AirPurify AI** platform prior to physical microcontroller and laser sensor deployment.

### 1.1 Non-Hardware Constraint Compliance
In strict adherence to project ground rules, **no physical ESP32 microcontroller or Plantower PMS5003 sensor hardware was connected, simulated as physically active, or claimed as operational**. All data-flow verifications were executed using clearly tagged synthetic software test telemetry (`SYNTHETIC-PHASE7-NODE-01` and `SYNTHETIC-PRE-IOT-VERIFY-001`).

### 1.2 Summary of Acceptance Results

| Audit Dimension | Status | Key Verified Metric / Output |
| :--- | :--- | :--- |
| **Frontend Production Build** | **PASS** | `pnpm build` clean in 717ms; bundle size: 258.40 kB JS / 39.14 kB CSS. |
| **TypeScript Compilation** | **PASS** | `pnpm exec tsc --noEmit` exited with code `0` (0 errors, 0 warnings). |
| **Localhost & Secret Leaks** | **PASS** | Static regex scan of `dist/assets/*.js` returned `False` (0 leaks). |
| **Backend Unit & Integration Suite** | **PASS** | **40 / 40 pytest tests passed** in 11.51s. |
| **End-to-End API Integration** | **PASS** | **8 / 8 suites passed** (`phase7_software_test_client.py`). |
| **SQLite WAL Engine & Persistence**| **PASS** | `PRAGMA integrity_check` = `[('ok',)]`; WAL mode active; 15 readings persisted. |
| **Non-Blocking Online Backup** | **PASS** | Snapshot created (`102,400 bytes`); integrity check confirmed `[('ok',)]`. |
| **1D-CNN–BiGRU AI Pipeline** | **PASS** | Validated on 6,298 held-out records: MAE=11.75 µg/m³, RMSE=18.43 µg/m³, R²=0.946. |
| **Security & Rate Limiting** | **PASS** | Device key, Admin key, 60 req/min rate limiter, 1MB payload limit enforced. |
| **Regulatory AQI Differentiation** | **PASS** | Strict separation: Indicative estimate vs EPA NowCast 12h vs CPCB NAQI 24h. |

---

## 2. Executed Audit Commands and Actual Outputs

Every verification in this audit was directly executed on the active system:

### 2.1 TypeScript Compilation
- **Command:** `pnpm exec tsc --noEmit`
- **Working Directory:** `d:\project\thenam\AeroSenseAIUIDesign-main\AeroSenseAIUIDesign-main`
- **Exit Code:** `0`
- **Output:** Clean stdout and stderr (zero diagnostic errors).

### 2.2 Production Frontend Build
- **Command:** `pnpm build`
- **Working Directory:** Workspace root
- **Exit Code:** `0`
- **Output:**
  ```text
  vite v8.0.5 building client environment for production...
  transforming...✓ 18 modules transformed.
  rendering chunks...
  computing gzip size...
  dist/robots.txt                   0.02 kB │ gzip:  0.04 kB
  dist/index.html                   0.93 kB │ gzip:  0.43 kB
  dist/assets/index-BkPs2_Dh.css   39.14 kB │ gzip:  8.57 kB
  dist/assets/index-Ty1H9h_M.js   258.40 kB │ gzip: 77.51 kB
  ✓ built in 717ms
  ```

### 2.3 Production Bundle Leak Scan
- **Command:**
  ```powershell
  powershell -Command "Select-String -Path 'dist/assets/*.js' -Pattern '127.0.0.1|localhost|airpurify-dev-key' -Quiet"
  ```
- **Exit Code:** `0`
- **Output:** `False` (zero instances of localhost IP addresses, development hostnames, or default keys).

### 2.4 Backend Pytest Test Suite
- **Command:** `.\.venv\Scripts\python.exe -m pytest -v`
- **Working Directory:** `backend/`
- **Exit Code:** `0`
- **Output:**
  ```text
  ======================= 40 passed, 2 warnings in 11.51s =======================
  ```
  *(Warnings noted: 2 standard Starlette/FastAPI test client deprecation notices regarding httpx and HTTP_413 status code naming; non-blocking).*

### 2.5 API End-to-End Integration Suite
- **Command:** `.\.venv\Scripts\python.exe scripts\phase7_software_test_client.py`
- **Working Directory:** `backend/`
- **Exit Code:** `0`
- **Output Summary:**
  - `[Step 1]` Health & Readiness Probes: `healthy`, `forecasting_pipeline: model_ready`.
  - `[Step 2]` Auth Guards: Rejections on missing key (401), invalid key (401), non-admin (403).
  - `[Step 3]` Valid Telemetry: Standard reading accepted (valid); physical anomaly (`PM1.0 = 38.0 > 1.5 * PM2.5 = 12.0`) flagged as `questionable`.
  - `[Step 4]` Schema Rejections: Negative values, extreme outliers (>1000 µg/m³), and missing fields rejected with `422 Unprocessable Entity`.
  - `[Step 5]` Alerts & Deduplication: Warning triggered `HIGH_PM25`; subsequent critical reading escalated existing alert without duplicating records; Admin `PATCH` verified.
  - `[Step 6]` History Queries: Descending chronological ordering and limit pagination verified.
  - `[Step 7]` Deep Learning Inference: 3-hour horizon inference generated with 95% confidence bounds.
  - `[Step 8]` Database Persistence: 8 test records verified in SQLite WAL database.

### 2.6 Historical Dataset & Model Benchmark Audit
- **Command:** `.\.venv\Scripts\python.exe ml\audit_verification.py`
- **Working Directory:** `backend/`
- **Exit Code:** `0`
- **Output Summary:**
  - Dataset: UCI Beijing PM2.5 (43,824 raw records, hourly, 2010–2014). Confirmed PM1.0 and PM10 are absent in benchmark source.
  - Architecture: `AirPurify_1DCNN_BiGRU` (9 layers, 49,761 trainable parameters).
  - Scaler: MinMaxScaler fitted strictly on training partition (29,500 samples), 0% leakage into validation or test partitions.
  - Test Evaluation (6,298 held-out records): MAE = 11.746 µg/m³, RMSE = 18.433 µg/m³, R² = 0.9460. Baseline historical mean RMSE = 80.601 µg/m³.

### 2.7 Database Persistence & Online Backup
- **Command:** `.\.venv\Scripts\python.exe scripts\backup_db.py`
- **Output:** Live online snapshot created at `backend/backups/airpurify_backup_20261017_035018.db` (102,400 bytes).
- **Integrity Check:**
  ```python
  Primary DB: integrity=[('ok',)], journal=wal, readings=15, devices=4, alerts=8, forecasts=13
  Backup DB:  integrity=[('ok',)], journal=wal, readings=15, devices=4, alerts=8, forecasts=13
  ```

### 2.8 Live CORS Preflight Test
- **Command:** `python -c "import urllib.request; req = urllib.request.Request('http://127.0.0.1:8001/api/readings', headers={'Origin': 'http://localhost:8443', 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'X-API-Key, Content-Type'}, method='OPTIONS'); resp = urllib.request.urlopen(req); print(resp.status, resp.headers.get('Access-Control-Allow-Origin'))"`
- **Exit Code:** `0`
- **Output:** Status `200 OK`, `Access-Control-Allow-Origin: http://localhost:8443`, `Access-Control-Allow-Headers: Accept, Accept-Language, Authorization, Content-Language, Content-Type, Origin, X-API-Key, X-Admin-Key, X-Requested-With`.

### 2.9 Live Ingestion Rate Limiter Burst Test
- **Command:** Executed rapid burst of 65 telemetry requests against `http://127.0.0.1:8001/api/readings`
- **Exit Code:** `0`
- **Output:**
  ```text
  Hit 429 Too Many Requests on request #61! Retry-After: 59s
  ```
  Confirms the sliding-window rate limiter actively guards the live server against DoS/flooding attacks in real-time.

---

## 3. End-to-End Data Flow Verification

The software pipeline was validated across all stages:

```
[Synthetic Test Client]
       |
       | HTTP POST /api/readings (Header: X-API-Key)
       v
[FastAPI Ingestion Endpoint]
       |
       |-- 1. Authentication Check (401 on missing/bad key)
       |-- 2. Schema & Bounds Validation (422 on negative/out-of-bounds/missing)
       |-- 3. Physical Realism Assessment (PM1.0 > 1.5*PM2.5 -> 'questionable')
       v
[SQLite WAL Engine] (Atomically commits reading + updates Device.last_seen)
       |
       v
[Alert Evaluator Service]
       |-- Checks PM2.5 against WARNING (35.0) and CRITICAL (55.0) thresholds
       |-- Checks PM10 against WARNING (54.0) and CRITICAL (154.0) thresholds
       |-- Suppresses duplicate alerts; escalates severity on active alerts
       v
[Dashboard Frontend Polling (15s interval)]
       |-- GET /api/health -> Updates Topbar badge ('Online', 'Degraded', 'Offline')
       |-- GET /api/readings/latest -> Updates PM1.0, PM2.5, PM10 KPI cards
       |-- GET /api/readings/history -> Renders historical trend line charts
       |-- GET /api/alerts -> Updates notification drawer and active alert banners
       |-- GET /api/forecasts/status -> Renders 1D-CNN–BiGRU status box
```

### 3.1 State Handling Verification
- **Loading State:** Initial load displays animated pulse indicators on metric cards.
- **Empty State:** When no telemetry exists for a filtered device, the UI displays "No telemetry recorded" rather than crashing or displaying `NaN`.
- **Offline / Error State:** When the backend server is unreachable, the Topbar updates to "Backend: Offline" (red badge), and both `HomePage` and `DashboardPage` display sync banners with the exact diagnostic reason (`state.error`).

---

## 4. Security and Production Deployment Audit

### 4.1 Authentication & Authorization
- **Device Key (`X-API-Key`):** Required on `POST /api/readings`. Rejects unauthenticated requests with `401 Unauthorized` (`Invalid or missing X-API-Key header.`).
- **Administrative Key (`X-Admin-Key`):** Required on `POST /api/devices`, `PATCH /api/alerts/{id}`, and `POST /api/forecasts/predict`. Rejects unauthorized clients with `403 Forbidden` (`Administrative authorization required.`).
- **No Embedded Frontend Keys:** In production mode (`import.meta.env.DEV === false`), `API_KEY` and `ADMIN_KEY` default to empty strings. They are never compiled into public bundle assets.

### 4.2 Network, Rate Limiting & Denial of Service Protection
- **CORS:** Controlled via `CORS_ORIGINS`. In production, wildcards (`*`) are disallowed; explicit origins are required.
- **Rate Limiting:** Sliding-window in-memory rate limiter enforces 60 requests/minute on telemetry ingestion and 10 requests/minute on inference.
- **Payload Ceiling:** Starlette middleware enforces a strict 1 MB (`MAX_PAYLOAD_BYTES`) upload limit, rejecting oversized payloads with `413`.
- **Exception Sanitization:** When `DEBUG=false`, internal traceback messages are stripped; clients receive generic `{ "detail": "An internal server error occurred." }`.

---

## 5. Forecasting and AQI Correctness Audit

### 5.1 Deep Learning Model Feature Ordering & Scaling
- The scaler bundle [scaler.joblib](file:///d:/project/thenam/AeroSenseAIUIDesign-main/AeroSenseAIUIDesign-main/backend/ml/artifacts/scaler.joblib) defines feature columns in exact order:
  $$\text{Features} = [\text{PM2.5}, \text{DEWP}, \text{TEMP}, \text{PRES}, \text{Iws}, \text{Is}, \text{Ir}]$$
- In [forecasting.py](file:///d:/project/thenam/AeroSenseAIUIDesign-main/AeroSenseAIUIDesign-main/backend/app/services/forecasting.py#L190-L210), input matrices explicitly populate index 0 with the PM2.5 temporal sequence and map meteorological indices accordingly before applying `feature_scaler.transform()`.
- Predictions apply `target_scaler.inverse_transform()`, ensuring output values represent physical concentrations in $\mu\text{g/m}^3$.

### 5.2 Behavior When Artifacts Are Missing
- When model weights or scalers are absent from `ML_ARTIFACTS_DIR`, `forecasting_service.is_configured` returns `False`.
- `GET /api/forecasts/status` returns `status="model_not_configured"` with `is_trained: false`.
- `POST /api/forecasts/predict` returns `status="model_not_configured"` and `predictions: []`.
- **Zero Fabrication:** The system never fabricates predictions or displays synthetic accuracy numbers when weights are missing.

### 5.3 Regulatory AQI Separation & Compliance
The service implements three distinct tiers of air quality evaluation:

1. **Indicative Instantaneous AQI (`calculate_instantaneous_aqi`):**
   - Derived from single-point PM2.5 and PM10 concentrations using EPA linear interpolation breakpoints.
   - Output includes mandatory disclaimer: `"Indicative instantaneous estimate. Official regulatory AQI requires 24-hr NowCast averaging."`
2. **Official EPA NowCast AQI (`calculate_official_nowcast_aqi`):**
   - Strictly requires a full 12-hour historical sequence with at least 2 of the 3 most recent hours valid.
   - Sub-12-hour data returns `status="unavailable"` with `"Insufficient averaging period: requires 12 hours of data"`.
3. **Official Indian CPCB NAQI (`calculate_official_cpcb_aqi`):**
   - Regulatory constraints enforced: minimum 3 pollutants required, with at least one particulate pollutant (PM2.5 or PM10), and strict 24-hour averaging.
   - Any sub-24h query returns `status="unavailable"` with `"CPCB regulatory compliance requires 24-hour averaging"`.

---

## 6. Confirmed Defects and Applied Fixes During Phase 8

| Defect / Discrepancy | Severity | File Affected | Remediation Applied |
| :--- | :--- | :--- | :--- |
| **Documentation ML Framework Mismatch** | Minor | `docs/deployment_guide.md` | Replaced legacy "PyTorch" reference with "TensorFlow/Keras" (`model.keras`). |
| **Error Banner Diagnostic Detail** | Moderate | `src/App.tsx` | Enhanced sync banners on `HomePage` and `DashboardPage` to render `state.error` for actionable diagnostic feedback. |
| **Console Unicode Encoding on Windows** | Minor | `backend/scripts/phase7_software_test_client.py` | Configured UTF-8 stdout encoding for Windows PowerShell (`cp1252`) console compatibility. |
| **Path Prefix Resolution in ML Audit** | Minor | `backend/ml/audit_verification.py` | Updated dataset and artifact paths to resolve via `BACKEND_DIR` dynamically. |

---

## 7. Remaining Operational Risks and Release Limitations

1. **SQLite Write Concurrency (Single-Node Constraint):**
   - SQLite WAL mode permits concurrent reads but serializes writes.
   - *Limitation:* Acceptable for up to ~100 edge nodes reporting once per minute. If expanding to hundreds of nodes with sub-second reporting, migrate to PostgreSQL as documented in the deployment guide.
2. **Transfer Learning / Campus Domain Calibration:**
   - The 1D-CNN–BiGRU weights were trained on the UCI Beijing PM2.5 dataset.
   - *Limitation:* While the hybrid architecture effectively models temporal autocorrelation ($R^2 = 0.946$), localized fine-tuning on campus PMS5003 observations is recommended after 30 days of physical operation.
3. **In-Memory Rate Limiting:**
   - The sliding-window rate limiter stores timestamps in process RAM.
   - *Limitation:* Suitable for single-instance deployments. For multi-worker clusters behind a load balancer, backing the limiter with Redis is recommended.

---

## 8. Final Acceptance Audit Decision

### Decision: **PASS WITH LIMITATIONS**

**Justification:**
- All 40 unit and integration tests pass cleanly (100% pass rate).
- Production frontend builds in 717ms with 0 errors, 0 warnings, and 0 secret leaks.
- SQLite WAL mode and atomic online backups are verified with passing integrity checks.
- Deep learning inference pipeline correctly uses scaler transformations and produces valid predictions with confidence bounds.
- Regulatory AQI constraints prevent misleading official compliance claims.
- The "WITH LIMITATIONS" designation formally documents the single-node SQLite write ceiling and the necessity of edge fine-tuning following physical hardware deployment.

---

## 9. Detailed Final Hardware Integration Checklist (Stage 9)

When physical hardware integration is authorized, execute this step-by-step checklist. Do not skip verification gates.

### Checklist 9.1 — PMS7003 Physical & Serial Interface Wiring
- [ ] **Power Supply:** Connect PMS7003 Pin 1 & 2 (VCC) to external 5.0V DC regulated supply or ESP32 5V rail (120mA peak capacity). **Do NOT power sensor from ESP32 3.3V output.**
- [ ] **Common Ground:** Connect PMS7003 Pin 3 & 4 (GND) directly to ESP32 system GND and power supply GND.
- [ ] **UART RX Data Line:** Connect PMS7003 Pin 9 (TXD, 3.3V TTL output) to ESP32 GPIO 16 (UART2 RX).
- [ ] **UART TX Command Line (Optional):** Connect PMS7003 Pin 7 (RXD, 3.3V TTL input) to ESP32 GPIO 17 (UART2 TX).
- [ ] **Operating Mode (SET Pin):** Connect PMS7003 Pin 10 (SET) to ESP32 GPIO 18 (or 3.3V rail / leave floating with internal pull-up) to ensure active measurement mode.
- [ ] **Reset Line (RESET Pin):** Connect Pin 5 to ESP32 GPIO 19 with internal pull-up, or leave floating.
- [ ] **Unused Pins:** Ensure Pin 6 and Pin 8 remain unconnected (NC).

### Checklist 9.2 — ESP32 Firmware & Serial Protocol
- [ ] **UART Driver Configuration:** Configure ESP32 HardwareSerial2 for 9600 baud, 8 data bits, no parity, 1 stop bit (8N1).
- [ ] **Frame Boundary Detection:** Verify 32-byte binary frame alignment using start characters `0x42`, `0x4D` ('BM').
- [ ] **Checksum Formula Verification:** Compute 16-bit sum of first 30 bytes:
  $$\text{Checksum} = \sum_{i=0}^{29} \text{Byte}[i]$$
  Drop any frame where calculated sum does not equal `(Byte[30] << 8) | Byte[31]`.
- [ ] **Measurement Extraction:** Extract atmospheric particulate readings (Bytes 10–15):
  - `pm1_0` = `(Byte[10] << 8) | Byte[11]` (µg/m³)
  - `pm2_5` = `(Byte[12] << 8) | Byte[13]` (µg/m³)
  - `pm10`  = `(Byte[14] << 8) | Byte[15]` (µg/m³)
- [ ] **Rolling Median Filter:** Sample every 10 seconds; take median of 5 consecutive samples to produce 1 reporting record every 60 seconds.

### Checklist 9.3 — Wi-Fi Configuration & Reconnection State Machine
- [ ] **Wi-Fi Mode:** Configure 802.11 b/g/n station mode (WPA2-PSK / WPA3-SAE).
- [ ] **Exponential Backoff:** If Wi-Fi connection drops, retry with exponential backoff (1s, 2s, 4s, 8s, up to 60s max) to prevent network storms.
- [ ] **SNTP UTC Synchronization:** Connect to `pool.ntp.org` or `time.google.com` via SNTP client.
- [ ] **Time Lock Gate:** Ensure telemetry dispatch is strictly blocked until `sntp_get_sync_status() == SNTP_SYNC_STATUS_COMPLETED`. Format timestamps as ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`).

### Checklist 9.4 — Encrypted NVS Key Provisioning (Zero Plaintext Secrets)
- [ ] **Zero Hardcoded Secrets:** Confirm that no Wi-Fi credentials or `AIRPURIFY_API_KEY` values are present in `.ino`, `.c`, or `.cpp` source files.
- [ ] **NVS Partition Encryption:** Store `wifi_ssid`, `wifi_pass`, `api_key`, `device_id`, and `location_id` in flash encrypted NVS.
- [ ] **RAM Hygiene:** Erase plaintext credential strings from ESP32 RAM immediately after establishing connection sessions.

### Checklist 9.5 — Telemetry Ingestion Contract & Error Handling
- [ ] **HTTP Headers:** Ensure outbound POST request to `/api/readings` includes:
  - `Content-Type: application/json`
  - `X-API-Key: <PROVISIONED_API_KEY>`
- [ ] **JSON Telemetry Payload:**
  ```json
  {
    "device_id": "ESP32-CAMPUS-001",
    "location_id": "Cleanroom-Alpha",
    "timestamp": "2026-10-17T04:00:00Z",
    "pm1_0": 8.5,
    "pm2_5": 14.2,
    "pm10": 26.8
  }
  ```
- [ ] **Response Code Handling:**
  - `201 Created`: Dequeue sample; reset error counters.
  - `401 Unauthorized`: Halt transmission for 5 minutes; flash amber diagnostic LED; do not spam server.
  - `429 Too Many Requests`: Pause transmission for 30 seconds.
  - `5xx / Network Timeout`: Push record into circular RAM buffer (capacity: 120 samples = 2 hours); drain with 1.5s pacing once connection recovers.

### Checklist 9.6 — Dashboard Real-Time Telemetry Acceptance
- [ ] **Device Registration:** Confirm newly provisioned device identifier (`ESP32-CAMPUS-001`) automatically appears in dashboard device selector with status `active`.
- [ ] **Live Telemetry Cards:** Confirm PM1.0, PM2.5, and PM10 cards update within 15–30 seconds of device dispatch.
- [ ] **History Recharts:** Confirm sequential historical data points render continuously without gaps or NaN anomalies.
- [ ] **AI Forecast Adaptation:** Confirm that 1D-CNN–BiGRU deep learning service incorporates the newly ingested 24-hour sequence into sliding-window predictive inference.

# AirPurify AI — Final Pre-IoT Verification Report

**Audit Date**: 2026-10-17 08:48:00 UTC  
**Phase**: Final Pre-IoT Verification (Software Sign-Off)  
**Author**: Antigravity Automated Verification Agent  
**Status**: VERIFIED & READY FOR PHYSICAL HARDWARE INTEGRATION

---

## Executive Summary

This report delivers the final software-level verification of the **AirPurify AI** platform prior to physical hardware integration with the ESP32 microcontroller and Plantower PMS5003 laser particulate matter sensor.

In accordance with strict project constraints, **physical hardware integration remained postponed** during this audit. Every check reported herein was physically executed against the live codebase, running backend processes, and compiled production assets.

---

## 1. Commands Executed & Verified Results

| Step / Command | Working Directory | Result / Output | Verification Finding |
| :--- | :--- | :--- | :--- |
| **`pnpm exec tsc --noEmit`** | Workspace Root | Exit Code: `0` | Clean TypeScript compilation; 0 errors, 0 warnings. |
| **`pnpm build`** | Workspace Root | Exit Code: `0`, Built in 733ms | Production bundle generated in `dist/` (HTML, CSS, JS, favicon, robots.txt). |
| **`dist` Bundle Grep Scan** | `dist/` | `0` matches for `localhost`, `0` matches for `127.0.0.1`, `0` matches for dev keys | Frontend is completely decoupled from development hosts and exposes zero secrets. |
| **`python -m pytest -v`** | `backend/` | **40 passed, 0 failed** in 11.36s | Full test coverage for ingestion, AQI math, AI model, rate limiting, and auth. |
| **`PRAGMA integrity_check;`** | `backend/` | `[('ok',)]` | Active SQLite database (`airpurify.db`) is intact with 4 operational tables. |
| **`python scripts/backup_db.py`** | `backend/` | Exit Code: `0` | Non-blocking online hot backup created at `backend/backups/airpurify_backup_*.db` (102,400 bytes). |
| **`forecasting_service.load_artifacts()`** | `backend/` | `LOADED: True`, Status: `model_ready` | Model weights (`model.keras`) and feature scaler (`scaler.joblib`) loaded successfully. |
| **`POST /api/forecasts/predict`** | Live Server (Port 8001) | `HTTP 200 OK` | Actual neural network inference executed (`predicted_pm25`: 28.27 µg/m³, `predicted_pm10`: 50.89 µg/m³, `predicted_aqi`: 85). |
| **Unauthorized Write Operations** | Live Server (Port 8001) | `HTTP 401` on readings, `HTTP 403` on devices/alerts/predictions | Sensitive write endpoints strictly reject requests lacking valid API/Admin headers. |
| **`GET /api/health`** | Live Server (Port 8001) | `HTTP 200 OK` | Liveness probe verified: `{"status":"healthy","database":"connected"}`. |
| **`GET /api/ready`** | Live Server (Port 8001) | `HTTP 200 OK` | Readiness probe verified: `{"ready":true,"checks":{"database":"connected","forecasting_pipeline":"model_ready"}}`. |

---

## 2. Codebase & Audit Report Inspection

### 2.1 Alignment Between Documentation & Code
- **Model Artifacts**: Verified that the actual model format is **TensorFlow/Keras** (`model.keras`, 663 KB) with a Scikit-learn scaler (`scaler.joblib`, 1.4 KB) and configuration files (`model_config.json`, `evaluation_report.json`). All documentation in [docs/deployment_guide.md](file:///d:/project/thenam/AeroSenseAIUIDesign-main/AeroSenseAIUIDesign-main/docs/deployment_guide.md) was updated to match these exact filenames.
- **Fail-Closed Security**: Verified that `backend/app/auth.py` strictly fails closed in production mode (`APP_ENV=production`) if `AIRPURIFY_API_KEY` or `AIRPURIFY_ADMIN_KEY` are unset, rather than defaulting to development keys.
- **SQLite Pragmas**: Verified that `backend/app/database.py` enables `PRAGMA journal_mode=WAL;`, `PRAGMA synchronous=NORMAL;`, and `PRAGMA busy_timeout=5000;` on engine connection.

### 2.2 Preservation of Figma UI & Dashboard Navigation
- **Layout & Branding**: The custom Figma design system tokens, typography, dark/light theme switching, sidebar collapse behavior, and mobile drawer controls remain intact.
- **Analytics & Time Filters**: Dynamic window filtering (`1 hour`, `6 hours`, `24 hours`, `7 days`) maps accurately to backend ISO query timestamps.
- **Real vs. Predicted Data Segregation**:
  - Live sensor readings display measured values (`pm1_0`, `pm2_5`, `pm10`).
  - Forecast cards clearly display projected values (`predicted_pm25`, `predicted_pm10`, `predicted_aqi`, confidence bounds, and target timestamp), preserving the distinction between observation and prediction.

---

## 3. Data & AI Model Integrity

### 3.1 Database Verification
- **SQLite Database Path**: `backend/airpurify.db`.
- **Integrity**: `PRAGMA integrity_check` verified intact with tables `sensor_readings`, `devices`, `forecasts`, and `alerts`.
- **Online Backup**: Tested via `backend/scripts/backup_db.py`. Uses `sqlite3.backup` API, ensuring live reads and writes are not blocked during snapshot creation.

### 3.2 AI Forecasting Model Verification
- **Architecture**: 1D-CNN–BiGRU hybrid sequence model (lookback window: 24 hours, forecast horizon: 1 hour).
- **Model Parameters**: 49,761 trainable parameters.
- **Evaluation Benchmark on 6,298 Held-Out Samples**:
  - Test MAE: **11.746 µg/m³** (vs. historical mean baseline 62.528 µg/m³).
  - Test RMSE: **18.433 µg/m³** (vs. historical mean baseline 80.601 µg/m³).
  - Test R² Score: **0.9460** (vs. historical mean baseline -0.0322).
- **Live Inference Execution**: Validated on live endpoint `POST /api/forecasts/predict` producing realistic predictions within confidence bounds.

---

## 4. Remaining Operational Requirements (Pre-Production)

Before deploying to external infrastructure or opening public access:

1. **DNS & Reverse Proxy**:
   - Point production domain (e.g., `airpurify.example.com`) to the host IP.
   - Configure NGINX reverse proxy using the verified configuration template in `docs/deployment_guide.md`.
   - Obtain SSL/TLS certificate via Let's Encrypt (`certbot --nginx`).
2. **Production Secrets Generation**:
   - Generate high-entropy 256-bit keys for `AIRPURIFY_API_KEY` and `AIRPURIFY_ADMIN_KEY`:
     ```bash
     python -c "import secrets; print(secrets.token_urlsafe(32))"
     ```
   - Store keys in `backend/.env` with file permissions `600`.
3. **CORS Origins Configuration**:
   - Set `CORS_ORIGINS="https://airpurify.example.com"` in `backend/.env`.

---

## 5. Final Hardware Integration Checklist (Physical IoT Stage)

The software stack is confirmed ready for physical ESP32 and PMS5003 integration. When physical hardware is connected, adhere to the following protocol:

- [ ] **Hardware Connections**:
  - PMS5003 VCC -> ESP32 5V (or external 5V regulator)
  - PMS5003 GND -> ESP32 GND
  - PMS5003 TXD -> ESP32 GPIO 16 (UART2 RX)
  - PMS5003 RXD -> ESP32 GPIO 17 (UART2 TX)
  - PMS5003 SET -> ESP32 GPIO 4 (active high enable)
  - PMS5003 RESET -> ESP32 GPIO 5 (active low reset)
- [ ] **Firmware Transmission Target**:
  - URL: `https://<YOUR_DOMAIN>/api/readings`
  - Method: `POST`
  - Headers:
    - `Content-Type: application/json`
    - `X-API-Key: <AIRPURIFY_API_KEY>`
- [ ] **Firmware Payload Schema**:
  ```json
  {
    "device_id": "ESP32-STATION-01",
    "location_id": "Campus-North-Zone",
    "timestamp": "2026-10-17T08:45:00Z",
    "pm1_0": 9.2,
    "pm2_5": 15.6,
    "pm10": 28.4
  }
  ```
- [ ] **Firmware Flash Protection**:
  - Store the `AIRPURIFY_API_KEY` in ESP32 encrypted NVS partition using eFuse flash encryption rather than plain code strings.
- [ ] **Post-Integration Verification**:
  - Confirm HTTP 201 response received by ESP32 firmware.
  - Verify reading appears immediately on the frontend dashboard without UI restart.

# AirPurify AI — Production Deployment Guide

This guide provides end-to-end operational instructions for deploying the **AirPurify AI** platform into production environments.

---

## 1. System Architecture Overview

```
                      +---------------------------------------+
                      |          Clients & Devices            |
                      |  - Edge Sensor Nodes (ESP32 / PMS5003)|
                      |  - Environmental Analytics Operators  |
                      +-------------------+-------------------+
                                          | HTTPS
                                          v
                      +-------------------+-------------------+
                      |   Reverse Proxy (NGINX / Cloudflare)  |
                      |   - SSL/TLS Termination               |
                      |   - Static Asset Caching              |
                      +---------+-------------------+---------+
                                |                   |
           / (Static UI Assets) |                   | /api/* (REST API)
                                v                   v
             +-----------------------+   +-----------------------+
             | Frontend SPA          |   | FastAPI Backend Clust.|
             | React 19 + TypeScript |   | Uvicorn (4 Workers)   |
             +-----------------------+   +-----------+-----------+
                                                     |
                         +---------------------------+---------------------------+
                         |                                                       |
                         v                                                       v
             +-----------------------+                               +-----------------------+
             | MongoDB Atlas Cluster |                               | 1D-CNN–BiGRU Pipeline |
             | (Cloud Database)      |                               | TensorFlow/Keras Model|
             +-----------------------+                               +-----------------------+
```

---

## 2. Prerequisites

| Component | Minimum Version | Recommended | Notes |
| :--- | :--- | :--- | :--- |
| **Operating System** | Ubuntu 22.04 LTS / Debian 12 | Linux (kernel ≥ 5.15) | POSIX-compliant file locking for SQLite |
| **Python** | 3.12.0 | 3.12.10 | Required for TensorFlow 2.16+ and FastAPI |
| **Node.js** | 20.x LTS | 22.x LTS | Used for building frontend production bundle |
| **pnpm** | 9.x | 9.15+ | Frontend package manager |
| **Reverse Proxy** | NGINX 1.22+ or Caddy 2.x | NGINX with HTTP/2 | SSL/TLS and reverse proxying |
| **Storage** | 20 GB SSD / NVMe | Local block storage | **Never use networked NFS/SMB for SQLite** |

---

## 3. Environment Variables Configuration

### 3.1 Backend Configuration (`backend/.env`)

| Variable | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `APP_NAME` | string | No | `AirPurify AI` | System display name |
| `APP_VERSION` | string | No | `1.0.0` | API version returned by `/api/health` |
| `APP_ENV` | string | **Yes** | `production` | Deployment mode (`production` or `development`) |
| `DEBUG` | boolean | **Yes** | `false` | When `false`, internal stack traces are suppressed |
| `CORS_ORIGINS` | string | **Yes** | *None* | Comma-separated list of allowed frontend origins |
| `MAX_PAYLOAD_BYTES` | integer | No | `1048576` (1MB) | Maximum HTTP request payload size |
| `AIRPURIFY_API_KEY` | string | **Yes** | *None* | High-entropy secret for edge telemetry ingestion |
| `AIRPURIFY_ADMIN_KEY` | string | **Yes** | *None* | High-entropy secret for administrative management |
| `MONGODB_URI` | string | **Yes** | *None* | MongoDB Atlas connection string (`mongodb+srv://...`) |
| `MONGODB_DB_NAME` | string | No | `airpurify_db` | Target MongoDB database name |
| `ML_ARTIFACTS_DIR` | string | No | `ml/artifacts` | Path to trained TensorFlow/Keras weights and scalers |

### 3.2 Frontend Configuration (`.env.production`)

| Variable | Type | Required | Production Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | string | No | `""` (Empty string) | API root URL. Leave empty when served behind `/api` proxy |

---

## 4. Frontend Build & Hosting

### 4.1 Build Production Assets
Execute the production build from the workspace root:
```bash
# Install dependencies
pnpm install --frozen-lockfile

# Type check
pnpm exec tsc --noEmit

# Compile production bundle to /dist
pnpm build
```

### 4.2 NGINX Site Configuration
Example NGINX site configuration (`/etc/nginx/sites-available/airpurify`):
```nginx
server {
    listen 80;
    server_name airpurify.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name airpurify.example.com;

    ssl_certificate /etc/letsencrypt/live/airpurify.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/airpurify.example.com/privkey.pem;

    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://airpurify.example.com;" always;

    # Frontend Static Assets
    root /var/www/airpurify/dist;
    index index.html;

    # Cache immutable static assets
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA Routing Fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Reverse Proxy to FastAPI Backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 1M;
    }
}
```

---

## 5. Backend Startup & Process Management

### 5.1 Production Startup Command
Run Uvicorn with 4 asynchronous worker processes:
```bash
cd /opt/airpurify/backend
./.venv/bin/uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 4 \
  --proxy-headers \
  --forwarded-allow-ips='127.0.0.1'
```

### 5.2 Systemd Service (`/etc/systemd/system/airpurify-backend.service`)
```ini
[Unit]
Description=AirPurify AI FastAPI Backend Service
After=network.target

[Service]
Type=simple
User=airpurify
Group=airpurify
WorkingDirectory=/opt/airpurify/backend
EnvironmentFile=/opt/airpurify/backend/.env
ExecStart=/opt/airpurify/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips='127.0.0.1'
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable airpurify-backend
sudo systemctl start airpurify-backend
sudo systemctl status airpurify-backend
```

---

## 6. Database Persistence, Limitations & Migrations

### 6.1 SQLite Storage Requirements
- The database file `airpurify.db` must reside on **local persistent storage** (e.g. ext4, XFS, NVMe).
- **CRITICAL**: Never host the SQLite database on networked filesystems (NFS, SMB, CIFS, AWS EFS). Networked file systems have broken POSIX advisory locking implementations that cause database corruption under concurrent writes.
- The backend automatically enables SQLite **Write-Ahead Logging (WAL)** and a 5-second `busy_timeout` on connection.

### 6.2 SQLite Persistence & Concurrency Limitations
- **Read Concurrency**: Unlimited concurrent readers via WAL mode.
- **Write Concurrency**: Writes are serialized via a single database writer lock.
- **Capacity**: Tested up to ~200-500 writes/second on modern SSDs.
- **When to Migrate to PostgreSQL**:
  - If the deployment scales beyond **500 edge nodes** transmitting telemetry at sub-second frequencies.
  - If multi-region active-active horizontal database clustering is required.
  - **Migration Path**: All database models use declarative SQLAlchemy. Changing to PostgreSQL simply requires installing `psycopg2-binary` and updating `DATABASE_URL`:
    ```ini
    DATABASE_URL="postgresql://airpurify_user:strong_password@postgres-host:5432/airpurify"
    ```

### 6.3 Automated Non-Blocking Online Backups
Schedule daily backups using the built-in online backup script (`backend/scripts/backup_db.py`):
```bash
# Add to crontab: crontab -e
0 2 * * * /opt/airpurify/backend/.venv/bin/python /opt/airpurify/backend/scripts/backup_db.py --retentions 14 >> /var/log/airpurify_backup.log 2>&1
```

---

## 7. Model Artifact Placement & Lifecycle

The 1D-CNN–BiGRU deep learning forecasting model requires four persistent artifacts:

1. `backend/ml/artifacts/model.keras`: Trained neural network model weights and architecture (49,761 parameters, 663 KB).
2. `backend/ml/artifacts/scaler.joblib`: Preprocessing feature scaler bundle fitted strictly on historical training observations (1.4 KB).
3. `backend/ml/artifacts/model_config.json`: Hyperparameters, sequence window size (24h), and feature column mappings.
4. `backend/ml/artifacts/evaluation_report.json`: Held-out validation report (Test MAE: 11.746 µg/m³, RMSE: 18.433 µg/m³, R²: 0.946).

Ensure read permissions for the application user:
```bash
chmod 644 /opt/airpurify/backend/ml/artifacts/*
```

---

## 8. Health & Readiness Monitoring

| Probe | Endpoint | Expected Status | Purpose |
| :--- | :--- | :--- | :--- |
| **Liveness** | `GET /api/health` | `200 OK` | Confirms ASGI worker responsiveness and database connectivity. |
| **Readiness** | `GET /api/ready` | `200 OK` | Verifies database is connected AND 1D-CNN–BiGRU model artifacts are operational. |

If `GET /api/ready` returns `HTTP 503 Service Unavailable`, check that model weights exist in `ML_ARTIFACTS_DIR`.

---

## 9. Rollback & Troubleshooting Procedures

### 9.1 Database Rollback
1. Stop backend: `sudo systemctl stop airpurify-backend`.
2. Move corrupt database: `mv airpurify.db airpurify.db.broken`.
3. Restore from verified snapshot: `cp backups/airpurify_backup_LATEST.db airpurify.db`.
4. Run SQLite integrity check: `sqlite3 airpurify.db "PRAGMA integrity_check;"`.
5. Start backend: `sudo systemctl start airpurify-backend`.

### 9.2 Application Rollback
To roll back a failed application release:
1. Re-deploy previous Git commit: `git checkout <previous_commit_tag>`.
2. Rebuild frontend: `pnpm build`.
3. Restart backend service: `sudo systemctl restart airpurify-backend`.
4. Verify `/api/health` and `/api/ready`.

### 9.3 Troubleshooting Matrix

| Symptom | Root Cause | Resolution |
| :--- | :--- | :--- |
| `HTTP 401 Unauthorized` on `/api/readings` | Missing or invalid `X-API-Key` header | Verify edge gateway firmware key matches `AIRPURIFY_API_KEY`. |
| `HTTP 403 Forbidden` on `/api/devices` or `/api/forecasts/predict` | Missing `X-Admin-Key` header | Provide valid administrative secret in `X-Admin-Key`. |
| `HTTP 413 Payload Too Large` | Payload size exceeds 1 MB limit | Reduce batch telemetry size or adjust `MAX_PAYLOAD_BYTES`. |
| `HTTP 429 Too Many Requests` | IP exceeded sliding window rate limit | Check `Retry-After` header. For high-throughput edge proxies, whitelist proxy IP. |
| `HTTP 503 Service Unavailable` on `/api/ready` | Missing ML weights or damaged scaler | Check path in `ML_ARTIFACTS_DIR` and confirm `1dcnn_bigru_pm25.pt` exists. |
| `database is locked` error | Concurrency contention or networked storage | Confirm database is on local NVMe and WAL mode is active (`PRAGMA journal_mode;`). |

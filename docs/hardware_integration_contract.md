# AirPurify AI — Hardware Integration Contract

**Document Version:** 1.0.0 (Pre-IoT Software Freeze)  
**Status:** Approved for Hardware Integration (Software Ready)  
**Target Hardware:** Espressif ESP32 (ESP-WROOM-32 / ESP32-S3) + Plantower PMS7003 Laser Particulate Sensor  
**Backend API Version:** v1.0.0 (FastAPI 0.115 / PyMongo 4.19 / MongoDB Atlas)  

---

## 1. System Overview and Integration Boundary

This contract governs the physical and communication interface between the edge telemetry node (ESP32 microcontroller with Plantower PMS7003 particulate sensor) and the AirPurify AI ingestion backend (`POST /api/readings`).

```
+-----------------------------------------------------------------------------------+
| PHYSICAL SENSOR NODE (Postponed until hardware stage)                            |
|                                                                                   |
|  +--------------------+         UART (9600 8N1)          +---------------------+  |
|  | Plantower PMS7003  | -------------------------------> |   Espressif ESP32   |  |
|  | Particulate Sensor | (32-byte binary frames)          |   Microcontroller   |  |
|  +--------------------+                                  +----------+----------+  |
+---------------------------------------------------------------------|-------------+
                                                                      |
                                                      HTTPS / Wi-Fi   | X-API-Key
                                                      (Encrypted NVS) | JSON Telemetry
                                                      v
+-----------------------------------------------------------------------------------+
| AIRPURIFY AI BACKEND (Fully Verified & Frozen)                                    |
|                                                                                   |
|  +---------------------+         PyMongo          +----------------------------+  |
|  | POST /api/readings  | -----------------------> | MongoDB Atlas (Cloud DB)   |  |
|  +----------+----------+                          +--------------+-------------+  |
|             |                                                    |                |
|             v                                                    v                |
|  +---------------------+                          +----------------------------+  |
|  | Alert Evaluator     |                          | 1D-CNN-BiGRU Forecasting   |  |
|  | (PM2.5/PM10 Alerts) |                          | (v1.0-hybrid Inference)    |  |
|  +---------------------+                          +----------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 2. PMS7003 Sensor Hardware Interface

### 2.1 Physical Pinout and Electrical Connections (10-Pin 1.27mm Header)

The PMS7003 features a 10-pin (2x5 row, 1.27mm pitch) interface:

| PMS7003 Pin | Signal Name | ESP32 Connection | Description / Electrical Constraints |
| :--- | :--- | :--- | :--- |
| **Pin 1 & 2** | VCC | 5V Rail (External / USB) | Sensor laser and fan supply: 5.0V ± 0.1V, active current ≤ 100mA, peak ~120mA. **Do NOT power from ESP32 3.3V pin.** |
| **Pin 3 & 4** | GND | Common GND | System reference ground common to ESP32 and power supply. |
| **Pin 5** | RESET | GPIO 19 (or Floating) | Hardware reset: `LOW` (<0.8V) for > 100ms resets sensor microcontroller. Default: floating (internal pull-up). |
| **Pin 6** | NC | Not Connected | Unused / Reserved. Keep isolated. |
| **Pin 7** | RXD | GPIO 17 (ESP32 UART2 TX) | Command interface (3.3V TTL). Used for passive mode query commands. |
| **Pin 8** | NC | Not Connected | Unused / Reserved. Keep isolated. |
| **Pin 9** | TXD | GPIO 16 (ESP32 UART2 RX) | Serial data output (3.3V TTL). Directly compatible with ESP32 3.3V logic. |
| **Pin 10** | SET | GPIO 18 (or 3.3V Pull-Up) | Operating mode: `HIGH` (3.3V or floating with internal pull-up) = Active sampling; `LOW` (0V) = Low-power standby. |

### 2.2 Serial Protocol Configuration

- **Baud Rate:** 9600 bps
- **Data Bits:** 8
- **Parity:** None
- **Stop Bits:** 1 (8N1)
- **Flow Control:** None

### 2.3 Binary Frame Format (32 Bytes Active Transmission)

The PMS7003 continuously outputs 32-byte frames every 200–800 ms in active mode:

| Byte Index | Field Description | Value / Formula | Notes |
| :--- | :--- | :--- | :--- |
| **0** | Start Character 1 | `0x42` ('B') | Frame magic byte 1 |
| **1** | Start Character 2 | `0x4D` ('M') | Frame magic byte 2 |
| **2..3** | Frame Length | `0x001C` (28 bytes) | High byte, Low byte |
| **4..5** | PM1.0 Standard (CF=1) | `(Byte[4] << 8) \| Byte[5]` | Standard particle calibration |
| **6..7** | PM2.5 Standard (CF=1) | `(Byte[6] << 8) \| Byte[7]` | Standard particle calibration |
| **8..9** | PM10 Standard (CF=1) | `(Byte[8] << 8) \| Byte[9]` | Standard particle calibration |
| **10..11** | **PM1.0 Atmospheric** | `(Byte[10] << 8) \| Byte[11]` | **Transmitted to API as `pm1_0`** (µg/m³) |
| **12..13** | **PM2.5 Atmospheric** | `(Byte[12] << 8) \| Byte[13]` | **Transmitted to API as `pm2_5`** (µg/m³) |
| **14..15** | **PM10 Atmospheric** | `(Byte[14] << 8) \| Byte[15]` | **Transmitted to API as `pm10`** (µg/m³) |
| **16..27** | Particle Counts (0.3µm to 10µm) | 6 × 16-bit counts per 0.1L | Diagnostic particle binning |
| **28** | Firmware Version | Integer byte | Diagnostic |
| **29** | Error / Status Code | Integer byte | 0 = normal |
| **30..31** | **Frame Checksum** | `(Byte[30] << 8) \| Byte[31]` | Expected 16-bit sum |

### 2.4 Frame Verification Rule
The firmware must compute the 16-bit sum of the first 30 bytes:
$$\text{Calculated Checksum} = \sum_{i=0}^{29} \text{Byte}[i]$$
If $\text{Calculated Checksum} \neq (\text{Byte}[30] \ll 8) \mid \text{Byte}[31]$, the frame **must be discarded immediately** without parsing.

---

## 3. ESP32 Firmware Configuration & Networking

### 3.1 Dual-Core Task Allocation
- **Core 0 (Network & Ingestion Task):** Wi-Fi connection supervisor, SNTP time synchronization, HTTP client, TLS session management, circular RAM queue dispatcher.
- **Core 1 (Sensor Telemetry Task):** FreeRTOS UART ring buffer reader, 32-byte frame parsing, 10-sample rolling median filter, health monitoring.

### 3.2 Wi-Fi & Reconnection Strategy
- **Supported Standards:** 802.11 b/g/n (2.4 GHz channel 1–13).
- **Security:** WPA2-Personal (AES) or WPA3-SAE.
- **Reconnection Algorithm:** Exponential backoff on disconnect:
  - Initial delay: 1.0 second
  - Multiplier: 2.0x
  - Maximum retry delay: 60 seconds
  - Wi-Fi power save mode: `WIFI_PS_MIN_MODEM` for optimal latency without packet dropping.

### 3.3 SNTP Time Synchronization
- Edge telemetry records require UTC timestamps.
- NTP pool servers: `pool.ntp.org`, `time.cloudflare.com`, `time.google.com`.
- Telemetry dispatch is **blocked** until SNTP reports `SNTP_SYNC_STATUS_COMPLETED`.
- Timestamp format: ISO 8601 extended UTC (`YYYY-MM-DDTHH:MM:SS.sssZ`).

---

## 4. Secure Key Provisioning via Encrypted NVS

> [!IMPORTANT]
> **Zero Plaintext Secrets Rule:** Under no circumstances should Wi-Fi credentials or the `AIRPURIFY_API_KEY` be hardcoded into the firmware `.ino` / `.c` / `.cpp` source files or committed to Git.

### 4.1 Encrypted NVS Architecture
- **Partition:** `nvs_keys` partition in flash memory, encrypted with hardware AES-256 eFuse key.
- **Keys stored in NVS:**
  - `wifi_ssid`: Wi-Fi network SSID (string, max 32 chars)
  - `wifi_pass`: Wi-Fi network password (string, max 64 chars)
  - `api_key`: `AIRPURIFY_API_KEY` shared secret (string, 32–64 chars)
  - `device_id`: Unique hardware identifier (e.g., `ESP32-LAB-001`)
  - `location_id`: Monitored site name (e.g., `Engineering Block`)
  - `api_host`: Ingestion server URL (e.g., `https://airpurify.internal/api/readings`)

### 4.2 Provisioning Workflow
1. **Factory Bench Provisioning:**
   Generate NVS binary using `nvs_partition_gen.py` and flash to device partition:
   ```bash
   python $IDF_PATH/components/nvs_flash/nvs_partition_generator/nvs_partition_gen.py \
       generate factory_config.csv nvs_partition.bin 0x4000
   esptool.py --port COM3 write_flash 0x9000 nvs_partition.bin
   ```
2. **Field Provisioning (Captive Portal / BLE):**
   When unconfigured, the ESP32 boots in SoftAP mode (`AirPurify-Setup-XXXX`), hosting a WPA2-protected configuration web page over TLS to accept credentials, saves them to NVS, and reboots in station mode.

---

## 5. Telemetry Ingestion Contract (`POST /api/readings`)

### 5.1 Endpoint Specification
- **Method:** `POST`
- **Path:** `/api/readings`
- **Content-Type:** `application/json`
- **Required Headers:**
  - `X-API-Key: <AIRPURIFY_API_KEY>`
  - `Content-Type: application/json`

### 5.2 Request Payload Schema (Pydantic `ReadingCreate`)

```json
{
  "device_id": "ESP32-001",
  "location_id": "Engineering Block",
  "timestamp": "2026-10-17T03:30:00.000Z",
  "pm1_0": 8.5,
  "pm2_5": 14.2,
  "pm10": 26.8
}
```

#### Field Specifications

| Field | Type | Required | Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| `device_id` | string | **Yes** | Min length 1, Max length 64 | Unique hardware device identifier |
| `location_id` | string | **Yes** | Min length 1, Max length 64 | Monitored location / room identifier |
| `timestamp` | string (ISO 8601) | **Yes** | Valid UTC timestamp format | Sensor acquisition time (synchronized via NTP) |
| `pm1_0` | float | No (Optional) | `0.0 <= pm1_0 <= 1000.0` | Atmospheric PM1.0 concentration in µg/m³ |
| `pm2_5` | float | **Yes** | `0.0 <= pm2_5 <= 1000.0` | Atmospheric PM2.5 concentration in µg/m³ |
| `pm10` | float | **Yes** | `0.0 <= pm10 <= 2000.0` | Atmospheric PM10 concentration in µg/m³ |

### 5.3 Backend Response Codes

| Status Code | Description | Firmware Action |
| :--- | :--- | :--- |
| **`201 Created`** | Telemetry successfully ingested, device updated, alerts evaluated. | Dequeue sample from local RAM buffer; continue normal operation. |
| **`400 Bad Request`** | Data out of range or malformed JSON. | Discard invalid sample; log error over UART; do not retry same payload. |
| **`401 Unauthorized`** | Missing or invalid `X-API-Key`. | Pause transmission for 5 minutes; flash warning LED; avoid spamming auth failures. |
| **`413 Content Too Large`** | Payload exceeds 1 MB limit. | Discard payload; firmware should only send single JSON objects (~180 bytes). |
| **`422 Unprocessable`** | Missing required fields or schema violation. | Discard sample; inspect field names. |
| **`429 Too Many Requests`** | Client IP exceeded rate limit (60 req/min). | Back off for 30 seconds before retrying. |
| **`5xx / Timeout`** | Server error or network drop. | Retain sample in circular RAM buffer; retry with exponential backoff. |

---

## 6. Rate Limiting, Retries, and Offline Buffering

### 6.1 Transmission Cadence
- **Sampling Interval:** PMS7003 sampled every 10 seconds.
- **Reporting Interval:** Firmware calculates the median of five 10-second samples and dispatches 1 telemetry payload every **60 seconds**.
- **Rate Limit Margin:** Ingestion server limits clients to 60 requests/minute. At 1 request/minute, normal operation consumes < 2% of the rate limit budget.

### 6.2 Offline Buffering & Duplicate Prevention
- **Local RAM Buffer:** The ESP32 maintains a circular buffer of up to 120 readings (~2 hours of data during network outages).
- **Draining Strategy:** Once Wi-Fi reconnects, buffered readings are sent sequentially with a minimum 1.5-second interval between requests to avoid triggering the rate limiter.
- **Server-Side Idempotency:** The database stores `timestamp` (sensor acquisition time) and `received_at` (server arrival time). Re-transmissions retain their original `timestamp`.

---

## 7. Alert Trigger Logic (Automated on Ingestion)

When a reading is accepted by `/api/readings`, the backend immediately evaluates threshold rules:

| Condition | Alert Type | Severity | Default Trigger Threshold |
| :--- | :--- | :--- | :--- |
| `pm2_5 >= 55.0 µg/m³` | `HIGH_PM25` | **critical** | Unhealthy air quality |
| `35.0 <= pm2_5 < 55.0 µg/m³` | `HIGH_PM25` | **warning** | Moderate air quality threshold |
| `pm10 >= 154.0 µg/m³` | `HIGH_PM10` | **critical** | Severe coarse dust |
| `54.0 <= pm10 < 154.0 µg/m³` | `HIGH_PM10` | **warning** | Elevated coarse dust |
| `last_seen > 15 min ago` | `DEVICE_OFFLINE` | **warning** | Heartbeat watchdog |

*Duplicate Alert Suppression:* If an active unacknowledged alert of the same type already exists for the device, the alert evaluator updates severity and timestamp rather than generating redundant records.

---

## 8. Physical Integration Checklist (To be executed in Hardware Stage)

When physical hardware integration is authorized:
1. [ ] Connect PMS7003 Pin 1 & 2 to 5V power supply, Pin 3 & 4 to GND, Pin 9 (TXD) to ESP32 GPIO 16 (RX2), Pin 7 (RXD) to ESP32 GPIO 17 (TX2).
2. [ ] Flash ESP32 firmware configured for 9600 baud UART on GPIO 16/17.
3. [ ] Provision Wi-Fi credentials and `AIRPURIFY_API_KEY` into encrypted NVS using factory tool or BLE portal.
4. [ ] Power on system and monitor ESP32 serial console (115200 baud) for:
   - Wi-Fi association and DHCP IP assignment.
   - SNTP time synchronization confirmed.
   - Valid PMS7003 32-byte frames with passing checksum.
   - HTTP 201 Created response from `/api/readings`.
5. [ ] Open AirPurify AI dashboard and confirm:
   - Device appears in device selector with status `active`.
   - Real-time PM1.0, PM2.5, PM10 metrics update.
   - History charts render consecutive incoming points.
   - 1D-CNN-BiGRU forecasts incorporate the live sequence into sliding-window inference.

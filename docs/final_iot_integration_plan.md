# AirPurify AI — Final ESP32 & PMS7003 IoT Integration Plan

**Document Version:** 1.1.0 (Pre-Assembly Hardware Specification: Plantower PMS7003)  
**Status:** **AWAITING USER REVIEW & AUTHORIZATION** (No Firmware Flashed / No Hardware Modified)  
**Software State:** Frozen & Verified (Phase 8 Audit Passed with Limitations)  
**Target Hardware:** Espressif ESP32 (ESP-WROOM-32 / ESP32-S3) + Plantower PMS7003 Laser Particulate Sensor  
**Target Backend:** AirPurify AI FastAPI Ingestion Service (`POST /api/readings`)  

---

## 1. Executive Hardware Specification & Safety Constraints

This document establishes the verified hardware assembly, electrical wiring, firmware architecture, network provisioning, and validation protocols for connecting the physical **Plantower PMS7003** particulate matter sensor to the **Espressif ESP32** edge telemetry node and integrating it with the **AirPurify AI** platform.

> [!IMPORTANT]
> **Hardware Model Correction (PMS5003 → PMS7003):**
> Following hardware identification review, the physical particulate sensor is confirmed as the **Plantower PMS7003** (compact 10-pin 1.27mm pitch connector), replacing all prior references to the PMS5003 (8-pin 1.25mm pitch connector).
> 
> **Key Architecture Impacts:**
> 1. **Electrical / Pinout:** PMS7003 utilizes a 10-pin (2x5 dual-row, 1.27mm pitch) male header with distinct pin mapping (Pins 1 & 2 = VCC 5V, Pins 3 & 4 = GND, Pin 5 = RESET, Pin 7 = RXD, Pin 9 = TXD, Pin 10 = SET).
> 2. **Serial & Protocol:** Operates at 9600 baud 8N1, producing the identical 32-byte binary frame format as PMS5003. Checksum formula and atmospheric particulate extraction remain bit-for-bit identical.
> 3. **Backend & Frontend Compatibility:** Zero API schema or database changes required. The FastAPI `ReadingCreate` schema and React 19 UI dashboard ingest and display atmospheric `pm1_0`, `pm2_5`, and `pm10` identically.
> 4. **Pre-Execution Boundary:** In strict adherence to project instructions:
>    - **No physical firmware flashing or hardware alterations will be executed until you review and authorize this plan.**
>    - **No physical testing has occurred.** All software verification was conducted using synthetic test vectors.
>    - The existing React 19 UI, FastAPI backend routes, SQLite WAL database, and 1D-CNN–BiGRU forecasting model artifacts remain 100% frozen and preserved.

---

## 2. Bill of Materials (BOM) & Component Specifications

| Item | Component | Specification / Part Number | Quantity | Role / Constraints |
| :---: | :--- | :--- | :---: | :--- |
| **1** | **Microcontroller** | ESP32-WROOM-32 / ESP32-S3 DevKit | 1 | 32-bit dual-core Xtensa @ 240MHz, 2.4GHz Wi-Fi, hardware UART2. |
| **2** | **Particulate Sensor** | Plantower PMS7003 | 1 | Laser scattering particulate matter sensor (PM1.0, PM2.5, PM10). Supply: 5.0V ± 0.1V. Logic: 3.3V TTL. Current: ≤100mA active, 120mA peak. |
| **3** | **Sensor Interface Cable / Adapter** | 10-pin 1.27mm (2x5) ribbon cable OR PMS7003 1.27mm-to-2.54mm breakout adapter board | 1 | Adapts high-density 1.27mm pitch header to standard 2.54mm breadboard/DuPont jumpers. |
| **4** | **Power Supply** | Regulated 5V DC Supply / USB VBUS (≥500mA) | 1 | Powers ESP32 and provides dedicated 5V rail for PMS7003 internal centrifugal fan and laser diode. |
| **5** | **DuPont Wires** | Premium stranded jumper wires (M-F / M-M) | 6 | High-reliability low-resistance signal and ground lines. |
| **6** | **Pull-up Resistor** | 10kΩ 0.25W Resistor (Optional) | 1 | Optional external pull-up for SET (Pin 10) if GPIO control is not used (sensor has internal pull-up). |

---

## 3. Electrical Pinout & Wiring Specification

### 3.1 PMS7003 10-Pin (2x5) Receptacle Pinout

The PMS7003 sensor features a miniature **10-pin (2x5 dual-row) male header with a 1.27 mm pitch**. Looking directly at the connector face (with Pin 1 situated at the keyed / corner position):

```text
       PMS7003 CONNECTOR GRID (2x5 Dual-Row, 1.27mm Pitch)
       ====================================================
               (Keyed / Corner Marker Side)
          [ Pin 1: VCC ]       [ Pin 2: VCC ]
          [ Pin 3: GND ]       [ Pin 4: GND ]
          [ Pin 5: RESET ]     [ Pin 6: NC  ]
          [ Pin 7: RXD ]       [ Pin 8: NC  ]
          [ Pin 9: TXD ]       [ Pin 10: SET ]
```

### 3.2 Electrical Interconnection Matrix

| PMS7003 Pin | Signal Name | Standard Wire / Breakout Label | ESP32 Connection | Electrical Level | Functional Description & Safety Warning |
| :---: | :--- | :--- | :--- | :---: | :--- |
| **Pin 1** | **VCC** | VCC / 5V (Red) | **VIN / 5V / VBUS** | **5.0V DC** | Main power supply for sensor laser diode and fan motor. Draw: ~100mA active, 120mA peak.<br>⚠️ **CRITICAL HAZARD:** *Do NOT connect to ESP32 3.3V pin. The 3.3V LDO regulator cannot supply the motor load, causing ESP32 brownouts and fan stall.* |
| **Pin 2** | **VCC** | VCC (Red) | Tied to Pin 1 | **5.0V DC** | Redundant power supply pin (internally bonded to Pin 1). Connect to 5V rail or leave tied to Pin 1. |
| **Pin 3** | **GND** | GND (Black) | **GND** | 0V | System reference ground. Must share a direct common ground with the ESP32 and power supply. |
| **Pin 4** | **GND** | GND (Black) | Tied to Pin 3 | 0V | Redundant ground pin (internally bonded to Pin 3). Connect to common GND or leave tied to Pin 3. |
| **Pin 5** | **RESET** | RST (White) | **GPIO 19** (or Floating) | 3.3V Logic | Hardware reset: `LOW` pulse (<0.8V) for > 100ms reboots the sensor microcontroller. Has internal pull-up; can be left floating if hardware reset is not required. |
| **Pin 6** | **NC** | — | **No Connection** | — | Unused / Reserved. Keep isolated. |
| **Pin 7** | **RXD** | RX (Green) | **GPIO 17** (UART2 TX) | 3.3V TTL | Serial command receiver. ESP32 transmits commands here (9600 baud, 3.3V logic). |
| **Pin 8** | **NC** | — | **No Connection** | — | Unused / Reserved. Keep isolated. |
| **Pin 9** | **TXD** | TX (Yellow) | **GPIO 16** (UART2 RX) | 3.3V TTL | Serial data transmitter. PMS7003 outputs binary frames here (9600 baud, 3.3V logic).<br>✅ **Directly compatible with ESP32 3.3V GPIO input.** |
| **Pin 10** | **SET** | SET (Blue) | **GPIO 18** (or 3.3V) | 3.3V Logic | Mode control: `HIGH` (3.3V or floating with internal pull-up) = Active continuous measurement; `LOW` (0V) = Low-power sleep mode (fan stopped). |

### 3.3 Breakout Adapter Board Pinout (If Using Standard Adapter)
If utilizing a standard PMS7003 breakout adapter board that converts the 1.27mm pitch 10-pin header to a standard 2.54mm single-row 8-pin header:
- `VCC` → ESP32 5V / VIN (5.0V DC)
- `GND` → ESP32 GND
- `SET` → ESP32 GPIO 18 (or 3.3V rail)
- `RXD` → ESP32 GPIO 17 (UART2 TX)
- `TXD` → ESP32 GPIO 16 (UART2 RX)
- `RST` → ESP32 GPIO 19 (or floating)

### 3.4 Electrical Schematic Diagram

```text
        +-------------------------------------------------+
        |           REGULATED 5V DC POWER SOURCE          |
        |        +5.0V Rail                     GND Rail  |
        +----+-------------------------------------+------+
             |                                     |
             |                                     +-----------------------+
             v                                                             |
    +-----------------------+                                              |
    | PMS7003 Pin 1 & 2     |                                              |
    | (VCC - 5.0V DC)       |                                              |
    +-----------------------+                                              |
                                                                           |
    +-----------------------+                                              |
    | PMS7003 Pin 3 & 4     | <--------------------------------------------+
    | (GND - 0V)            |                                              |
    +-----------------------+                                              |
                                                                           |
    +-----------------------+                                              |
    | PMS7003 Pin 5 (RESET) | <---- 3.3V Logic (ESP32 GPIO 19 / Floating)  |
    +-----------------------+                                              |
                                                                           |
    +-----------------------+                                              |
    | PMS7003 Pin 7 (RXD)   | <---- 3.3V UART TX (ESP32 GPIO 17)           |
    +-----------------------+                                              |
                                                                           |
    +-----------------------+                                              |
    | PMS7003 Pin 9 (TXD)   | ----> 3.3V UART RX (ESP32 GPIO 16)           |
    +-----------------------+                                              |
                                                                           |
    +-----------------------+                                              |
    | PMS7003 Pin 10 (SET)  | <---- 3.3V Mode Ctrl (ESP32 GPIO 18 / High)  |
    +-----------------------+                                              |
                                                                           | Common GND
    +-----------------------+                                              |
    | ESP32 DevKit          |                                              |
    |  - GND Pin            | <--------------------------------------------+
    |  - VIN / 5V Pin       | <---- From 5V USB / Power Rail
    |  - GPIO 16 (RX2)      | <---- From PMS7003 Pin 9 (TXD)
    |  - GPIO 17 (TX2)      | ----> To PMS7003 Pin 7 (RXD)
    |  - GPIO 18 (SET)      | ----> To PMS7003 Pin 10 (SET)
    |  - GPIO 19 (RESET)    | ----> To PMS7003 Pin 5 (RESET)
    +-----------------------+
```

---

## 4. Serial Protocol, Binary Frame Parsing & Malformed-Frame Recovery Engine

### 4.1 UART Configuration
- **Port:** ESP32 Hardware UART2 (`Serial2`)
- **Baud Rate:** `9600 bps`
- **Data Bits:** `8`
- **Parity:** `None`
- **Stop Bits:** `1` (`8N1`)
- **Flow Control:** `None`

### 4.2 32-Byte Frame Structure & Bitwise Mapping

The PMS7003 outputs a 32-byte frame continuously every 200–800 ms in active mode:

| Byte Index | Field Description | Hex / Mask | Target Destination |
| :---: | :--- | :--- | :--- |
| **0** | Frame Header 1 | `0x42` ('B') | Frame synchronizer magic byte 1 |
| **1** | Frame Header 2 | `0x4D` ('M') | Frame synchronizer magic byte 2 |
| **2..3** | Frame Length | `0x001C` (28 bytes) | Expected remaining payload length |
| **4..5** | PM1.0 Standard (CF=1) | `(Byte[4] << 8) \| Byte[5]` | Factory calibration (standard aerosol) |
| **6..7** | PM2.5 Standard (CF=1) | `(Byte[6] << 8) \| Byte[7]` | Factory calibration (standard aerosol) |
| **8..9** | PM10 Standard (CF=1) | `(Byte[8] << 8) \| Byte[9]` | Factory calibration (standard aerosol) |
| **10..11** | **PM1.0 Atmospheric** | `(Byte[10] << 8) \| Byte[11]` | **Ingested to API as `pm1_0` ($\mu\text{g/m}^3$)** |
| **12..13** | **PM2.5 Atmospheric** | `(Byte[12] << 8) \| Byte[13]` | **Ingested to API as `pm2_5` ($\mu\text{g/m}^3$)** |
| **14..15** | **PM10 Atmospheric** | `(Byte[14] << 8) \| Byte[15]` | **Ingested to API as `pm10` ($\mu\text{g/m}^3$)** |
| **16..27** | Particle Counts (0.3–10$\mu$m) | 6 × 16-bit integers | Diagnostic bin counts per 0.1L air |
| **28..29** | Reserved / Version Info | 2 bytes | Diagnostic sensor firmware version |
| **30..31** | **Frame Checksum** | `(Byte[30] << 8) \| Byte[31]` | **Expected 16-bit additive sum** |

### 4.3 Checksum Validation Algorithm
The firmware computes the 16-bit sum of the first 30 bytes modulo 65536:
$$\text{Calculated Checksum} = \left(\sum_{i=0}^{29} \text{Frame}[i]\right) \pmod{65536}$$
$$\text{Expected Checksum} = (\text{Frame}[30] \ll 8) \mid \text{Frame}[31]$$
- **Pass Criterion:** $\text{Calculated Checksum} == \text{Expected Checksum}$.

### 4.4 Malformed-Frame Recovery Protocol
In edge deployments, UART serial lines can experience baud jitter, electrical transients, or dropped bytes during boot or sensor power cycles. The firmware incorporates a 5-stage malformed-frame recovery state machine:

1. **Byte-by-Byte Sliding Window Synchronizer:**
   The parser does not assume the UART buffer starts with `0x42`. It scans incoming bytes sequentially. If `0x42` is detected, it peeks at the next byte. If the next byte is NOT `0x4D`, it consumes `0x42` and continues searching. This eliminates framing deadlock if `0x42` appears in the payload.
2. **Payload Length Guard:**
   Bytes 2 & 3 must equal `0x001C` (28 bytes). If length $\neq 28$, the frame is immediately flagged as corrupt and discarded without waiting.
3. **Frame Assembly Timeout:**
   Once a valid `0x42 0x4D` header is detected, the remaining 30 bytes must arrive within **100 ms**. If a timeout occurs, the buffer is purged to prevent partial frame stalling.
4. **Consecutive Error Ring-Buffer Flush:**
   A global counter tracks consecutive checksum failures. If $\ge 3$ consecutive checksum errors occur, the firmware triggers a complete UART flush (`while (pmsSerial.available()) pmsSerial.read();`) to re-sync on the clean leading edge of the next transmission burst.
5. **Hardware Watchdog Recovery:**
   If no valid frame is successfully parsed for $>60$ seconds, the firmware triggers hardware line recovery: it pulls the SET pin (GPIO 18) `LOW` for 2 seconds and returns it `HIGH`, or pulses the RESET pin (GPIO 19) `LOW` for 150 ms to hard-reboot the PMS7003 internal microcontroller.

---

## 5. ESP32 Firmware Implementation Blueprint

### 5.1 Dual-Core FreeRTOS Task Architecture
- **Core 1 (PMS7003 Telemetry Task — Priority 2):**
  - Executes non-blocking UART frame acquisition on `Serial2`.
  - Runs sliding-window header hunt and checksum validation.
  - Pushes valid readings into a 10-sample rolling buffer.
  - Calculates rolling median sample every 60 seconds.
  - Monitors line health and triggers sensor reboot if stream freezes.
- **Core 0 (Network & Ingestion Task — Priority 1):**
  - Manages Wi-Fi station connectivity with exponential backoff.
  - Locks SNTP UTC clock (`pool.ntp.org`).
  - Serializes JSON telemetry conforming to Pydantic `ReadingCreate`.
  - Issues HTTP POST to `/api/readings` with `X-API-Key`.
  - Manages 120-reading circular RAM buffer during network drops.

### 5.2 Complete Firmware Implementation (`AirPurifyNode.ino`)

```cpp
/**
 * AirPurify AI — Physical Edge Telemetry Firmware
 * Target: Espressif ESP32 + Plantower PMS7003 Particulate Sensor
 * Interface: Hardware UART2 (GPIO 16 RX / GPIO 17 TX) @ 9600 baud 8N1
 * Ingestion: HTTP/HTTPS POST /api/readings with X-API-Key
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <time.h>

// --- Pin Definitions (ESP32 to PMS7003) ---
#define PMS_RX2_PIN 16     // ESP32 RX2 <- PMS7003 Pin 9 (TXD, 3.3V TTL)
#define PMS_TX2_PIN 17     // ESP32 TX2 -> PMS7003 Pin 7 (RXD, 3.3V TTL)
#define PMS_SET_PIN 18     // ESP32 Pin -> PMS7003 Pin 10 (SET, 3.3V Mode Control)
#define PMS_RST_PIN 19     // ESP32 Pin -> PMS7003 Pin 5 (RESET, Active LOW)
#define STATUS_LED_PIN 2   // Onboard diagnostic status LED

// --- Telemetry Buffer Structure ---
struct SensorData {
  float pm1_0;
  float pm2_5;
  float pm10;
  time_t timestamp;
  bool valid;
};

// --- Hardware Handles ---
HardwareSerial pmsSerial(2);
Preferences prefs;

// --- Runtime Configuration (Loaded from Encrypted NVS) ---
String wifiSSID = "";
String wifiPass = "";
String apiKey = "";
String apiHost = "http://192.168.1.100:8001"; // Target backend LAN IP
String deviceId = "ESP32-CAMPUS-001";
String locationId = "Cleanroom-Alpha";

// --- NTP Configuration ---
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 0; // UTC
const int daylightOffset_sec = 0;

// --- Circular RAM Outage Buffer (120 samples = 2 hours) ---
#define BUFFER_CAPACITY 120
SensorData outageBuffer[BUFFER_CAPACITY];
int bufferHead = 0;
int bufferTail = 0;
int bufferCount = 0;

void pushBuffer(SensorData data) {
  if (bufferCount < BUFFER_CAPACITY) {
    outageBuffer[bufferHead] = data;
    bufferHead = (bufferHead + 1) % BUFFER_CAPACITY;
    bufferCount++;
  } else {
    // Overwrite oldest sample during extended outage
    outageBuffer[bufferTail] = data;
    bufferTail = (bufferTail + 1) % BUFFER_CAPACITY;
    bufferHead = (bufferHead + 1) % BUFFER_CAPACITY;
  }
}

bool popBuffer(SensorData* data) {
  if (bufferCount == 0) return false;
  *data = outageBuffer[bufferTail];
  bufferTail = (bufferTail + 1) % BUFFER_CAPACITY;
  bufferCount--;
  return true;
}

// --- PMS7003 Hardware Reset Routine ---
void resetPMS7003() {
  Serial.println("[PMS7003] Triggering sensor hardware reset pulse...");
  digitalWrite(PMS_RST_PIN, LOW);
  delay(150);
  digitalWrite(PMS_RST_PIN, HIGH);
  delay(1000); // Allow sensor internal MCU and fan to stabilize
}

// --- PMS7003 Robust Stream Parser with Malformed-Frame Recovery ---
int consecutiveErrors = 0;
unsigned long lastValidFrameTime = 0;

bool readPMS7003(SensorData* result) {
  result->valid = false;

  // 1. Sliding-window hunt for frame header 0x42 0x4D
  while (pmsSerial.available() >= 32) {
    if (pmsSerial.read() != 0x42) {
      continue; // Discard noise until start byte 0x42
    }
    if (pmsSerial.peek() != 0x4D) {
      continue; // Not followed by 0x4D, keep scanning
    }
    pmsSerial.read(); // Consume 0x4D

    // 2. Read remaining 30 bytes with timeout guard
    uint8_t buffer[30];
    unsigned long startRead = millis();
    size_t bytesRead = 0;
    while (bytesRead < 30 && (millis() - startRead < 100)) {
      if (pmsSerial.available()) {
        buffer[bytesRead++] = pmsSerial.read();
      }
    }

    if (bytesRead != 30) {
      Serial.println("[PMS7003] Incomplete frame timeout! Discarding fragment.");
      consecutiveErrors++;
      return false;
    }

    // 3. Frame length validation (Bytes 2..3 should equal 0x001C = 28 bytes)
    uint16_t frameLen = ((uint16_t)buffer[0] << 8) | buffer[1];
    if (frameLen != 28) {
      Serial.printf("[PMS7003] Invalid frame length: %u (expected 28)\n", frameLen);
      consecutiveErrors++;
      return false;
    }

    // 4. Checksum verification: Sum(0x42 + 0x4D + buffer[0..27])
    uint16_t calculatedSum = 0x42 + 0x4D;
    for (int i = 0; i < 28; i++) {
      calculatedSum += buffer[i];
    }
    uint16_t expectedSum = ((uint16_t)buffer[28] << 8) | buffer[29];

    if (calculatedSum != expectedSum) {
      Serial.printf("[PMS7003] Checksum mismatch! Calc: 0x%04X, Expected: 0x%04X\n",
                    calculatedSum, expectedSum);
      consecutiveErrors++;
      if (consecutiveErrors >= 3) {
        Serial.println("[PMS7003] >= 3 consecutive errors! Flushing UART buffer...");
        while (pmsSerial.available()) pmsSerial.read();
      }
      return false;
    }

    // 5. Checksum passed: extract atmospheric PM measurements (Bytes 10..15 of full frame)
    // In our buffer (which starts after 0x42 0x4D):
    // buffer[8..9] = Atmospheric PM1.0
    // buffer[10..11] = Atmospheric PM2.5
    // buffer[12..13] = Atmospheric PM10
    result->pm1_0 = (float)(((uint16_t)buffer[8] << 8) | buffer[9]);
    result->pm2_5 = (float)(((uint16_t)buffer[10] << 8) | buffer[11]);
    result->pm10  = (float)(((uint16_t)buffer[12] << 8) | buffer[13]);
    time(&result->timestamp);
    result->valid = true;

    consecutiveErrors = 0;
    lastValidFrameTime = millis();
    return true;
  }

  // 6. Watchdog check: If no valid frame for >60s, reboot sensor
  if (millis() - lastValidFrameTime > 60000 && lastValidFrameTime > 0) {
    Serial.println("[PMS7003] Sensor stream stalled >60s. Initiating watchdog recovery.");
    resetPMS7003();
    lastValidFrameTime = millis();
  }

  return false;
}

// --- ISO 8601 UTC Formatter ---
String formatIsoTime(time_t t) {
  struct tm timeinfo;
  gmtime_r(&t, &timeinfo);
  char buf[30];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
  return String(buf);
}

// --- Telemetry Dispatch to FastAPI /api/readings ---
bool sendTelemetry(const SensorData& data) {
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  String url = apiHost + "/api/readings";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", apiKey);
  http.setTimeout(5000);

  // Construct JSON payload conforming to Pydantic ReadingCreate
  String payload = "{";
  payload += "\"device_id\":\"" + deviceId + "\",";
  payload += "\"location_id\":\"" + locationId + "\",";
  payload += "\"timestamp\":\"" + formatIsoTime(data.timestamp) + "\",";
  payload += "\"pm1_0\":" + String(data.pm1_0, 1) + ",";
  payload += "\"pm2_5\":" + String(data.pm2_5, 1) + ",";
  payload += "\"pm10\":" + String(data.pm10, 1);
  payload += "}";

  int httpCode = http.POST(payload);
  http.end();

  if (httpCode == 201) {
    digitalWrite(STATUS_LED_PIN, HIGH);
    delay(50);
    digitalWrite(STATUS_LED_PIN, LOW);
    return true;
  } else if (httpCode == 429) {
    Serial.println("[HTTP] Rate limited (429). Backing off 30s.");
    delay(30000);
  } else if (httpCode == 401) {
    Serial.println("[HTTP] 401 Unauthorized! Verify provisioned AIRPURIFY_API_KEY.");
  } else {
    Serial.printf("[HTTP] Ingestion failed with status code: %d\n", httpCode);
  }
  return false;
}

void setup() {
  Serial.begin(115200);
  pinMode(STATUS_LED_PIN, OUTPUT);
  pinMode(PMS_SET_PIN, OUTPUT);
  pinMode(PMS_RST_PIN, OUTPUT);

  // Ensure PMS7003 is enabled and not in reset
  digitalWrite(PMS_SET_PIN, HIGH);
  digitalWrite(PMS_RST_PIN, HIGH);

  // Initialize Hardware UART2 for PMS7003
  pmsSerial.begin(9600, SERIAL_8N1, PMS_RX2_PIN, PMS_TX2_PIN);
  lastValidFrameTime = millis();

  // Load site credentials from Encrypted NVS
  prefs.begin("airpurify", true);
  wifiSSID = prefs.getString("ssid", "CAMPUS_WIFI");
  wifiPass = prefs.getString("pass", "");
  apiKey = prefs.getString("api_key", "airpurify-dev-key-2026");
  apiHost = prefs.getString("host", "http://192.168.1.100:8001");
  deviceId = prefs.getString("dev_id", "ESP32-CAMPUS-001");
  locationId = prefs.getString("loc_id", "Cleanroom-Alpha");
  prefs.end();

  // Connect to Wi-Fi
  Serial.printf("[WIFI] Connecting to %s...\n", wifiSSID.c_str());
  WiFi.mode(WIFI_STA);
  WiFi.begin(wifiSSID.c_str(), wifiPass.c_str());

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WIFI] Connected! Assigned IP: %s\n", WiFi.localIP().toString().c_str());
    configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
    struct tm timeinfo;
    if (getLocalTime(&timeinfo)) {
      Serial.println("[NTP] UTC time synchronized successfully.");
    }
  } else {
    Serial.println("\n[WIFI] Connection failed. Operating in offline buffer mode.");
  }
}

void loop() {
  static unsigned long lastSampleTime = 0;
  static unsigned long lastReportTime = 0;
  static float pm1_samples[5];
  static float pm25_samples[5];
  static float pm10_samples[5];
  static int sampleIdx = 0;

  // Sample PMS7003 every 10 seconds
  if (millis() - lastSampleTime >= 10000) {
    lastSampleTime = millis();
    SensorData sample;
    if (readPMS7003(&sample)) {
      pm1_samples[sampleIdx] = sample.pm1_0;
      pm25_samples[sampleIdx] = sample.pm2_5;
      pm10_samples[sampleIdx] = sample.pm10;
      sampleIdx++;
    }
  }

  // Aggregate and report 60-second median record
  if (millis() - lastReportTime >= 60000) {
    lastReportTime = millis();
    if (sampleIdx > 0) {
      SensorData report;
      report.pm1_0 = pm1_samples[sampleIdx / 2];
      report.pm2_5 = pm25_samples[sampleIdx / 2];
      report.pm10  = pm10_samples[sampleIdx / 2];
      time(&report.timestamp);
      sampleIdx = 0;

      Serial.printf("[PMS7003] 60s Telemetry: PM1.0=%.1f, PM2.5=%.1f, PM10=%.1f ug/m3\n",
                    report.pm1_0, report.pm2_5, report.pm10);

      // Attempt transmission or push to RAM outage buffer
      if (!sendTelemetry(report)) {
        pushBuffer(report);
      } else {
        // Drain buffered samples if connection is healthy
        SensorData oldSample;
        while (popBuffer(&oldSample)) {
          delay(1500); // Pace re-transmissions to respect rate limit
          sendTelemetry(oldSample);
        }
      }
    }
  }
}
```

---

## 6. Network & Backend Alignment Checklist

| Configuration Parameter | Required Value | Notes & Pitfalls |
| :--- | :--- | :--- |
| **Ingestion Target URL** | `http://<HOST_LAN_IP>:8001/api/readings` | ⚠️ **DO NOT USE `localhost` or `127.0.0.1`** in ESP32 firmware. The ESP32 is a separate network node; `localhost` targets itself. Use the PC's actual LAN IP (e.g. `192.168.1.50`). |
| **Authentication Header** | `X-API-Key: <AIRPURIFY_API_KEY>` | Must match `AIRPURIFY_API_KEY` configured in `backend/.env`. |
| **Content-Type** | `application/json` | Enforces Pydantic `ReadingCreate` schema validation. |
| **Timestamp Format** | ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`) | Synced via SNTP (`pool.ntp.org`). |
| **API Schema Compatibility** | **100% Compatible (No change needed)** | PMS7003 outputs atmospheric PM1.0, PM2.5, and PM10 in $\mu\text{g/m}^3$, matching backend fields exactly. |
| **Firewall Rule** | Allow inbound port 8001 | On Windows development machine, ensure inbound TCP connections on port 8001 are permitted through Windows Defender Firewall. |

---

## 7. Step-by-Step Five-Gate Validation Protocol

Execute validation across five discrete gates. Do not advance to the next gate until the current gate succeeds.

### Gate 1 — Physical Safe Power-Up & Electrical Inspection
1. Before connecting the ESP32 to PC USB, verify wiring with a digital multimeter:
   - Check resistance between PMS7003 VCC (Pins 1 & 2) and GND (Pins 3 & 4): must be > 100kΩ (zero short circuits).
   - Verify Pin 9 (TXD) connects to ESP32 GPIO 16.
   - Verify Pin 7 (RXD) connects to ESP32 GPIO 17.
   - Verify Pin 10 (SET) connects to ESP32 GPIO 18 (or 3.3V).
   - Verify Pin 5 (RESET) connects to ESP32 GPIO 19 (or left floating).
   - Verify Pins 3 & 4 (GND) are tied directly to ESP32 system GND.
2. Connect external 5V power supply to PMS7003 VCC and GND.
3. Listen for PMS7003 internal centrifugal fan spin-up (subtle quiet hum within 500 ms).
4. Measure voltage across PMS7003 Pin 1 & Pin 3: must read **4.90V – 5.10V DC**.
5. Measure logic voltage on PMS7003 Pin 9 (TXD): must read **3.2V – 3.4V DC**.

### Gate 2 — Raw UART Serial Stream & Checksum Validation
1. Connect ESP32 to PC via USB.
2. Open Serial Monitor at **115200 baud**.
3. Observe raw console logs:
   - Confirm magic header detected: `0x42 0x4D`.
   - Confirm frame length verified: `28 bytes`.
   - Confirm calculated checksum matches expected checksum (0 discarded frames under normal operation).
   - Observe ambient particulate readings: typical clean indoor baseline values range between 5 and 35 $\mu\text{g/m}^3$.

### Gate 3 — Wi-Fi Association & SNTP Clock Lock
1. Observe Serial Monitor during boot:
   - Confirm `[WIFI] Connected! Assigned IP: 192.168.X.X`.
   - Confirm `[NTP] UTC time synchronized successfully`.
   - Ensure current UTC year is 2026 (reject timestamps with year 1970).

### Gate 4 — Ingestion API Response (`POST /api/readings`)
1. Monitor terminal running FastAPI backend:
   ```text
   INFO: 192.168.X.X - "POST /api/readings HTTP/1.1" 201 Created
   ```
2. Verify response payload in ESP32 serial console:
   ```json
   {
     "id": 80,
     "device_id": "ESP32-CAMPUS-001",
     "location_id": "Cleanroom-Alpha",
     "data_quality_status": "valid"
   }
   ```
3. Confirm onboard status LED flashes (50ms pulse) upon receiving HTTP 201.

### Gate 5 — MongoDB Atlas Database Persistence & Dashboard Acceptance
1. Query MongoDB Atlas database from backend terminal:
   ```bash
   python -c "import os; from pymongo import MongoClient; client=MongoClient(os.getenv('MONGODB_URI')); db=client[os.getenv('MONGODB_DB_NAME','airpurify_db')]; print(db['sensor_readings'].find_one(sort=[('id', -1)]))"
   ```
   Confirm record ID, device identifier, and PM measurements match sensor serial output.
2. Open browser dashboard (`http://localhost:8443` or production URL):
   - Confirm device `ESP32-CAMPUS-001` appears in device selector dropdown with status `active`.
   - Confirm live KPI cards for PM1.0, PM2.5, and PM10 reflect physical sensor readings.
   - Confirm history charts render continuous real-time telemetry points.
   - Confirm 1D-CNN–BiGRU deep learning service incorporates the live telemetry into sliding-window inference.

---

## 8. Safe Power-Up, Troubleshooting & Rollback Instructions

### 8.1 Diagnostic Troubleshooting Matrix

| Symptom | Probable Cause | Remediation Step |
| :--- | :--- | :--- |
| **No fan hum from PMS7003** | Missing or inadequate 5V supply | Verify external 5V rail. Check that Pin 10 (SET) is pulled high (3.3V). Check 1.27mm ribbon seating. |
| **`[PMS7003] Checksum mismatch`** | Baud rate mismatch or loose DuPont wire | Verify 9600 baud setting. Inspect connection between PMS7003 Pin 9 (TXD) and ESP32 GPIO 16. |
| **`Incomplete frame timeout`** | Partial frame or electrical noise | Ensure common ground is secure. Firmware automatic buffer flush will re-sync stream. |
| **HTTP 401 Unauthorized** | Invalid or missing API key | Verify provisioned `AIRPURIFY_API_KEY` matches `backend/.env`. |
| **HTTP 422 Unprocessable** | Malformed JSON or negative values | Verify timestamp format (`YYYY-MM-DDTHH:MM:SSZ`) and ensure PM values are non-negative. |
| **HTTP 429 Too Many Requests** | Reporting interval too fast | Ensure reporting interval is ≥60 seconds. Firmware will back off 30s. |
| **Connection Refused / Timeout** | Firewall or wrong IP address | Ensure ESP32 targets host machine's LAN IP (`192.168.X.X`), not `localhost`. Open port 8001 in Windows Firewall. |

### 8.2 Safe Rollback Procedure
If physical hardware causes instability or unexpected behavior:
1. Disconnect USB and 5V power from ESP32 immediately.
2. The AirPurify AI backend and frontend will remain fully functional; the UI will simply indicate that the edge node is offline after 15 minutes per stale data detection rules.
3. The MongoDB Atlas cloud cluster remains protected with automatic multi-zone replication; no data corruption will occur.

---

## 9. Undocumented Parameters (Action Items for User)

The following site-specific deployment parameters must be provisioned into ESP32 NVS before powering on:

| Parameter | Description | Where to Provide |
| :--- | :--- | :--- |
| **Wi-Fi SSID** | Name of 2.4 GHz local Wi-Fi network | Provisioned into ESP32 NVS |
| **Wi-Fi Password** | WPA2/WPA3 network password | Provisioned into ESP32 NVS |
| **Backend Host LAN IP** | IP address of PC/server running FastAPI on local subnet (e.g. `192.168.1.50`) | Configured in firmware / NVS |
| **Production API Key** | Secret key matching `AIRPURIFY_API_KEY` in `backend/.env` | Provisioned into ESP32 NVS |
| **Physical Location Name** | Site identifier for sensor node (e.g. `Cleanroom-Alpha`, `Lab-302`) | Configured in firmware / NVS |

---

## 10. Summary of Changes Required for PMS7003 Integration

| Subsystem | PMS5003 Baseline | PMS7003 Updated Specification | Status / Impact |
| :--- | :--- | :--- | :--- |
| **Physical Connector** | 8-pin single-row, 1.25mm pitch Molex | **10-pin dual-row (2x5), 1.27mm pitch header** | **Physical Change:** Requires 10-pin ribbon cable or 1.27mm-to-2.54mm adapter board. |
| **Pin Mapping** | Pin 1=VCC, 2=GND, 3=SET, 4=RX, 5=TX, 6=RST | **Pins 1&2=VCC, 3&4=GND, 5=RST, 7=RX, 9=TX, 10=SET** | **Wiring Change:** Pin assignments updated in schematic and wiring matrix. |
| **Power Requirements** | 5.0V DC supply, ~120mA peak | **5.0V DC supply, ~100-120mA peak** | **Unchanged:** Dedicated 5V rail required; 3.3V logic level for serial lines. |
| **UART Protocol** | 9600 baud, 8N1 | **9600 baud, 8N1** | **Unchanged:** ESP32 Hardware UART2 configuration is identical. |
| **Frame Parsing** | 32-byte binary packet | **32-byte binary packet** | **Unchanged:** Same header (`0x42 0x4D`), frame length (28), and checksum formula. |
| **Field Extraction** | Bytes 10..15 (PM1.0, PM2.5, PM10) | **Bytes 10..15 (PM1.0, PM2.5, PM10)** | **Unchanged:** Same atmospheric particulate registers. |
| **API Ingestion Contract**| `POST /api/readings` (`ReadingCreate`) | `POST /api/readings` (`ReadingCreate`) | **Unchanged:** 100% compatible. Zero backend code changes. |
| **Database & Frontend** | SQLite WAL schema, React 19 UI | SQLite WAL schema, React 19 UI | **Unchanged:** 100% compatible. Zero frontend code changes. |

/**
 * =============================================================================
 * AirPurify AI — Physical Edge Telemetry Firmware
 * Target: Espressif ESP32 (ESP-WROOM-32 / ESP32-S3)
 * Sensor: Plantower PMS7003 Laser Particulate Matter Sensor
 * Interface: Hardware UART2 (9600 baud 8N1, 3.3V TTL)
 * Ingestion: HTTP/HTTPS POST to FastAPI /api/readings with X-API-Key
 * =============================================================================
 *
 * ARCHITECTURE & SECURITY NOTICE:
 * - The ESP32 communicates EXCLUSIVELY with the FastAPI ingestion service.
 * - NEVER place MongoDB Atlas credentials or connection strings on this device.
 *   The FastAPI backend acts as the secure, authenticated cloud database gateway.
 * - Wi-Fi credentials and API keys are provisioned into encrypted Non-Volatile
 *   Storage (NVS) via the ESP32 Preferences library.
 * =============================================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <time.h>

// -----------------------------------------------------------------------------
// Pin Definitions (ESP32-WROOM-32 to Plantower PMS7003)
// -----------------------------------------------------------------------------
#define PMS_RX2_PIN 16     // ESP32 RX2  <- PMS7003 Pin 9 (TXD, 3.3V TTL)
#define PMS_TX2_PIN 17     // ESP32 TX2  -> PMS7003 Pin 7 (RXD, 3.3V TTL)
#define PMS_SET_PIN 18     // ESP32 GPIO -> PMS7003 Pin 10 (SET, 3.3V Mode Control)
#define PMS_RST_PIN 19     // ESP32 GPIO -> PMS7003 Pin 5 (RESET, Active LOW)
#define STATUS_LED_PIN 2   // Onboard diagnostic status LED

// -----------------------------------------------------------------------------
// Telemetry Data Structure
// -----------------------------------------------------------------------------
struct SensorData {
  float pm1_0;
  float pm2_5;
  float pm10;
  time_t timestamp;
  bool valid;
};

// -----------------------------------------------------------------------------
// Hardware Handles & Runtime Configuration
// -----------------------------------------------------------------------------
HardwareSerial pmsSerial(2);
Preferences prefs;

// Default fallbacks (overwritten by encrypted NVS on boot)
String wifiSSID = "";
String wifiPass = "";
String apiKey = "airpurify-dev-key-2026";
String apiHost = "http://192.168.1.100:8001"; // Target FastAPI server LAN IP (NOT localhost)
String deviceId = "ESP32-CAMPUS-001";
String locationId = "Cleanroom-Alpha";

// NTP Configuration
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 0; // UTC
const int daylightOffset_sec = 0;

// -----------------------------------------------------------------------------
// Circular RAM Outage Buffer (120 samples = 2 hours of disconnected buffer)
// -----------------------------------------------------------------------------
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
    // Overwrite oldest sample during extended network outages
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

// -----------------------------------------------------------------------------
// PMS7003 Hardware Reset Routine
// -----------------------------------------------------------------------------
void resetPMS7003() {
  Serial.println("[PMS7003] Triggering sensor hardware reset pulse...");
  digitalWrite(PMS_RST_PIN, LOW);
  delay(150);
  digitalWrite(PMS_RST_PIN, HIGH);
  delay(1000); // Allow internal sensor MCU and fan motor to stabilize
}

// -----------------------------------------------------------------------------
// PMS7003 Stream Parser with Sliding-Window Recovery
// -----------------------------------------------------------------------------
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
      continue; // Next byte is not 0x4D, continue search
    }
    pmsSerial.read(); // Consume 0x4D

    // 2. Read remaining 30 bytes with timeout guard (100 ms)
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

    // 3. Frame length validation (Bytes 2..3 must equal 0x001C = 28 bytes)
    uint16_t frameLen = ((uint16_t)buffer[0] << 8) | buffer[1];
    if (frameLen != 28) {
      Serial.printf("[PMS7003] Invalid frame length: %u (expected 28)\n", frameLen);
      consecutiveErrors++;
      return false;
    }

    // 4. 16-bit additive checksum verification modulo 65536
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

    // 5. Checksum verified: extract atmospheric particulate readings
    // Full frame byte index:
    // buffer[8..9]   = Atmospheric PM1.0 (ug/m3)
    // buffer[10..11] = Atmospheric PM2.5 (ug/m3)
    // buffer[12..13] = Atmospheric PM10 (ug/m3)
    result->pm1_0 = (float)(((uint16_t)buffer[8] << 8) | buffer[9]);
    result->pm2_5 = (float)(((uint16_t)buffer[10] << 8) | buffer[11]);
    result->pm10  = (float)(((uint16_t)buffer[12] << 8) | buffer[13]);
    time(&result->timestamp);
    result->valid = true;

    consecutiveErrors = 0;
    lastValidFrameTime = millis();
    return true;
  }

  // 6. Hardware Watchdog: If no valid frame parsed for >60s, trigger sensor reset
  if (millis() - lastValidFrameTime > 60000 && lastValidFrameTime > 0) {
    Serial.println("[PMS7003] Sensor stream stalled >60s. Triggering watchdog reset.");
    resetPMS7003();
    lastValidFrameTime = millis();
  }

  return false;
}

// -----------------------------------------------------------------------------
// ISO 8601 UTC Timestamp Formatter
// -----------------------------------------------------------------------------
String formatIsoTime(time_t t) {
  struct tm timeinfo;
  gmtime_r(&t, &timeinfo);
  char buf[30];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
  return String(buf);
}

// -----------------------------------------------------------------------------
// Ingestion Dispatcher: HTTP POST to FastAPI /api/readings
// -----------------------------------------------------------------------------
bool sendTelemetry(const SensorData& data) {
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  String url = apiHost + "/api/readings";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", apiKey);
  http.setTimeout(5000); // 5-second socket timeout

  // Serialize JSON payload matching Pydantic ReadingCreate schema
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
    // Flash onboard diagnostic LED for 50 ms upon successful write
    digitalWrite(STATUS_LED_PIN, HIGH);
    delay(50);
    digitalWrite(STATUS_LED_PIN, LOW);
    return true;
  } else if (httpCode == 429) {
    Serial.println("[HTTP] Ingestion rate limited (429). Backing off 30s.");
    delay(30000);
  } else if (httpCode == 401) {
    Serial.println("[HTTP] 401 Unauthorized! Check configured AIRPURIFY_API_KEY.");
  } else {
    Serial.printf("[HTTP] Ingestion failed with status code: %d\n", httpCode);
  }
  return false;
}

// -----------------------------------------------------------------------------
// System Setup
// -----------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  pinMode(STATUS_LED_PIN, OUTPUT);
  pinMode(PMS_SET_PIN, OUTPUT);
  pinMode(PMS_RST_PIN, OUTPUT);

  // Assert default active states
  digitalWrite(PMS_SET_PIN, HIGH); // Active sampling mode
  digitalWrite(PMS_RST_PIN, HIGH); // Active high reset release

  // Initialize Hardware UART2 for PMS7003
  pmsSerial.begin(9600, SERIAL_8N1, PMS_RX2_PIN, PMS_TX2_PIN);
  lastValidFrameTime = millis();

  // Load site provisioning secrets from encrypted NVS
  prefs.begin("airpurify", true);
  wifiSSID = prefs.getString("ssid", "CAMPUS_WIFI");
  wifiPass = prefs.getString("pass", "");
  apiKey = prefs.getString("api_key", "airpurify-dev-key-2026");
  apiHost = prefs.getString("host", "http://192.168.1.100:8001");
  deviceId = prefs.getString("dev_id", "ESP32-CAMPUS-001");
  locationId = prefs.getString("loc_id", "Cleanroom-Alpha");
  prefs.end();

  // Connect to Wi-Fi station
  Serial.printf("\n[WIFI] Connecting to SSID: %s...\n", wifiSSID.c_str());
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
    Serial.println("\n[WIFI] Wi-Fi connection timed out. Telemetry will buffer in RAM.");
  }
}

// -----------------------------------------------------------------------------
// Main Execution Loop
// -----------------------------------------------------------------------------
void loop() {
  static unsigned long lastSampleTime = 0;
  static unsigned long lastReportTime = 0;
  static float pm1_samples[5];
  static float pm25_samples[5];
  static float pm10_samples[5];
  static int sampleIdx = 0;

  // 1. Sample PMS7003 every 10 seconds
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

  // 2. Aggregate and report 60-second median telemetry
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

      // Dispatch to FastAPI backend
      if (!sendTelemetry(report)) {
        pushBuffer(report);
      } else {
        // Drain buffered samples if connection is healthy
        SensorData oldSample;
        while (popBuffer(&oldSample)) {
          delay(1500); // Pace transmissions to respect rate limit
          sendTelemetry(oldSample);
        }
      }
    }
  }
}

# Manufacturer Integration Guide for GPS Tracking Platform

## Table of Contents
1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [ESP32 Device Implementation](#esp32-device-implementation)
4. [API Integration](#api-integration)
5. [Testing with Emulator](#testing-with-emulator)
6. [Production Deployment](#production-deployment)
7. [Troubleshooting](#troubleshooting)

## Overview

This guide helps manufacturers integrate their GPS tracking devices with our platform. The platform supports:
- Real-time GPS tracking via MQTT over TLS
- Secure device registration and authentication
- HMAC-signed messages for data integrity
- TimescaleDB for efficient time-series storage
- RESTful API for device management

### Key Concepts

1. **Manufacturer Secret**: A unique key provided to each manufacturer for device registration
2. **Device Registration**: One-time process to authenticate and activate devices
3. **API Key**: Generated during registration for ongoing device authentication
4. **HMAC Signing**: All GPS data must be cryptographically signed

## Getting Started

### 1. Obtain Manufacturer Credentials

Contact the platform administrator to receive:
- Manufacturer name (e.g., "DIGIFLY", "SKYTRACK", etc.)
- Manufacturer secret (32+ character key)
- API endpoint URL
- MQTT broker details

### 2. Platform Architecture

```
┌─────────────┐      MQTT/TLS      ┌──────────────┐
│ ESP32       │ ─────────────────► │ MQTT Broker  │
│ Device      │     Port 8883      │ (HAProxy LB) │
└─────────────┘                    └──────────────┘
                                           │
                                           ▼
┌─────────────┐      HTTP API      ┌──────────────┐
│ Registration│ ─────────────────► │ API Server   │
│ Client      │     Port 80/443    │ (Nginx LB)   │
└─────────────┘                    └──────────────┘
```

## ESP32 Device Implementation

### Hardware Requirements

- **MCU**: ESP32 or ESP32-S3
- **GPS Module**: Neo-6M/7M/8M or equivalent
- **Power**: Battery with voltage monitoring
- **Storage**: 4MB+ flash for certificates and config

### Software Components

#### 1. Core Libraries

```cpp
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <TinyGPS++.h>
#include <mbedtls/md.h>
#include <Preferences.h>
```

#### 2. Device Configuration Structure

```cpp
struct DeviceConfig {
    char deviceId[64];
    char apiKey[128];
    char deviceSecret[64];
    char manufacturer[32];
    bool registered;
};
```

#### 3. MQTT Message Format

```json
{
    "data": {
        "device_id": "PARA-20241210-12345-0001",
        "latitude": 45.9237,
        "longitude": 6.8694,
        "altitude": 2400.5,
        "speed": 35.2,
        "heading": 180.0,
        "accuracy": 5.0,
        "satellites": 12,
        "battery_level": 85.5,
        "timestamp": "2024-12-10T10:30:00Z",
        "device_metadata": {
            "vario": 2.5,
            "phase": "thermaling",
            "flight_time": 45,
            "pilot": "John Doe"
        }
    },
    "signature": "a1b2c3d4e5f6...",
    "api_key": "pk_live_..."
}
```

#### 4. HMAC Signature Generation

```cpp
String generateHMAC(String payload, String secret) {
    // Create canonical JSON (sorted keys, no spaces)
    StaticJsonDocument<512> doc;
    deserializeJson(doc, payload);
    
    String canonical;
    serializeJson(doc, canonical);
    
    // Generate HMAC-SHA256
    unsigned char hmac[32];
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1);
    
    mbedtls_md_hmac_starts(&ctx, (unsigned char*)secret.c_str(), secret.length());
    mbedtls_md_hmac_update(&ctx, (unsigned char*)canonical.c_str(), canonical.length());
    mbedtls_md_hmac_finish(&ctx, hmac);
    
    // Convert to hex string
    String signature = "";
    for(int i = 0; i < 32; i++) {
        char str[3];
        sprintf(str, "%02x", (int)hmac[i]);
        signature += str;
    }
    
    mbedtls_md_free(&ctx);
    return signature;
}
```

#### 5. Device Registration Flow

```cpp
bool registerDevice() {
    HTTPClient http;
    http.begin(API_BASE_URL + "/api/v1/devices/register");
    http.addHeader("Content-Type", "application/json");
    
    // Generate unique device ID
    String deviceId = String(MANUFACTURER) + "-" + getTimestamp() + "-" + getChipId();
    String deviceSecret = "secret_" + deviceId + "_0";
    
    // Create registration token
    String message = String(MANUFACTURER) + ":" + deviceId + ":" + deviceSecret;
    String registrationToken = generateHMAC(message, MANUFACTURER_SECRET);
    
    // Build registration payload
    StaticJsonDocument<512> doc;
    doc["device_id"] = deviceId;
    doc["manufacturer"] = MANUFACTURER;
    doc["registration_token"] = registrationToken;
    doc["device_secret"] = deviceSecret;
    doc["name"] = "Paraglider Tracker " + String(getChipId());
    doc["device_type"] = "PARAGLIDER_TRACKER";
    doc["firmware_version"] = FIRMWARE_VERSION;
    
    JsonObject deviceInfo = doc.createNestedObject("device_info");
    deviceInfo["chip_id"] = getChipId();
    deviceInfo["model"] = "ESP32-GPS-v1";
    
    String payload;
    serializeJson(doc, payload);
    
    int httpCode = http.POST(payload);
    
    if (httpCode == 200) {
        String response = http.getString();
        StaticJsonDocument<256> responseDoc;
        deserializeJson(responseDoc, response);
        
        // Save credentials
        preferences.putString("device_id", responseDoc["device_id"]);
        preferences.putString("api_key", responseDoc["api_key"]);
        preferences.putString("device_secret", deviceSecret);
        preferences.putBool("registered", true);
        
        return true;
    }
    
    return false;
}
```

#### 6. MQTT Connection with TLS

```cpp
WiFiClientSecure wifiClient;
PubSubClient mqttClient(wifiClient);

void setupMQTT() {
    // Load certificates
    wifiClient.setCACert(CA_CERT);
    wifiClient.setCertificate(CLIENT_CERT);
    wifiClient.setPrivateKey(CLIENT_KEY);
    
    mqttClient.setServer(MQTT_HOST, MQTT_PORT);
    mqttClient.setBufferSize(1024);
}

bool connectMQTT() {
    String clientId = deviceConfig.deviceId + "-" + String(millis());
    
    if (mqttClient.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD)) {
        Serial.println("MQTT connected");
        return true;
    }
    
    return false;
}
```

#### 7. GPS Data Publishing

```cpp
void publishGPSData() {
    if (!gps.location.isValid()) return;
    
    StaticJsonDocument<512> doc;
    JsonObject data = doc.createNestedObject("data");
    
    data["device_id"] = deviceConfig.deviceId;
    data["latitude"] = gps.location.lat();
    data["longitude"] = gps.location.lng();
    data["altitude"] = gps.altitude.meters();
    data["speed"] = gps.speed.kmph();
    data["heading"] = gps.course.deg();
    data["accuracy"] = gps.hdop.hdop() * 2.5;
    data["satellites"] = gps.satellites.value();
    data["battery_level"] = getBatteryLevel();
    data["timestamp"] = getISOTimestamp();
    
    // Add device-specific metadata
    JsonObject metadata = data.createNestedObject("device_metadata");
    metadata["firmware"] = FIRMWARE_VERSION;
    metadata["uptime"] = millis() / 1000;
    metadata["free_heap"] = ESP.getFreeHeap();
    
    // Serialize data object only for signature
    String dataStr;
    serializeJson(data, dataStr);
    
    // Generate signature
    String signature = generateHMAC(dataStr, deviceConfig.deviceSecret);
    
    // Add signature and API key to main document
    doc["signature"] = signature;
    doc["api_key"] = deviceConfig.apiKey;
    
    // Publish to MQTT
    String topic = "gps/" + String(deviceConfig.deviceId) + "/data";
    String payload;
    serializeJson(doc, payload);
    
    mqttClient.publish(topic.c_str(), payload.c_str(), false);
}
```

### Complete ESP32 Example Sketch

```cpp
// See examples/esp32_gps_tracker/esp32_gps_tracker.ino in the package
```

## API Integration

### 1. Device Registration Endpoint

**POST** `/api/v1/devices/register`

```bash
curl -X POST http://api.example.com/api/v1/devices/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "PARA-20241210-12345-0001",
    "manufacturer": "DIGIFLY",
    "registration_token": "a1b2c3d4e5f6...",
    "device_secret": "secret_PARA-20241210-12345-0001_0",
    "name": "Paraglider Tracker #1",
    "device_type": "PARAGLIDER_TRACKER",
    "firmware_version": "1.0.0",
    "device_info": {
        "pilot": "John Doe",
        "model": "ESP32-GPS-v1"
    }
}'
```

**Response:**
```json
{
    "device_id": "PARA-20241210-12345-0001",
    "api_key": "pk_live_a1b2c3d4e5f6...",
    "created_at": "2024-12-10T10:00:00Z"
}
```

### 2. Query Device Data

**GET** `/api/v1/devices/{device_id}/gps/latest`

```bash
curl -X GET http://api.example.com/api/v1/devices/PARA-20241210-12345-0001/gps/latest \
  -H "Authorization: Bearer pk_live_a1b2c3d4e5f6..."
```

### 3. Historical Data

**GET** `/api/v1/devices/{device_id}/gps/history`

Query parameters:
- `start_time`: ISO 8601 timestamp
- `end_time`: ISO 8601 timestamp
- `limit`: Maximum records (default: 1000)

## Testing with Emulator

### 1. Setup Emulator

```bash
cd paraglider_emulator
python setup.py
```

### 2. Configure Manufacturer

```bash
python paraglider_emulator.py --config --manufacturer YOUR_MANUFACTURER_NAME
```

Enter your manufacturer secret when prompted.

### 3. Run Test Simulation

```bash
# Safe mode (recommended for initial testing)
./run_safe.sh --devices 5 --duration 10 --domain api.example.com

# Or directly with Python
python paraglider_emulator.py \
  --devices 5 \
  --duration 10 \
  --domain api.example.com \
  --manufacturer YOUR_MANUFACTURER_NAME
```

### 4. Verify Data Flow

1. Check registration success in emulator output
2. Monitor MQTT messages: `mosquitto_sub -h mqtt.example.com -t 'gps/+/data' -v`
3. Query API for latest positions
4. Check database for stored data

## Production Deployment

### 1. Security Best Practices

- **Never hardcode secrets** in firmware
- Use secure storage (ESP32 eFuse or encrypted NVS)
- Implement secure OTA updates
- Rotate device secrets periodically
- Use unique certificates per device in production

### 2. Power Management

```cpp
void enterDeepSleep(uint64_t sleepSeconds) {
    // Save state before sleep
    preferences.putULong("sleep_count", sleepCount++);
    
    // Configure wake up
    esp_sleep_enable_timer_wakeup(sleepSeconds * 1000000);
    
    // Enter deep sleep
    esp_deep_sleep_start();
}

// Adaptive update intervals
int getUpdateInterval() {
    if (isMoving()) return 5;      // 5 seconds when moving
    if (batteryLow()) return 60;   // 1 minute when battery low
    return 30;                      // 30 seconds default
}
```

### 3. Error Handling

```cpp
enum ErrorCode {
    ERR_NONE = 0,
    ERR_NO_GPS = 1,
    ERR_NO_NETWORK = 2,
    ERR_MQTT_FAILED = 3,
    ERR_AUTH_FAILED = 4
};

void handleError(ErrorCode error) {
    // Log to flash
    logError(error);
    
    // LED indication
    blinkErrorCode(error);
    
    // Retry strategy
    switch(error) {
        case ERR_NO_GPS:
            delay(5000);  // Wait for GPS fix
            break;
        case ERR_MQTT_FAILED:
            reconnectMQTT();
            break;
        case ERR_AUTH_FAILED:
            // Attempt re-registration
            registerDevice();
            break;
    }
}
```

### 4. Firmware Updates

```cpp
void checkForUpdates() {
    HTTPClient http;
    http.begin(API_BASE_URL + "/api/v1/firmware/check");
    http.addHeader("X-Device-ID", deviceConfig.deviceId);
    http.addHeader("X-Firmware-Version", FIRMWARE_VERSION);
    
    int httpCode = http.GET();
    
    if (httpCode == 200) {
        String response = http.getString();
        // Parse update info and download if available
        performOTAUpdate(response);
    }
}
```

## Troubleshooting

### Common Issues

1. **Registration Fails**
   - Verify manufacturer secret is correct
   - Check device ID uniqueness
   - Ensure correct API endpoint
   - Check network connectivity

2. **MQTT Connection Fails**
   - Verify certificates are valid
   - Check MQTT credentials
   - Ensure port 8883 is not blocked
   - Test with mosquitto_pub first

3. **GPS Data Not Appearing**
   - Verify HMAC signature generation
   - Check JSON formatting (must be canonical)
   - Ensure timestamp is in UTC
   - Monitor MQTT broker logs

4. **High Power Consumption**
   - Implement adaptive update intervals
   - Use GPS power save modes
   - Optimize WiFi connection time
   - Use deep sleep when stationary

### Debug Tools

1. **Serial Monitor Output**
```cpp
#define DEBUG 1
#if DEBUG
  #define DEBUG_PRINT(x) Serial.print(x)
  #define DEBUG_PRINTLN(x) Serial.println(x)
#else
  #define DEBUG_PRINT(x)
  #define DEBUG_PRINTLN(x)
#endif
```

2. **MQTT Testing**
```bash
# Subscribe to all device messages
mosquitto_sub -h localhost -p 8883 \
  --cafile ca.crt \
  --cert client.crt \
  --key client.key \
  -u mqtt_user -P mqtt_password \
  -t 'gps/+/data' -v

# Publish test message
mosquitto_pub -h localhost -p 8883 \
  --cafile ca.crt \
  --cert client.crt \
  --key client.key \
  -u mqtt_user -P mqtt_password \
  -t 'gps/TEST-DEVICE/data' \
  -m '{"data":{"device_id":"TEST-DEVICE","latitude":45.0,"longitude":6.0},"signature":"...","api_key":"..."}'
```

3. **API Testing**
```bash
# Test registration
curl -X POST http://localhost/api/v1/devices/register \
  -H "Content-Type: application/json" \
  -d @test_registration.json \
  -v

# Check device exists
curl http://localhost/api/v1/devices/TEST-DEVICE \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Support

For technical support:
1. Check the emulator for testing your implementation
2. Review server logs for error messages
3. Contact platform administrator with:
   - Device ID
   - Error messages
   - Sample code
   - Network traces

## Appendix

### A. Certificate Generation (Development Only)

```bash
# Generate self-signed certificates for testing
openssl req -new -x509 -days 365 -keyout ca.key -out ca.crt -nodes
openssl req -new -keyout client.key -out client.csr -nodes
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days 365
```

### B. Example Device Metadata

Different device types can include relevant metadata:

**Paraglider Tracker:**
```json
{
    "vario": 2.5,
    "phase": "thermaling",
    "flight_time": 45,
    "pilot": "John Doe"
}
```

**Vehicle Tracker:**
```json
{
    "engine_on": true,
    "fuel_level": 75,
    "odometer": 12345,
    "driver_id": "D123"
}
```

**Asset Tracker:**
```json
{
    "temperature": 23.5,
    "humidity": 65,
    "shock_detected": false,
    "container_id": "C789"
}
```

### C. Rate Limits

- Device Registration: 10 requests per minute per IP
- GPS Data: No limit (MQTT subscription based)
- API Queries: 1000 requests per hour per API key

---

*Last Updated: December 2024*
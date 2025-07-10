/*
 * ESP32 GPS Tracker for Paraglider Platform
 * 
 * This example demonstrates how to build a GPS tracking device
 * that integrates with the platform using MQTT over TLS.
 * 
 * Required Libraries:
 * - WiFi (built-in)
 * - WiFiClientSecure (built-in)  
 * - PubSubClient by Nick O'Leary
 * - ArduinoJson by Benoit Blanchon
 * - TinyGPSPlus by Mikal Hart
 * - Preferences (built-in)
 * 
 * Hardware:
 * - ESP32 DevKit
 * - GPS Module (Neo-6M/7M/8M)
 * - Battery with voltage divider on ADC pin
 * 
 * Connections:
 * - GPS TX -> ESP32 RX2 (GPIO 16)
 * - GPS RX -> ESP32 TX2 (GPIO 17)
 * - Battery voltage divider -> GPIO 34 (ADC)
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <TinyGPSPlus.h>
#include <Preferences.h>
#include "mbedtls/md.h"
#include <time.h>

// ===== CONFIGURATION =====
// Update these values for your deployment
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

const char* MANUFACTURER = "DIGIFLY";
const char* MANUFACTURER_SECRET = "YOUR_MANUFACTURER_SECRET_HERE";

const char* API_BASE_URL = "http://your-server.com";
const char* MQTT_HOST = "your-server.com";
const int MQTT_PORT = 8883;
const char* MQTT_USER = "mqtt_user";
const char* MQTT_PASSWORD = "mqtt_secure_password";

const char* FIRMWARE_VERSION = "1.0.0";

// GPS Configuration
#define GPS_BAUD 9600
#define GPS_RX 16
#define GPS_TX 17

// Battery monitoring
#define BATTERY_PIN 34
#define BATTERY_MAX_VOLTAGE 4.2
#define BATTERY_MIN_VOLTAGE 3.0

// Update intervals (seconds)
#define UPDATE_INTERVAL_MOVING 5
#define UPDATE_INTERVAL_STATIONARY 30
#define UPDATE_INTERVAL_LOW_BATTERY 60

// ===== CERTIFICATES =====
// For production, store these in encrypted NVS or external secure element
const char* CA_CERT = R"EOF(
-----BEGIN CERTIFICATE-----
# Paste your CA certificate here
-----END CERTIFICATE-----
)EOF";

const char* CLIENT_CERT = R"EOF(
-----BEGIN CERTIFICATE-----
# Paste your client certificate here
-----END CERTIFICATE-----
)EOF";

const char* CLIENT_KEY = R"EOF(
-----BEGIN RSA PRIVATE KEY-----
# Paste your client key here
-----END RSA PRIVATE KEY-----
)EOF";

// ===== GLOBAL OBJECTS =====
WiFiClientSecure wifiClient;
PubSubClient mqttClient(wifiClient);
TinyGPSPlus gps;
HardwareSerial GPS_Serial(2);
Preferences preferences;

// Device configuration
struct {
    char deviceId[64];
    char apiKey[128];
    char deviceSecret[64];
    bool registered;
} deviceConfig;

// State tracking
unsigned long lastUpdate = 0;
unsigned long lastGPSCheck = 0;
int updateInterval = UPDATE_INTERVAL_STATIONARY;
float lastLat = 0;
float lastLng = 0;
bool isMoving = false;

// ===== HELPER FUNCTIONS =====

String getChipId() {
    uint64_t chipid = ESP.getEfuseMac();
    char chipIdStr[13];
    sprintf(chipIdStr, "%04X%08X", (uint16_t)(chipid>>32), (uint32_t)chipid);
    return String(chipIdStr);
}

String getTimestamp() {
    time_t now;
    time(&now);
    char buf[21];
    strftime(buf, sizeof(buf), "%Y%m%d%H%M%S", gmtime(&now));
    return String(buf);
}

String getISOTimestamp() {
    time_t now;
    time(&now);
    char buf[21];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", gmtime(&now));
    return String(buf);
}

float getBatteryLevel() {
    int adcValue = analogRead(BATTERY_PIN);
    float voltage = (adcValue / 4095.0) * 3.3 * 2; // Assuming 2:1 voltage divider
    float percentage = ((voltage - BATTERY_MIN_VOLTAGE) / (BATTERY_MAX_VOLTAGE - BATTERY_MIN_VOLTAGE)) * 100;
    return constrain(percentage, 0, 100);
}

String generateHMAC(const String& payload, const String& secret) {
    unsigned char hmac[32];
    
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1);
    
    mbedtls_md_hmac_starts(&ctx, (unsigned char*)secret.c_str(), secret.length());
    mbedtls_md_hmac_update(&ctx, (unsigned char*)payload.c_str(), payload.length());
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

// ===== DEVICE REGISTRATION =====

bool registerDevice() {
    HTTPClient http;
    
    String url = String(API_BASE_URL) + "/api/v1/devices/register";
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    
    // Generate device ID
    String deviceId = String("PARA-") + getTimestamp() + "-" + getChipId();
    String deviceSecret = "secret_" + deviceId + "_0";
    
    // Create registration token
    String message = String(MANUFACTURER) + ":" + deviceId + ":" + deviceSecret;
    String registrationToken = generateHMAC(message, String(MANUFACTURER_SECRET));
    
    // Build registration payload
    StaticJsonDocument<768> doc;
    doc["device_id"] = deviceId;
    doc["manufacturer"] = MANUFACTURER;
    doc["registration_token"] = registrationToken;
    doc["device_secret"] = deviceSecret;
    doc["name"] = "ESP32 Tracker " + getChipId();
    doc["device_type"] = "PARAGLIDER_TRACKER";
    doc["firmware_version"] = FIRMWARE_VERSION;
    
    JsonObject deviceInfo = doc.createNestedObject("device_info");
    deviceInfo["chip_id"] = getChipId();
    deviceInfo["model"] = "ESP32-GPS-v1";
    deviceInfo["wifi_mac"] = WiFi.macAddress();
    
    String payload;
    serializeJson(doc, payload);
    
    Serial.println("Registering device...");
    Serial.println("Payload: " + payload);
    
    int httpCode = http.POST(payload);
    
    if (httpCode == 200) {
        String response = http.getString();
        Serial.println("Registration successful!");
        Serial.println("Response: " + response);
        
        StaticJsonDocument<512> responseDoc;
        DeserializationError error = deserializeJson(responseDoc, response);
        
        if (!error) {
            // Save credentials
            strcpy(deviceConfig.deviceId, responseDoc["device_id"]);
            strcpy(deviceConfig.apiKey, responseDoc["api_key"]);
            strcpy(deviceConfig.deviceSecret, deviceSecret.c_str());
            deviceConfig.registered = true;
            
            // Persist to NVS
            preferences.putString("device_id", deviceConfig.deviceId);
            preferences.putString("api_key", deviceConfig.apiKey);
            preferences.putString("device_secret", deviceConfig.deviceSecret);
            preferences.putBool("registered", true);
            
            http.end();
            return true;
        }
    } else {
        Serial.printf("Registration failed. HTTP code: %d\n", httpCode);
        Serial.println("Response: " + http.getString());
    }
    
    http.end();
    return false;
}

// ===== MQTT FUNCTIONS =====

void setupMQTT() {
    wifiClient.setCACert(CA_CERT);
    wifiClient.setCertificate(CLIENT_CERT);
    wifiClient.setPrivateKey(CLIENT_KEY);
    
    mqttClient.setServer(MQTT_HOST, MQTT_PORT);
    mqttClient.setBufferSize(1024);
}

bool connectMQTT() {
    if (mqttClient.connected()) {
        return true;
    }
    
    String clientId = String(deviceConfig.deviceId) + "-" + String(millis());
    
    Serial.print("Connecting to MQTT broker...");
    
    if (mqttClient.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD)) {
        Serial.println(" connected!");
        return true;
    } else {
        Serial.print(" failed, rc=");
        Serial.println(mqttClient.state());
        return false;
    }
}

void publishGPSData() {
    if (!gps.location.isValid()) {
        Serial.println("No valid GPS data");
        return;
    }
    
    // Check if device is moving
    float distance = TinyGPSPlus::distanceBetween(
        lastLat, lastLng,
        gps.location.lat(), gps.location.lng()
    );
    
    isMoving = (distance > 5); // Moving if more than 5 meters
    
    // Update last position
    lastLat = gps.location.lat();
    lastLng = gps.location.lng();
    
    // Build GPS data message
    StaticJsonDocument<768> doc;
    JsonObject data = doc.createNestedObject("data");
    
    data["device_id"] = deviceConfig.deviceId;
    data["latitude"] = serialized(String(gps.location.lat(), 6));
    data["longitude"] = serialized(String(gps.location.lng(), 6));
    data["altitude"] = gps.altitude.meters();
    data["speed"] = gps.speed.kmph();
    data["heading"] = gps.course.deg();
    data["accuracy"] = gps.hdop.hdop() * 2.5;
    data["satellites"] = gps.satellites.value();
    data["battery_level"] = getBatteryLevel();
    data["timestamp"] = getISOTimestamp();
    
    // Add metadata
    JsonObject metadata = data.createNestedObject("device_metadata");
    metadata["firmware"] = FIRMWARE_VERSION;
    metadata["uptime"] = millis() / 1000;
    metadata["free_heap"] = ESP.getFreeHeap();
    metadata["moving"] = isMoving;
    metadata["rssi"] = WiFi.RSSI();
    
    // Create canonical JSON for signature
    String dataStr;
    serializeJson(data, dataStr);
    
    // Generate HMAC signature
    String signature = generateHMAC(dataStr, String(deviceConfig.deviceSecret));
    
    // Add signature and API key
    doc["signature"] = signature;
    doc["api_key"] = deviceConfig.apiKey;
    
    // Publish to MQTT
    String topic = "gps/" + String(deviceConfig.deviceId) + "/data";
    String payload;
    serializeJson(doc, payload);
    
    if (mqttClient.publish(topic.c_str(), payload.c_str(), false)) {
        Serial.println("GPS data published successfully");
        Serial.printf("Position: %.6f, %.6f, Alt: %.1fm, Sats: %d\n",
            gps.location.lat(), gps.location.lng(),
            gps.altitude.meters(), gps.satellites.value());
    } else {
        Serial.println("Failed to publish GPS data");
    }
}

// ===== SETUP =====

void setup() {
    Serial.begin(115200);
    Serial.println("\n\nESP32 GPS Tracker Starting...");
    
    // Initialize GPS
    GPS_Serial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX, GPS_TX);
    Serial.println("GPS initialized");
    
    // Initialize preferences
    preferences.begin("gps-tracker", false);
    
    // Load saved configuration
    deviceConfig.registered = preferences.getBool("registered", false);
    if (deviceConfig.registered) {
        preferences.getString("device_id", deviceConfig.deviceId, sizeof(deviceConfig.deviceId));
        preferences.getString("api_key", deviceConfig.apiKey, sizeof(deviceConfig.apiKey));
        preferences.getString("device_secret", deviceConfig.deviceSecret, sizeof(deviceConfig.deviceSecret));
        Serial.println("Loaded saved device configuration");
        Serial.printf("Device ID: %s\n", deviceConfig.deviceId);
    }
    
    // Connect to WiFi
    Serial.printf("Connecting to WiFi: %s", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi connected!");
    Serial.printf("IP address: %s\n", WiFi.localIP().toString().c_str());
    
    // Sync time
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    Serial.print("Syncing time");
    time_t now = time(nullptr);
    while (now < 24 * 3600) {
        Serial.print(".");
        delay(500);
        now = time(nullptr);
    }
    Serial.println(" done!");
    
    // Register device if needed
    if (!deviceConfig.registered) {
        if (!registerDevice()) {
            Serial.println("Failed to register device. Restarting in 30 seconds...");
            delay(30000);
            ESP.restart();
        }
    }
    
    // Setup MQTT
    setupMQTT();
    
    // Battery monitoring
    analogReadResolution(12);
    pinMode(BATTERY_PIN, INPUT);
    
    Serial.println("Setup complete! Starting GPS tracking...");
}

// ===== MAIN LOOP =====

void loop() {
    // Feed GPS data
    while (GPS_Serial.available() > 0) {
        gps.encode(GPS_Serial.read());
    }
    
    // Check GPS status every second
    if (millis() - lastGPSCheck > 1000) {
        lastGPSCheck = millis();
        
        if (gps.location.isValid()) {
            digitalWrite(LED_BUILTIN, HIGH);
        } else {
            digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN)); // Blink when no fix
        }
        
        // Print GPS stats
        if (gps.charsProcessed() < 10) {
            Serial.println("WARNING: No GPS data received. Check wiring!");
        }
    }
    
    // Update interval based on movement and battery
    float battery = getBatteryLevel();
    if (battery < 20) {
        updateInterval = UPDATE_INTERVAL_LOW_BATTERY;
    } else if (isMoving) {
        updateInterval = UPDATE_INTERVAL_MOVING;
    } else {
        updateInterval = UPDATE_INTERVAL_STATIONARY;
    }
    
    // Publish GPS data at configured interval
    if (millis() - lastUpdate > updateInterval * 1000) {
        lastUpdate = millis();
        
        // Ensure WiFi is connected
        if (WiFi.status() != WL_CONNECTED) {
            Serial.println("WiFi disconnected. Reconnecting...");
            WiFi.reconnect();
            delay(5000);
            return;
        }
        
        // Ensure MQTT is connected
        if (!connectMQTT()) {
            Serial.println("MQTT connection failed. Will retry next cycle.");
            return;
        }
        
        // Publish GPS data
        publishGPSData();
    }
    
    // Maintain MQTT connection
    mqttClient.loop();
    
    // Yield to watchdog
    yield();
}

// ===== ERROR HANDLING =====

void handleError(int errorCode) {
    Serial.printf("Error %d occurred\n", errorCode);
    
    // Log to NVS
    preferences.putInt("last_error", errorCode);
    preferences.putULong("error_time", millis());
    
    // Visual indication (if LED available)
    for (int i = 0; i < errorCode; i++) {
        digitalWrite(LED_BUILTIN, HIGH);
        delay(200);
        digitalWrite(LED_BUILTIN, LOW);
        delay(200);
    }
    
    // Recovery action based on error
    switch(errorCode) {
        case 1: // No GPS
            // Just wait, GPS might need time
            break;
        case 2: // No Network
            WiFi.reconnect();
            break;
        case 3: // MQTT Failed
            mqttClient.disconnect();
            delay(1000);
            connectMQTT();
            break;
        case 4: // Auth Failed
            // Try re-registration
            deviceConfig.registered = false;
            preferences.putBool("registered", false);
            break;
    }
}
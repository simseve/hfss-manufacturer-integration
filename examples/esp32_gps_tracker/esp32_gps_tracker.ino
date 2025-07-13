/**
 * ESP32 GPS Tracker for HFSS-DIGI Platform
 * 
 * This example demonstrates how to integrate an ESP32-based GPS tracker
 * with the HFSS-DIGI tracking platform using secure MQTT over TLS.
 * 
 * Required Libraries:
 * - WiFi (built-in)
 * - PubSubClient by Nick O'Leary
 * - ArduinoJson by Benoit Blanchon
 * - TinyGPSPlus by Mikal Hart
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <TinyGPSPlus.h>
#include <HTTPClient.h>
#include <mbedtls/md.h>
#include <time.h>

// Configuration
#define WIFI_SSID "your-wifi-ssid"
#define WIFI_PASSWORD "your-wifi-password"
#define API_DOMAIN "your-domain.com"
#define API_BASE_URL "https://your-domain.com"
#define MQTT_PORT 8883

// Factory provisioned values (DO NOT HARDCODE IN PRODUCTION)
#define MANUFACTURER_ID "DIGIFLY"
#define DEVICE_ID "PARA-20250711-TEST-0001"
#define DEVICE_SECRET "your-device-secret-from-factory"
#define REGISTRATION_TOKEN "your-registration-token"

// GPS Serial (adjust pins for your board)
#define GPS_RX_PIN 16
#define GPS_TX_PIN 17
#define GPS_BAUD 9600

// Global objects
WiFiClientSecure wifiClient;
PubSubClient mqttClient(wifiClient);
Preferences preferences;
TinyGPSPlus gps;
HardwareSerial gpsSerial(1);

// State variables
bool deviceRegistered = false;
unsigned long lastGPSUpdate = 0;
unsigned long lastMQTTReconnect = 0;
int mqttReconnectDelay = 1000;

// Function declarations
void setupWiFi();
bool registerDevice();
bool downloadCACert();
void setupMQTT();
bool connectMQTT();
void sendGPSData();
String generateHMAC(const String& data);
String getISO8601Time();
void mqttCallback(char* topic, byte* payload, unsigned int length);
float getBatteryLevel();
bool isDeviceMoving();

void setup() {
    Serial.begin(115200);
    Serial.println("ESP32 GPS Tracker Starting...");
    
    // Initialize GPS
    gpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
    Serial.println("GPS initialized");
    
    // Initialize secure storage
    preferences.begin("gps-tracker", false);
    
    // Connect to WiFi
    setupWiFi();
    
    // Check if device is already registered
    deviceRegistered = preferences.getBool("registered", false);
    
    if (!deviceRegistered) {
        Serial.println("Device not registered. Starting registration...");
        if (registerDevice()) {
            deviceRegistered = true;
            preferences.putBool("registered", true);
        } else {
            Serial.println("Registration failed! Restarting in 30 seconds...");
            delay(30000);
            ESP.restart();
        }
    }
    
    // Download CA certificate if not present
    if (!preferences.isKey("ca_cert")) {
        downloadCACert();
    }
    
    // Setup MQTT
    setupMQTT();
    
    // Sync time for accurate timestamps
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
}

void loop() {
    // Feed GPS data
    while (gpsSerial.available() > 0) {
        gps.encode(gpsSerial.read());
    }
    
    // Maintain MQTT connection
    if (!mqttClient.connected()) {
        unsigned long now = millis();
        if (now - lastMQTTReconnect > mqttReconnectDelay) {
            if (connectMQTT()) {
                mqttReconnectDelay = 1000; // Reset delay on success
            } else {
                mqttReconnectDelay = min(mqttReconnectDelay * 2, 60000); // Max 1 minute
            }
            lastMQTTReconnect = now;
        }
    } else {
        mqttClient.loop();
    }
    
    // Send GPS updates
    unsigned long updateInterval = isDeviceMoving() ? 1000 : 30000; // 1s moving, 30s stationary
    
    if (millis() - lastGPSUpdate > updateInterval) {
        if (gps.location.isValid() && mqttClient.connected()) {
            sendGPSData();
            lastGPSUpdate = millis();
        }
    }
}

void setupWiFi() {
    Serial.print("Connecting to WiFi");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    
    Serial.println("\nWiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
}

bool registerDevice() {
    HTTPClient http;
    http.begin(String(API_BASE_URL) + "/api/v1/devices/register");
    http.addHeader("Content-Type", "application/json");
    
    // Create registration payload
    StaticJsonDocument<512> doc;
    doc["device_id"] = DEVICE_ID;
    doc["manufacturer"] = MANUFACTURER_ID;
    doc["registration_token"] = REGISTRATION_TOKEN;
    doc["device_secret"] = DEVICE_SECRET;
    doc["device_type"] = "PARAGLIDER_TRACKER";
    doc["firmware_version"] = "1.0.0";
    
    JsonObject device_info = doc.createNestedObject("device_info");
    device_info["model"] = "ESP32-GPS-v1";
    device_info["chip_id"] = String((uint32_t)ESP.getEfuseMac(), HEX);
    
    String payload;
    serializeJson(doc, payload);
    
    Serial.println("Sending registration request...");
    int httpCode = http.POST(payload);
    
    if (httpCode == 200) {
        String response = http.getString();
        StaticJsonDocument<512> responseDoc;
        DeserializationError error = deserializeJson(responseDoc, response);
        
        if (!error) {
            // Store credentials
            preferences.putString("api_key", responseDoc["api_key"]);
            preferences.putString("mqtt_user", responseDoc["mqtt_username"]);
            preferences.putString("mqtt_pass", responseDoc["mqtt_password"]);
            preferences.putString("device_secret", DEVICE_SECRET);
            
            Serial.println("Registration successful!");
            Serial.print("MQTT Username: ");
            Serial.println(responseDoc["mqtt_username"].as<String>());
            
            http.end();
            return true;
        }
    }
    
    Serial.print("Registration failed. HTTP code: ");
    Serial.println(httpCode);
    http.end();
    return false;
}

bool downloadCACert() {
    HTTPClient http;
    http.begin(String(API_BASE_URL) + "/ca.crt");
    
    int httpCode = http.GET();
    if (httpCode == 200) {
        String cert = http.getString();
        preferences.putString("ca_cert", cert);
        Serial.println("CA certificate downloaded and stored");
        http.end();
        return true;
    }
    
    Serial.print("Failed to download CA cert. HTTP code: ");
    Serial.println(httpCode);
    http.end();
    return false;
}

void setupMQTT() {
    // Load and set CA certificate
    String caCert = preferences.getString("ca_cert");
    wifiClient.setCACert(caCert.c_str());
    
    // Configure MQTT
    mqttClient.setServer(API_DOMAIN, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
    mqttClient.setBufferSize(1024); // Increase buffer for GPS messages
    
    // Initial connection
    connectMQTT();
}

bool connectMQTT() {
    String clientId = "esp32-" + String(DEVICE_ID);
    String username = preferences.getString("mqtt_user");
    String password = preferences.getString("mqtt_pass");
    
    Serial.print("Connecting to MQTT broker...");
    
    if (mqttClient.connect(clientId.c_str(), username.c_str(), password.c_str())) {
        Serial.println(" connected!");
        
        // Subscribe to command topic
        String cmdTopic = "devices/" + String(DEVICE_ID) + "/command";
        mqttClient.subscribe(cmdTopic.c_str());
        Serial.print("Subscribed to: ");
        Serial.println(cmdTopic);
        
        return true;
    }
    
    Serial.print(" failed, rc=");
    Serial.println(mqttClient.state());
    return false;
}

void sendGPSData() {
    // Create GPS data object
    StaticJsonDocument<512> gpsDoc;
    gpsDoc["device_id"] = DEVICE_ID;
    gpsDoc["timestamp"] = getISO8601Time();
    gpsDoc["latitude"] = gps.location.lat();
    gpsDoc["longitude"] = gps.location.lng();
    gpsDoc["altitude"] = gps.altitude.meters();
    gpsDoc["speed"] = gps.speed.kmph();
    gpsDoc["heading"] = gps.course.deg();
    gpsDoc["accuracy"] = gps.hdop.hdop();
    gpsDoc["satellites"] = gps.satellites.value();
    gpsDoc["battery_level"] = getBatteryLevel();
    
    // Add metadata
    JsonObject metadata = gpsDoc.createNestedObject("device_metadata");
    metadata["fix_type"] = gps.location.isValid() ? "3D" : "No Fix";
    metadata["hdop"] = gps.hdop.hdop();
    
    // Serialize for signing (sorted keys)
    String canonicalJson;
    serializeJsonSorted(gpsDoc, canonicalJson);
    
    // Generate signature
    String signature = generateHMAC(canonicalJson);
    
    // Create final message
    StaticJsonDocument<768> message;
    message["data"] = gpsDoc;
    message["signature"] = signature;
    message["api_key"] = preferences.getString("api_key");
    
    // Publish
    String payload;
    serializeJson(message, payload);
    
    String topic = "gps/" + String(DEVICE_ID) + "/data";
    
    if (mqttClient.publish(topic.c_str(), payload.c_str())) {
        Serial.print("GPS data sent: ");
        Serial.print(gps.location.lat(), 6);
        Serial.print(", ");
        Serial.println(gps.location.lng(), 6);
    } else {
        Serial.println("Failed to send GPS data");
    }
}

String generateHMAC(const String& data) {
    String secret = preferences.getString("device_secret");
    
    unsigned char hmacResult[32];
    mbedtls_md_context_t ctx;
    mbedtls_md_type_t md_type = MBEDTLS_MD_SHA256;
    
    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(md_type), 1);
    mbedtls_md_hmac_starts(&ctx, (unsigned char*)secret.c_str(), secret.length());
    mbedtls_md_hmac_update(&ctx, (unsigned char*)data.c_str(), data.length());
    mbedtls_md_hmac_finish(&ctx, hmacResult);
    mbedtls_md_free(&ctx);
    
    // Convert to hex
    String hmacHex = "";
    for (int i = 0; i < 32; i++) {
        char str[3];
        sprintf(str, "%02x", (int)hmacResult[i]);
        hmacHex += str;
    }
    
    return hmacHex;
}

String getISO8601Time() {
    struct tm timeinfo;
    if (!getLocalTime(&timeinfo)) {
        return "2025-01-01T00:00:00.000Z"; // Fallback
    }
    
    char buffer[30];
    strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S.000Z", &timeinfo);
    return String(buffer);
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    Serial.print("Message received [");
    Serial.print(topic);
    Serial.print("]: ");
    
    // Parse JSON command
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, payload, length);
    
    if (!error) {
        String command = doc["command"];
        Serial.println(command);
        
        // Handle commands
        if (command == "restart") {
            ESP.restart();
        } else if (command == "status") {
            // Send status update
            // Implementation depends on requirements
        }
    }
}

float getBatteryLevel() {
    // Example: Read battery voltage from ADC
    // Adjust for your hardware setup
    
    // For testing, return a simulated value
    static float battery = 100.0;
    battery -= 0.01; // Slow drain
    if (battery < 20) battery = 100; // Reset
    return battery;
}

bool isDeviceMoving() {
    static double lastLat = 0;
    static double lastLon = 0;
    
    if (!gps.location.isValid()) return false;
    
    double distance = TinyGPSPlus::distanceBetween(
        lastLat, lastLon,
        gps.location.lat(), gps.location.lng()
    );
    
    lastLat = gps.location.lat();
    lastLon = gps.location.lng();
    
    return distance > 5.0; // Moving if more than 5 meters
}
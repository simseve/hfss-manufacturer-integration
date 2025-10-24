# Critical Events API & MQTT Documentation

## Overview

The Critical Events system allows mobile apps and IoT devices to report safety-critical events (impacts, SOS, battery alerts, etc.) through both REST API and MQTT. All events are processed asynchronously through Redis Streams for reliability.

---

## REST API Endpoints

### Base URL
```
Production: https://dg-dev.hikeandfly.app/api/v1
Local: http://localhost/api/v1
```

### Authentication
All endpoints require JWT authentication via Bearer token:
```http
Authorization: Bearer <your_jwt_token>
```

---

## 1. Report Impact Alert

**Endpoint:** `POST /critical-event (RECOMMENDED) & /impact-alert (backward compatible)`

**Description:** Report an impact detection event from a mobile device accelerometer.

**Request Headers:**
```http
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "device_id": "SS_IOS_479AA038-2826-424A-A810-75887DE18309",
  "flight_id": "e6c4db96-470e-44d0-a06c-4e6231e112a4",
  "timestamp": "2025-10-24T19:00:00Z",
  "location": {
    "lat": 45.5017,
    "lon": -73.5673,
    "alt": 1500
  },
  "impact_magnitude": 15.2,
  "severity": "critical"
}
```

**Field Details:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_id` | string | ✅ Yes | Unique device identifier |
| `flight_id` | UUID | ❌ No | Optional flight session ID |
| `timestamp` | ISO 8601 | ✅ Yes | Time of impact detection (UTC) |
| `location.lat` | float | ✅ Yes | Latitude (-90 to 90) |
| `location.lon` | float | ✅ Yes | Longitude (-180 to 180) |
| `location.alt` | float | ❌ No | Altitude in meters |
| `impact_magnitude` | float | ✅ Yes | G-force magnitude (≥ 0) |
| `severity` | enum | ✅ Yes | `moderate`, `severe`, or `critical` |

**Response (202 Accepted):**
```json
{
  "status": "queued",
  "message": "Impact alert queued for processing (msg_id: 1761287699102-0)",
  "device_id": "SS_IOS_479AA038-2826-424A-A810-75887DE18309",
  "timestamp": "2025-10-24T19:00:00Z",
  "notifications_queued": 0,
  "contacts_notified": 0
}
```

**Status Code:** `202 Accepted` - Event queued successfully for async processing

**Error Responses:**

| Code | Description |
|------|-------------|
| `400` | Bad Request - Invalid data format |
| `401` | Unauthorized - Invalid or missing JWT token |
| `403` | Forbidden - Device not owned by user |
| `500` | Internal Server Error - Failed to queue event |

**Example cURL:**
```bash
curl -X POST https://dg-dev.hikeandfly.app/api/v1/impact-alert \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "device_id": "SS_IOS_12345",
    "timestamp": "2025-10-24T14:30:00Z",
    "location": {"lat": 45.5017, "lon": -73.5673, "alt": 1500},
    "impact_magnitude": 12.5,
    "severity": "severe"
  }'
```

**Example JavaScript (React Native):**
```javascript
const reportImpact = async (impactData) => {
  try {
    const response = await fetch('https://dg-dev.hikeandfly.app/api/v1/impact-alert', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`
      },
      body: JSON.stringify({
        device_id: deviceId,
        timestamp: new Date().toISOString(),
        location: {
          lat: currentLocation.latitude,
          lon: currentLocation.longitude,
          alt: currentLocation.altitude
        },
        impact_magnitude: gForce,
        severity: calculateSeverity(gForce)
      })
    });

    const result = await response.json();

    if (response.status === 202) {
      console.log('Impact reported successfully:', result.message);
      // Clear local storage after successful queue
      clearLocalImpactData();
    }
  } catch (error) {
    console.error('Failed to report impact:', error);
    // Store locally for retry
    storeImpactLocally(impactData);
  }
};

const calculateSeverity = (gForce) => {
  if (gForce >= 20) return 'critical';
  if (gForce >= 10) return 'severe';
  return 'moderate';
};
```

---

## 2. Admin: List Critical Events

**Endpoint:** `GET /admin/critical-events`

**Description:** List all critical events with filtering options (admin only).

**Request Headers:**
```http
Authorization: Bearer <admin_jwt_token>
```

**Query Parameters:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `skip` | int | Offset for pagination | `0` |
| `limit` | int | Max results (default: 50) | `50` |
| `event_type` | string | Filter by type | `impact`, `sos` |
| `severity` | string | Filter by severity | `critical`, `severe` |
| `is_resolved` | string | Filter by status | `pending`, `resolved` |
| `device_id` | string | Filter by device | `SS_IOS_12345` |
| `user_id` | UUID | Filter by user | `f5eb492a-...` |

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "f52436aa-c31e-422e-aa26-bb7e05b335b1",
      "device_id": "SS_IOS_479AA038-2826-424A-A810-75887DE18309",
      "user_id": "f5eb492a-3455-4e56-bd71-b8e5d7c9d001",
      "flight_id": "e6c4db96-470e-44d0-a06c-4e6231e112a4",
      "event_type": "impact",
      "severity": "critical",
      "timestamp": "2025-10-24T18:45:00Z",
      "latitude": 45.5017,
      "longitude": -73.5673,
      "altitude": 1500.0,
      "event_data": {
        "impact_magnitude": 15.2
      },
      "description": "CRITICAL impact detected: 15.2G",
      "is_resolved": "pending",
      "resolved_at": null,
      "resolved_by": null,
      "resolution_notes": null,
      "notifications_sent": [],
      "platform_notification_created": "yes",
      "created_at": "2025-10-24T06:34:59.316138Z",
      "updated_at": "2025-10-24T06:34:59.316138Z"
    }
  ],
  "total": 1,
  "unresolved_count": 1
}
```

**Example cURL:**
```bash
curl -X GET "https://dg-dev.hikeandfly.app/api/v1/admin/critical-events?severity=critical&is_resolved=pending" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

---

## 3. Admin: Get Event Statistics

**Endpoint:** `GET /admin/critical-events/stats/summary`

**Description:** Get aggregated statistics for critical events (admin only).

**Response (200 OK):**
```json
{
  "total_events": 10,
  "pending": 3,
  "severity_breakdown": {
    "info": 1,
    "moderate": 2,
    "severe": 4,
    "critical": 3
  },
  "type_breakdown": {
    "impact": 8,
    "sos": 1,
    "low_altitude": 0,
    "geofence": 0,
    "offline": 1,
    "battery": 0,
    "other": 0
  }
}
```

---

## 4. Admin: Update Event Resolution

**Endpoint:** `PATCH /admin/critical-events/{event_id}`

**Description:** Update the resolution status of a critical event (admin only).

**Request Body:**
```json
{
  "is_resolved": "acknowledged",
  "resolution_notes": "Team contacted user, situation under control"
}
```

**Valid Status Values:**
- `pending` - New event, not yet reviewed
- `acknowledged` - Admin has seen and is investigating
- `resolved` - Situation resolved
- `false_alarm` - Not a real emergency

**Response (200 OK):**
```json
{
  "id": "f52436aa-c31e-422e-aa26-bb7e05b335b1",
  "is_resolved": "acknowledged",
  "resolved_at": "2025-10-24T07:00:00Z",
  "resolved_by": "37c87fc0-e4b1-4dd4-b618-6219437bb28f",
  "resolution_notes": "Team contacted user, situation under control",
  ...
}
```

---

## MQTT Integration

### Overview

Devices can also report critical events via MQTT for scenarios where:
- Device is always connected to broker
- Lower latency required
- Offline buffering needed
- Battery optimization (MQTT more efficient than HTTP)

### MQTT Connection

**Broker:** `mqtt-lb` (via HAProxy load balancer)
**Port:** `8883` (TLS encrypted)
**Protocol:** MQTT v3.1.1 or v5.0
**Authentication:** Username/Password + TLS client certificates
**QoS:** 1 (at least once delivery)

**Connection Details:**
```
Host: dg-dev.hikeandfly.app
Port: 8883
TLS: Required
Client Cert: Required
CA Cert: /certs/mqtt/ca.crt
Client Cert: /certs/mqtt/client.crt
Client Key: /certs/mqtt/client.key
Username: From MQTT_USER env
Password: From MQTT_PASSWORD env
```

---

## MQTT Topics for Critical Events

### 1. Impact Detection

**Topic:** `device/{device_id}/critical/impact`

**Payload (JSON):**
```json
{
  "user_id": "f5eb492a-3455-4e56-bd71-b8e5d7c9d001",
  "severity": "critical",
  "timestamp": "2025-10-24T19:00:00Z",
  "latitude": 45.5017,
  "longitude": -73.5673,
  "altitude": 1500,
  "impact_magnitude": 15.2,
  "direction": "vertical",
  "flight_id": "e6c4db96-470e-44d0-a06c-4e6231e112a4"
}
```

**Example (Python with Paho MQTT):**
```python
import paho.mqtt.client as mqtt
import json
import ssl
from datetime import datetime

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
    else:
        print(f"Connection failed with code {rc}")

# Configure MQTT client
client = mqtt.Client(client_id=f"device_{device_id}")
client.username_pw_set(username="mqtt_user", password="mqtt_password")

# Configure TLS
client.tls_set(
    ca_certs="/path/to/ca.crt",
    certfile="/path/to/client.crt",
    keyfile="/path/to/client.key",
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.on_connect = on_connect
client.connect("dg-dev.hikeandfly.app", 8883, keepalive=60)

# Report impact
impact_data = {
    "user_id": "f5eb492a-3455-4e56-bd71-b8e5d7c9d001",
    "severity": "critical",
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "latitude": 45.5017,
    "longitude": -73.5673,
    "altitude": 1500,
    "impact_magnitude": 15.2,
    "direction": "vertical"
}

topic = f"device/{device_id}/critical/impact"
client.publish(topic, json.dumps(impact_data), qos=1)
```

---

### 2. SOS Button Press

**Topic:** `device/{device_id}/critical/sos`

**Payload (JSON):**
```json
{
  "user_id": "f5eb492a-3455-4e56-bd71-b8e5d7c9d001",
  "severity": "critical",
  "timestamp": "2025-10-24T19:00:00Z",
  "latitude": 45.5017,
  "longitude": -73.5673,
  "altitude": 1500,
  "message": "Emergency - need assistance",
  "auto_triggered": false,
  "flight_id": "e6c4db96-470e-44d0-a06c-4e6231e112a4"
}
```

**Example (ESP32 Arduino):**
```cpp
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

WiFiClientSecure wifiClient;
PubSubClient mqttClient(wifiClient);

void reportSOS() {
  StaticJsonDocument<512> doc;
  doc["user_id"] = "f5eb492a-3455-4e56-bd71-b8e5d7c9d001";
  doc["severity"] = "critical";
  doc["timestamp"] = getISOTimestamp(); // Your function
  doc["latitude"] = gps.latitude;
  doc["longitude"] = gps.longitude;
  doc["altitude"] = gps.altitude;
  doc["message"] = "SOS button pressed";
  doc["auto_triggered"] = false;

  char payload[512];
  serializeJson(doc, payload);

  String topic = "device/" + String(deviceId) + "/critical/sos";
  mqttClient.publish(topic.c_str(), payload, true); // QoS 1, retained
}

void setup() {
  // Load certificates
  wifiClient.setCACert(ca_cert);
  wifiClient.setCertificate(client_cert);
  wifiClient.setPrivateKey(client_key);

  mqttClient.setServer("dg-dev.hikeandfly.app", 8883);
  mqttClient.setCallback(messageCallback);
}
```

---

### 3. Critical Battery Level

**Topic:** `device/{device_id}/critical/battery`

**Payload (JSON):**
```json
{
  "user_id": "f5eb492a-3455-4e56-bd71-b8e5d7c9d001",
  "severity": "severe",
  "timestamp": "2025-10-24T19:00:00Z",
  "latitude": 45.5017,
  "longitude": -73.5673,
  "battery_level": 5,
  "voltage": 3.2,
  "flight_id": "e6c4db96-470e-44d0-a06c-4e6231e112a4"
}
```

---

### 4. Device Offline Alert

**Topic:** `device/{device_id}/critical/offline`

**Payload (JSON):**
```json
{
  "user_id": "f5eb492a-3455-4e56-bd71-b8e5d7c9d001",
  "severity": "moderate",
  "timestamp": "2025-10-24T19:00:00Z",
  "latitude": 45.5017,
  "longitude": -73.5673,
  "last_seen": "2025-10-24T18:30:00Z",
  "reason": "signal_lost"
}
```

---

## Event Processing Flow

```
┌─────────────────┐
│  Mobile App /   │
│  IoT Device     │
└────────┬────────┘
         │
         ├─────────── HTTP POST /critical-event (RECOMMENDED) & /impact-alert (backward compatible)
         │            (202 Accepted - immediate response)
         │
         └─────────── MQTT Publish device/{id}/critical/{type}
                      (QoS 1 - at least once)
         │
         ▼
┌─────────────────────────────────────────────────┐
│            Redis Stream: critical_events         │
│  • Reliable message queue                       │
│  • Survives API restarts                        │
│  • Persistent (AOF enabled)                     │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   Celery Worker       │
         │   (Auto-consuming)    │
         │   • Batch processing  │
         │   • Retry on failure  │
         └───────────┬───────────┘
                     │
         ┌───────────┴────────────┐
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌──────────────────┐
│   PostgreSQL    │    │  Platform News   │
│  critical_events│    │  (Bell Notif)    │
└─────────────────┘    └──────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌──────────────────┐
│ Circle Contacts │    │   Admin          │
│ Email Notif     │    │   Dashboard      │
└─────────────────┘    └──────────────────┘
```

---

## Best Practices

### For Mobile Apps

1. **Retry Logic:** If API returns 5xx, retry after 5 seconds (max 3 retries)
2. **Local Storage:** Store events locally if offline, send when connected
3. **Battery:** Batch events if multiple occur within 10 seconds
4. **Accuracy:** Wait for GPS fix before sending location
5. **Deduplication:** Don't send same event twice (check timestamp + magnitude)

```javascript
// Example retry with exponential backoff
const sendWithRetry = async (data, retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(endpoint, { method: 'POST', body: data });
      if (response.status === 202) return response.json();
      if (response.status >= 500) throw new Error('Server error');
      return response.json(); // Client error, don't retry
    } catch (error) {
      if (i === retries - 1) throw error;
      await sleep(Math.pow(2, i) * 1000); // 1s, 2s, 4s
    }
  }
};
```

### For ESP32 / IoT Devices

1. **Connection:** Use MQTT for always-on devices (more efficient than HTTP)
2. **QoS 1:** Ensure at-least-once delivery
3. **Certificates:** Store certs in secure flash (not code)
4. **Reconnect:** Implement exponential backoff on connection failure
5. **Buffer:** Store events in flash if MQTT disconnected

```cpp
// Example with reconnect logic
void maintainMQTT() {
  if (!mqttClient.connected()) {
    int retries = 0;
    while (!mqttClient.connected() && retries < 5) {
      Serial.println("Attempting MQTT connection...");
      if (mqttClient.connect(clientId, mqttUser, mqttPassword)) {
        Serial.println("Connected to MQTT");
        sendBufferedEvents(); // Send any stored events
      } else {
        retries++;
        delay(5000 * retries); // Exponential backoff
      }
    }
  }
  mqttClient.loop();
}
```

---

## Security

### API Security
- ✅ JWT authentication required
- ✅ Device ownership verified before accepting events
- ✅ Rate limiting: 100 requests/minute per user
- ✅ Input validation: lat/lon bounds, magnitude sanity checks

### MQTT Security
- ✅ TLS 1.2+ required (port 8883)
- ✅ Client certificates required
- ✅ HMAC message signing (optional, for extra security)
- ✅ Username/password authentication
- ✅ Topic ACLs: devices can only publish to their own topics

---

## Testing

### Test Impact Alert (cURL)
```bash
# 1. Get JWT token
TOKEN=$(curl -s -X POST https://dg-dev.hikeandfly.app/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=youruser&password=yourpass" | jq -r '.access_token')

# 2. Send test impact
curl -X POST https://dg-dev.hikeandfly.app/api/v1/impact-alert \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "device_id": "TEST_DEVICE_001",
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "location": {"lat": 45.5, "lon": -73.5, "alt": 1000},
    "impact_magnitude": 10.0,
    "severity": "severe"
  }'
```

### Test MQTT (mosquitto_pub)
```bash
mosquitto_pub \
  -h dg-dev.hikeandfly.app \
  -p 8883 \
  --cafile ca.crt \
  --cert client.crt \
  --key client.key \
  -u mqtt_user \
  -P mqtt_password \
  -t "device/TEST_DEVICE_001/critical/impact" \
  -m '{"user_id":"test-user-id","severity":"critical","timestamp":"2025-10-24T19:00:00Z","latitude":45.5,"longitude":-73.5,"impact_magnitude":12.5}' \
  -q 1
```

---

## Support

**API Documentation:** https://dg-dev.hikeandfly.app/docs
**System Status:** https://dg-dev.hikeandfly.app/api/v1/health
**Admin Dashboard:** https://dg-dev.hikeandfly.app/admin/critical-events

For questions or issues:
- Check logs: `docker compose logs -f celery_worker_critical_events`
- Monitor queue: `redis-cli XINFO STREAM stream:critical_events`
- View events: Login to admin dashboard → Critical Events

---

## Changelog

### v1.0 (2025-10-24)
- ✅ Initial release
- ✅ Impact detection via REST API
- ✅ MQTT topic structure defined
- ✅ Admin dashboard for event management
- ✅ Async processing with Redis Streams
- ✅ Platform notifications (bell icon)
- ✅ Circle contact email notifications

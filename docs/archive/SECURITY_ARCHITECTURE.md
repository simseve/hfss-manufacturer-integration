# End-to-End Security Architecture

## Overview

The HFSS-DIGI GPS tracking system implements defense-in-depth with multiple security layers protecting data from device to database. This document details how security is enforced at each stage of the data flow.

## Security Layers

### 1. Device Provisioning & Authentication

#### Factory Provisioning (Secure by Design)
```
┌─────────────────┐
│ Manufacturing   │
│    Factory      │
├─────────────────┤
│ • Device ID     │ ← Unique per device
│ • Device Secret │ ← 256-bit random
│ • Reg Token     │ ← SHA256(ID + Secret + Manufacturer)
└─────────────────┘
```

**Security Controls:**
- Each device receives a cryptographically secure 256-bit secret
- Registration token prevents unauthorized device cloning
- Secrets are burned to secure storage (ESP32 eFuse recommended)

#### Device Registration Flow
```
Device                          API                           Database
  │                              │                                │
  ├── POST /register ──────────→ │                                │
  │   {device_id,                │                                │
  │    manufacturer_secret,      ├── Verify manufacturer ────────→ │
  │    registration_token}       │   secret (HMAC)                 │
  │                              │                                │
  │                              ├── Generate MQTT creds ────────→ │
  │ ←─── API Key + MQTT ──────── │   Store encrypted secret        │
  │      credentials             │                                │
```

**Security Controls:**
- Manufacturer secret required (known only to authorized manufacturers)
- Registration token validates device authenticity
- One-time registration prevents replay attacks
- Device secrets encrypted with Fernet before database storage

### 2. MQTT Transport Security

#### Connection Security
```
┌────────────┐     TLS 1.3      ┌──────────┐     ┌──────────┐
│   Device   │ ←───────────────→ │ HAProxy  │ ←──→│   MQTT   │
│ (ESP32)    │    Port 8883      │   (LB)   │     │  Broker  │
└────────────┘                   └──────────┘     └──────────┘
```

**Security Controls:**
- **TLS 1.3** with strong cipher suites (AES-256-GCM-SHA384)
- **Certificate validation** prevents MITM attacks
- **Port 8883** exclusively for encrypted traffic
- **HAProxy** terminates TLS and load balances to MQTT brokers

#### MQTT Authentication
```
mosquitto-go-auth Plugin
         │
         ├── PostgreSQL Backend
         │   └── bcrypt hashed passwords
         │
         └── Per-device ACLs
             ├── Publish: gps/{device_id}/data
             └── Subscribe: devices/{device_id}/+
```

**Security Controls:**
- **PostgreSQL authentication** via mosquitto-go-auth plugin
- **Unique credentials** per device (username: device_{id})
- **bcrypt** password hashing (cost factor 12)
- **Topic-based ACLs** restrict device access to own topics only
- **No anonymous access** - all connections require authentication

### 3. Message Integrity & Authentication

#### HMAC Signature Scheme
```python
# Device side
gps_data = {
    "device_id": "PARA-001",
    "timestamp": "2025-01-11T10:00:00Z",
    "latitude": 45.5,
    "longitude": 6.7,
    ...
}

# Canonical JSON for consistent hashing
canonical = json.dumps(gps_data, sort_keys=True, separators=(',',':'))

# HMAC-SHA256 signature
signature = hmac.new(
    device_secret.encode(),
    canonical.encode(),
    hashlib.sha256
).hexdigest()

# Final message
mqtt_message = {
    "data": gps_data,
    "signature": signature,
    "api_key": device_api_key
}
```

**Security Controls:**
- **HMAC-SHA256** signatures on every message
- **Canonical JSON** ensures consistent signature verification
- **Timestamp validation** prevents replay attacks (5-minute window)
- **Device secret** never transmitted, only used for signing

#### Server-Side Verification
```python
# API verification flow
def verify_message(payload):
    # 1. Check required fields
    if not all(k in payload for k in ["data", "signature", "api_key"]):
        return False  # Reject
    
    # 2. Validate timestamp freshness
    if not is_message_fresh(payload["data"]["timestamp"]):
        return False  # Reject old messages
    
    # 3. Decrypt device secret from database
    device_secret = decrypt(device.encrypted_device_secret)
    
    # 4. Verify HMAC signature
    expected = hmac.new(device_secret, canonical_data, sha256)
    if not hmac.compare_digest(expected, provided_signature):
        return False  # Reject invalid signature
    
    return True  # Accept
```

### 4. API Security

#### Authentication Flow
```
┌────────┐        JWT          ┌─────────┐
│ Client │ ←─────────────────→ │   API   │
└────────┘                     └─────────┘
     │                              │
     └── Bearer Token ──────────────┘
         (HS256 signed)
```

**Security Controls:**
- **JWT tokens** for API authentication
- **HS256 signing** with secure secret key
- **Token expiration** (configurable, default 30 minutes)
- **Role-based access** (admin, user, device roles)

### 5. Data Storage Security

#### Database Security
```
┌─────────────────────────────────────┐
│         TimescaleDB                 │
├─────────────────────────────────────┤
│ • Encrypted device secrets (Fernet) │
│ • Hashed passwords (bcrypt)        │
│ • PostGIS geometry columns         │
│ • Hypertable partitioning          │
│ • Row-level security (planned)     │
└─────────────────────────────────────┘
```

**Security Controls:**
- **Fernet encryption** for device secrets (AES-128 in CBC mode)
- **bcrypt hashing** for all passwords
- **Separate database users** with minimal privileges
- **Connection encryption** (SSL/TLS to database)

### 6. Infrastructure Security

#### Network Isolation
```
┌─────────────────────────────────────────┐
│          Docker Network                 │
├─────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌────────┐ │
│  │  MQTT   │  │   API   │  │   DB   │ │
│  └─────────┘  └─────────┘  └────────┘ │
└─────────────────────────────────────────┘
     ↑              ↑
     │              │
  Port 8883     Port 80/443
  (MQTT TLS)    (HTTPS API)
```

**Security Controls:**
- **Docker network isolation** - services communicate internally
- **Minimal port exposure** - only 80, 443, 8883 exposed
- **No direct database access** from outside
- **Redis password protection** for cache/queue

## Threat Model & Mitigations

### 1. Device Impersonation
**Threat**: Attacker tries to send fake GPS data
**Mitigations**:
- Unique device secrets (unguessable)
- HMAC signatures (unforgeable without secret)
- Device registration control

### 2. Man-in-the-Middle (MITM)
**Threat**: Attacker intercepts GPS data
**Mitigations**:
- TLS 1.3 encryption
- Certificate validation
- No plaintext protocols

### 3. Replay Attacks
**Threat**: Attacker replays old GPS messages
**Mitigations**:
- Timestamp validation (5-minute window)
- Message deduplication in processing

### 4. Unauthorized Access
**Threat**: Attacker tries to access other devices' data
**Mitigations**:
- Per-device MQTT credentials
- Topic-based ACLs
- API authentication required

### 5. Secret Compromise
**Threat**: Device secret is extracted/leaked
**Mitigations**:
- Secrets encrypted at rest
- Secure provisioning process
- Device revocation capability

## Security Best Practices

### For Device Manufacturers
1. Use hardware security modules (HSM) for provisioning
2. Implement secure boot on devices
3. Store secrets in protected memory (eFuse/TrustZone)
4. Implement firmware signing and updates

### For System Operators
1. Regular security audits
2. Monitor for anomalous behavior
3. Implement rate limiting
4. Regular credential rotation
5. Keep all components updated

### For Deployment
1. Use strong PostgreSQL passwords
2. Configure firewall rules
3. Enable audit logging
4. Implement backup encryption
5. Use separate environments (dev/staging/prod)

## Compliance Considerations

### GDPR (Location Data)
- Encryption at rest and in transit ✓
- Access controls and authentication ✓
- Data minimization (configurable retention)
- Right to deletion (device revocation)

### IoT Security Standards
- Unique credentials per device ✓
- Secure by default ✓
- No hardcoded passwords ✓
- Encrypted communications ✓

## Security Monitoring

### Key Metrics to Monitor
```sql
-- Failed authentication attempts
SELECT COUNT(*) FROM mqtt_logs 
WHERE event_type = 'auth_failed' 
AND timestamp > NOW() - INTERVAL '1 hour';

-- Invalid signatures
SELECT device_id, COUNT(*) as invalid_count
FROM api_logs
WHERE event_type = 'invalid_signature'
GROUP BY device_id
HAVING COUNT(*) > 10;

-- Unusual GPS patterns
SELECT device_id 
FROM gps_data
WHERE ST_Distance(
    geometry,
    LAG(geometry) OVER (PARTITION BY device_id ORDER BY timestamp)
) > 1000 -- 1km jump
AND timestamp - LAG(timestamp) < INTERVAL '1 minute';
```

## Summary

The HFSS-DIGI system implements comprehensive security through:

1. **Strong cryptography**: HMAC-SHA256, bcrypt, Fernet encryption
2. **Defense in depth**: Multiple security layers
3. **Zero trust**: Every message authenticated
4. **Least privilege**: Minimal access per component
5. **Secure by default**: No optional security

This architecture protects against common IoT threats while maintaining high performance for thousands of concurrent devices.
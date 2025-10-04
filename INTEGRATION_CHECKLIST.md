# Integration Checklist

Use this checklist to ensure your GPS device integration is complete and production-ready.

## Pre-Integration

- [ ] **Request Manufacturer Credentials**
  - [ ] Contact sales@hikeandfly.app
  - [ ] Receive MANUFACTURER_SECRET (32 characters)
  - [ ] Receive MANUFACTURER_ID
  - [ ] Get production endpoints confirmed

- [ ] **Development Environment**
  - [ ] Python 3.7+ installed
  - [ ] Git installed
  - [ ] Network access to dg-dev.hikeandfly.app
  - [ ] Ports 8883 and 443 open

## Integration Setup

- [ ] **Repository Setup**
  ```bash
  git clone https://github.com/hfss/manufacturer-integration.git
  cd manufacturer-integration
  pip install -r requirements.txt
  ```

- [ ] **Configure Credentials**
  ```bash
  cp .env.example .env
  # Edit .env with your MANUFACTURER_SECRET
  ```

## Testing Phase

- [ ] **Basic Connectivity**
  ```bash
  # Test API endpoint
  curl https://dg-dev.hikeandfly.app/api/v1/health

  # Test MQTT broker
  ping dg-mqtt.hikeandfly.app
  ```

- [ ] **Run Integration Tests**
  ```bash
  ./run_all_gps_tests.sh
  ```
  - [ ] Test 1: MQTT Single Point ✅
  - [ ] Test 2: MQTT Batch ✅
  - [ ] Test 3: HTTP Single Point ✅
  - [ ] Test 4: HTTP Batch ✅
  - [ ] Test 5: Flight Close (MQTT) ✅
  - [ ] Test 6: Flight Close (HTTP) ✅

- [ ] **Device Registration**
  ```bash
  python3 scripts/manufacturer_device_test.py \
    --device-id TEST-001 \
    --manufacturer-secret $MANUFACTURER_SECRET \
    --num-messages 5
  ```
  - [ ] Registration successful
  - [ ] Credentials saved to /tmp/
  - [ ] GPS data transmitted
  - [ ] No error messages

- [ ] **Batch Mode Testing**
  ```bash
  python3 scripts/manufacturer_device_test.py \
    --config-file /tmp/device_TEST-001_complete.json \
    --skip-registration \
    --batch-mode \
    --batch-size 20
  ```
  - [ ] Batch transmission works
  - [ ] All points accepted

## Device Implementation

- [ ] **Security**
  - [ ] Device credentials stored in secure flash
  - [ ] HMAC-SHA256 signature implemented
  - [ ] TLS connection established
  - [ ] No hardcoded secrets in code

- [ ] **GPS Data Format**
  - [ ] All mandatory fields present
    - [ ] device_id
    - [ ] flight_id (UUID v4)
    - [ ] timestamp (UTC ISO 8601)
    - [ ] latitude (-90 to 90)
    - [ ] longitude (-180 to 180)
  - [ ] Optional fields as needed
    - [ ] altitude
    - [ ] speed
    - [ ] battery_level

- [ ] **Flight Lifecycle Management**
  - [ ] New flight_id generated on takeoff
  - [ ] Same flight_id used for all points in flight
  - [ ] Flight closed on landing (MQTT or HTTP)
  - [ ] Listen for close confirmation on `flight/{device_id}/closed`

- [ ] **Connection Management**
  - [ ] Automatic reconnection on disconnect
  - [ ] Exponential backoff for retries
  - [ ] Offline data buffering
  - [ ] Battery-aware transmission

- [ ] **Error Handling**
  - [ ] Invalid GPS filtered (0,0)
  - [ ] Future timestamps prevented
  - [ ] Network failures handled gracefully
  - [ ] Registration errors logged

## Production Readiness

- [ ] **Load Testing**
  ```bash
  python3 scripts/paraglider_emulator.py \
    --devices 100 \
    --duration 60
  ```
  - [ ] No connection drops
  - [ ] >99% success rate
  - [ ] Acceptable latency

- [ ] **Manufacturing Process**
  - [ ] Device provisioning automated
  - [ ] Unique device IDs generated
  - [ ] Credentials securely stored
  - [ ] Quality control tests defined

- [ ] **Field Testing**
  - [ ] Real GPS hardware tested
  - [ ] Various signal conditions tested
  - [ ] Battery life acceptable
  - [ ] Data accuracy verified

## Documentation

- [ ] **Code Documentation**
  - [ ] Integration code commented
  - [ ] API usage documented
  - [ ] Error codes explained
  - [ ] Configuration documented

- [ ] **User Documentation**
  - [ ] Setup instructions clear
  - [ ] Troubleshooting guide complete
  - [ ] Support contact provided
  - [ ] FAQ section added

## Support & Maintenance

- [ ] **Monitoring**
  - [ ] Device health metrics tracked
  - [ ] Transmission success rate monitored
  - [ ] Battery levels tracked
  - [ ] Connection stability monitored

- [ ] **Updates**
  - [ ] Firmware update mechanism ready
  - [ ] Credential rotation planned
  - [ ] API version compatibility checked
  - [ ] Deprecation notices monitored

## Final Verification

- [ ] **Complete Integration Test**
  ```bash
  # Register production device
  DEVICE_ID="PROD-$(date +%s)"
  python3 scripts/manufacturer_device_test.py \
    --device-id $DEVICE_ID \
    --manufacturer-secret $MANUFACTURER_SECRET \
    --num-messages 100
  ```

- [ ] **Verify Data Reception**
  - [ ] All GPS points received
  - [ ] Data correctly formatted
  - [ ] No missing fields
  - [ ] Timestamps accurate

- [ ] **Production Approval**
  - [ ] HFSS team notified
  - [ ] Production credentials received
  - [ ] Rate limits confirmed
  - [ ] SLA agreed

## Sign-off

- [ ] Technical Lead Approval
- [ ] QA Testing Complete
- [ ] Production Deployment Ready
- [ ] Support Team Briefed

---

## Quick Reference

**Production Endpoints:**
- API: `https://dg-dev.hikeandfly.app/api/v1`
- MQTT: `dg-mqtt.hikeandfly.app:8883`
- CA Cert: `https://dg-dev.hikeandfly.app/ca.crt`

**Support Contacts:**
- Technical: support@hikeandfly.app
- Sales: sales@hikeandfly.app
- Emergency: +41 XX XXX XX XX

**Documentation:**
- [Getting Started](GETTING_STARTED.md)
- [Script Usage](SCRIPT_USAGE.md)
- [GPS Testing Guide](GPS_TESTING_GUIDE.md)
- [Troubleshooting](GPS_TESTING_GUIDE.md#troubleshooting)

---

✅ **Ready for Production?** Complete all checkboxes above!
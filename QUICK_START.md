# Quick Start - GPS Device Integration

## 1️⃣ Run the Test Script

```bash
cd scripts
./run_all_gps_tests.sh
```

## 2️⃣ What Just Happened?

The script automatically:
- ✅ Downloaded CA certificate from `/ca.crt` endpoint
- ✅ Registered 2 test devices
- ✅ Sent GPS data via MQTT (single + batch)
- ✅ Sent GPS data via HTTP (single + batch)
- ✅ Verified data in database

## 3️⃣ Use the Test Results

You'll see device credentials saved at:
```
/tmp/device_MQTT-TEST-xxxxx_complete.json
/tmp/device_HTTP-TEST-xxxxx_complete.json
```

These files contain everything your device needs:
- Device ID
- API Key (for HTTP)
- MQTT Username & Password
- Device Secret (for signatures)

## That's It! 🎉

Your integration is working. Now implement the same flow in your device firmware.

---

**Need more details?** See [GPS_TESTING_GUIDE.md](GPS_TESTING_GUIDE.md)
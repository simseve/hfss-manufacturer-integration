# HFSS DIGI - Manufacturer Integration

Welcome! This guide helps you integrate your GPS devices with the HFSS DIGI platform.

## 🚀 Quick Start (5 minutes)

### 1. Test Your Device Integration

```bash
cd scripts
./run_all_gps_tests.sh
```

This runs all 4 tests automatically and shows you the results.

### 2. What You'll See

✅ **Test 1**: Send 1 GPS point via MQTT  
✅ **Test 2**: Send 5 GPS points via MQTT (batch)  
✅ **Test 3**: Send 1 GPS point via HTTP API  
✅ **Test 4**: Send 5 GPS points via HTTP API (batch)  

## 📁 What's in This Folder

```
manufacturer/
├── README.md                           <- You are here
├── GPS_TESTING_GUIDE.md                <- Detailed testing instructions
├── MANUFACTURER_QUICK_REFERENCE.md     <- One-page cheat sheet
├── scripts/                            <- Ready-to-run test scripts
│   ├── run_all_gps_tests.sh           <- Run all 4 tests automatically
│   ├── manufacturer_device_test.py     <- Main device testing tool
│   └── test_http_api.py               <- HTTP API tester
├── examples/                           <- Code examples for your devices
│   └── esp32_gps_tracker/             <- Complete ESP32 example
└── docs/                              <- Additional documentation
    └── archive/                       <- Detailed specs (if needed)
```

## 🎯 Three Simple Steps

### Step 1: Get Your Credentials
```bash
# Your manufacturer secret is provided by HFSS
export MANUFACTURER_SECRET=your_secret_here
```

### Step 2: Register a Test Device
```bash
python scripts/manufacturer_device_test.py \
  --device-id TEST-001 \
  --manufacturer-secret $MANUFACTURER_SECRET \
  --num-messages 0
```

### Step 3: Send GPS Data
```bash
# Send via MQTT
python scripts/manufacturer_device_test.py \
  --config-file /tmp/device_TEST-001_complete.json \
  --skip-registration \
  --num-messages 5

# Or send via HTTP
python scripts/test_http_api.py
```

## 📊 Verify Your Data

Check if your GPS points reached our servers:

```bash
docker compose exec timescaledb psql -U gps_prod_user -d gps_tracking_production -c \
  "SELECT COUNT(*) FROM gps_data WHERE device_id = 'TEST-001'"
```

## 🔧 Integration Options

### Option A: MQTT (Recommended for Real-time)
- **Protocol**: MQTT over TLS (port 8883)
- **Best for**: Continuous GPS tracking
- **Power efficient**: Batch up to 30 points

### Option B: HTTP API
- **Protocol**: HTTPS REST API
- **Best for**: Periodic updates
- **Simple**: Standard HTTP POST requests

## 📚 Need More Details?

- **Testing Guide**: See [GPS_TESTING_GUIDE.md](GPS_TESTING_GUIDE.md)
- **Quick Reference**: See [MANUFACTURER_QUICK_REFERENCE.md](MANUFACTURER_QUICK_REFERENCE.md)
- **Certificate Info**: See [CERTIFICATE_INFO.md](CERTIFICATE_INFO.md)
- **ESP32 Example**: See [examples/esp32_gps_tracker/](examples/esp32_gps_tracker/)

## 🆘 Getting Help

1. **Common Issues**: Check the troubleshooting section in GPS_TESTING_GUIDE.md
2. **Integration Support**: Contact your HFSS representative
3. **Technical Specs**: See docs/archive/ for detailed documentation

---

**Ready to start?** → Run `./scripts/run_all_gps_tests.sh` and see your GPS data in action!
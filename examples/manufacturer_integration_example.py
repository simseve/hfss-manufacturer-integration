#!/usr/bin/env python3
"""
HFSS-DIGI Manufacturer Integration Example
==========================================

This example shows how to integrate a GPS tracking device with the HFSS-DIGI platform.
It demonstrates the complete flow from device provisioning to sending GPS data.

Example Usage:
- Set environment variables or update the configuration section
- Run the script to see the complete integration flow

Required packages:
pip install requests paho-mqtt
"""

import os
import json
import time
import hmac
import hashlib
import secrets
import ssl
from datetime import datetime, timezone
import requests
import paho.mqtt.client as mqtt

# ============================================================================
# CONFIGURATION - Update these values for your deployment
# ============================================================================

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost/api/v1")
CA_CERT_URL = os.getenv("CA_CERT_URL", "http://localhost/ca.crt")

# MQTT Configuration  
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))

# Manufacturer Credentials (Keep these secure!)
MANUFACTURER_ID = os.getenv("MANUFACTURER_ID", "YOUR_MANUFACTURER_ID")
MANUFACTURER_SECRET = os.getenv("MANUFACTURER_SECRET", "your-manufacturer-secret-here")

# ============================================================================
# DEVICE PROVISIONING (Factory Process)
# ============================================================================

def provision_device(device_number=1):
    """
    Generate device credentials at the factory.
    In production, this would be done in a secure environment and the
    credentials would be burned into the device's secure storage.
    """
    # Generate unique device ID
    timestamp = datetime.now().strftime('%Y%m%d')
    random_id = secrets.randbelow(9000) + 1000
    device_id = f"PARA-{timestamp}-{random_id}-{device_number:04d}"
    
    # Generate secure device secret (256-bit)
    device_secret = secrets.token_hex(32)
    
    # Calculate registration token
    message = f"{device_id}:{device_secret}:{MANUFACTURER_ID}"
    registration_token = hmac.new(
        MANUFACTURER_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    print(f"✅ Device provisioned:")
    print(f"   Device ID: {device_id}")
    print(f"   Device Secret: {device_secret[:8]}... (hidden)")
    print(f"   Registration Token: {registration_token[:16]}... (hidden)")
    
    return {
        "device_id": device_id,
        "device_secret": device_secret,
        "registration_token": registration_token,
        "manufacturer": MANUFACTURER_ID
    }

# ============================================================================
# DEVICE REGISTRATION (First Boot)
# ============================================================================

def download_ca_certificate(filepath="ca.crt"):
    """Download CA certificate from the API endpoint."""
    if os.path.exists(filepath):
        print(f"✅ CA certificate already exists: {filepath}")
        return filepath
        
    print(f"📥 Downloading CA certificate from {CA_CERT_URL}...")
    try:
        response = requests.get(CA_CERT_URL)
        response.raise_for_status()
        
        with open(filepath, 'w') as f:
            f.write(response.text)
            
        print(f"✅ CA certificate saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Failed to download CA certificate: {e}")
        return None

def register_device(device_config):
    """
    Register the device with the platform.
    This is done once during the device's first boot.
    """
    print("\n📡 Registering device with platform...")
    
    registration_data = {
        "device_id": device_config["device_id"],
        "device_secret": device_config["device_secret"],
        "registration_token": device_config["registration_token"],
        "manufacturer": device_config["manufacturer"],
        "device_metadata": {
            "model": "TRACKER-X1",
            "firmware": "1.0.0",
            "hardware": "rev2"
        }
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/devices/register",
            json=registration_data,
            timeout=10
        )
        
        if response.status_code == 200:
            credentials = response.json()
            print("✅ Registration successful!")
            print(f"   API Key: {credentials['api_key'][:20]}...")
            print(f"   MQTT Username: {credentials['mqtt_username']}")
            return credentials
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return None

# ============================================================================
# MQTT CONNECTION
# ============================================================================

class GPSDevice:
    """Represents a GPS tracking device."""
    
    def __init__(self, device_id, api_key, mqtt_username, mqtt_password, ca_cert_path):
        self.device_id = device_id
        self.api_key = api_key
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        self.ca_cert_path = ca_cert_path
        self.client = None
        self.connected = False
        
    def on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback."""
        if rc == 0:
            print("✅ MQTT connected successfully!")
            self.connected = True
        else:
            print(f"❌ MQTT connection failed with code: {rc}")
            self.connected = False
            
    def on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback."""
        print(f"📡 MQTT disconnected with code: {rc}")
        self.connected = False
        
    def connect(self):
        """Connect to MQTT broker."""
        print(f"\n🔌 Connecting to MQTT broker at {MQTT_HOST}:{MQTT_PORT}...")
        
        self.client = mqtt.Client(client_id=self.device_id)
        self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
        
        # Set up TLS
        self.client.tls_set(
            ca_certs=self.ca_cert_path,
            tls_version=ssl.PROTOCOL_TLSv1_2
        )
        
        # Set callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        
        try:
            self.client.connect(MQTT_HOST, MQTT_PORT, 60)
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10
            while not self.connected and timeout > 0:
                time.sleep(1)
                timeout -= 1
                
            return self.connected
            
        except Exception as e:
            print(f"❌ MQTT connection error: {e}")
            return False
            
    def send_gps_data(self, latitude, longitude, altitude, **kwargs):
        """Send GPS data to the platform."""
        if not self.connected:
            print("❌ Not connected to MQTT")
            return False
            
        # Prepare GPS data
        gps_data = {
            "device_id": self.device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": latitude,
            "longitude": longitude,
            "altitude": altitude,
            "speed": kwargs.get("speed", 0.0),
            "heading": kwargs.get("heading", 0.0),
            "accuracy": kwargs.get("accuracy", 5.0),
            "battery": kwargs.get("battery", 85.0),
            "temperature": kwargs.get("temperature", 22.5),
            "satellites": kwargs.get("satellites", 10),
            "hdop": kwargs.get("hdop", 1.2)
        }
        
        # Calculate HMAC signature
        data_json = json.dumps(gps_data, sort_keys=True)
        signature = hmac.new(
            self.api_key.encode(),
            data_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Prepare message
        message = {
            "data": gps_data,
            "signature": signature
        }
        
        # Publish to MQTT
        topic = f"gps/{self.device_id}/data"
        result = self.client.publish(topic, json.dumps(message), qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"✅ GPS data sent: lat={latitude:.6f}, lon={longitude:.6f}, alt={altitude:.1f}m")
            return True
        else:
            print(f"❌ Failed to send GPS data: {result.rc}")
            return False
            
    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def main():
    """Run the complete device integration example."""
    
    print("🚀 HFSS-DIGI Device Integration Example")
    print("======================================")
    print()
    
    # Step 1: Factory provisioning
    print("STEP 1: Factory Provisioning")
    print("-" * 40)
    device_config = provision_device()
    print()
    
    # Step 2: Download CA certificate
    print("STEP 2: CA Certificate Setup")
    print("-" * 40)
    ca_cert_path = download_ca_certificate()
    if not ca_cert_path:
        print("❌ Cannot proceed without CA certificate")
        return
    print()
    
    # Step 3: Device registration (first boot)
    print("STEP 3: Device Registration")
    print("-" * 40)
    credentials = register_device(device_config)
    if not credentials:
        print("❌ Registration failed")
        return
    print()
    
    # Step 4: MQTT connection
    print("STEP 4: MQTT Connection")
    print("-" * 40)
    device = GPSDevice(
        device_config["device_id"],
        credentials["api_key"],
        credentials["mqtt_username"],
        credentials["mqtt_password"],
        ca_cert_path
    )
    
    if not device.connect():
        print("❌ MQTT connection failed")
        return
    print()
    
    # Step 5: Send GPS data
    print("STEP 5: Sending GPS Data")
    print("-" * 40)
    
    # Simulate GPS data from Chamonix, France
    base_lat = 45.9237
    base_lon = 6.8694
    base_alt = 2400.0
    
    try:
        for i in range(5):
            # Simulate small movements
            lat = base_lat + (secrets.randbelow(200) - 100) / 100000
            lon = base_lon + (secrets.randbelow(200) - 100) / 100000
            alt = base_alt + (secrets.randbelow(50) - 25)
            
            device.send_gps_data(
                latitude=lat,
                longitude=lon,
                altitude=alt,
                speed=secrets.randbelow(10) / 10,
                heading=secrets.randbelow(360),
                battery=85 - i,
                satellites=10 + secrets.randbelow(5)
            )
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        
    finally:
        # Disconnect
        device.disconnect()
        print("\n✅ Device integration example completed!")

if __name__ == "__main__":
    main()
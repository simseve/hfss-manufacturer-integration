#!/usr/bin/env python3
"""
Manufacturer Device Integration Test
====================================
This script simulates the complete lifecycle of a GPS tracking device
from a manufacturer's perspective:
1. Device provisioning (at factory)
2. Device registration (first boot)
3. MQTT connection setup
4. Sending GPS data

This is what would run on an actual device (ESP32, etc.)
"""

import os
import sys
import json
import time
import uuid
import hmac
import hashlib
import random
import ssl
from datetime import datetime, timezone
import requests
import paho.mqtt.client as mqtt
from dataclasses import dataclass
from typing import Optional, Tuple
import argparse
import urllib.request

# Default configuration
DEFAULT_API_URL = "http://localhost/api/v1"
DEFAULT_MQTT_HOST = "localhost"
DEFAULT_MQTT_PORT = 8883
DEFAULT_CA_CERT_URL = None  # Will be constructed from API URL if not provided

@dataclass
class DeviceConfig:
    """Device configuration (would be stored in device's secure storage)"""
    device_id: str
    device_secret: str
    registration_token: str
    manufacturer: str = "DIGIFLY"
    
    # These are received after registration
    api_key: Optional[str] = None
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    
    def save_to_file(self, filepath: str):
        """Save config to file (simulating secure storage)"""
        data = {
            "device_id": self.device_id,
            "device_secret": self.device_secret,
            "registration_token": self.registration_token,
            "manufacturer": self.manufacturer,
            "api_key": self.api_key,
            "mqtt_username": self.mqtt_username,
            "mqtt_password": self.mqtt_password
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'DeviceConfig':
        """Load config from file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(**data)


class ManufacturerDevice:
    """Simulates a GPS tracking device from manufacturer's perspective"""
    
    def __init__(self, api_url: str, mqtt_host: str, mqtt_port: int, ca_cert_path: Optional[str] = None):
        self.api_url = api_url
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.ca_cert_path = ca_cert_path
        self.mqtt_client = None
        self.config = None
        self.connected = False
        
    def step1_factory_provisioning(self, device_num: int, manufacturer_secret: str, device_id: str = None, device_secret: str = None) -> DeviceConfig:
        """
        STEP 1: Factory Provisioning
        This happens at the manufacturer's factory.
        Each device gets unique credentials burned into secure storage.
        """
        print("\n" + "="*60)
        print("STEP 1: FACTORY PROVISIONING")
        print("="*60)
        print("Location: Manufacturer's Factory")
        print("Process: Generating unique device credentials...")
        
        # Use provided device_id or generate unique device ID (serial number)
        if device_id:
            print(f"✓ Using provided Device ID: {device_id}")
        else:
            timestamp = int(time.time() * 1000) % 100000
            device_id = f"PARA-{datetime.now().strftime('%Y%m%d')}-{timestamp}-{device_num:04d}"
            print(f"✓ Generated Device ID: {device_id}")
        
        # Use provided device_secret or generate new one
        if device_secret:
            print(f"✓ Using provided Device Secret: {device_secret[:8]}... (hidden)")
        else:
            # Generate device-specific secret (random for each device)
            device_secret = hashlib.sha256(f"{device_id}:{time.time()}:{random.random()}".encode()).hexdigest()[:32]
            print(f"✓ Generated Device Secret: {device_secret[:8]}... (hidden)")
        
        # Calculate registration token (proves device authenticity)
        manufacturer = "DIGIFLY"
        message = f"{manufacturer}:{device_id}:{device_secret}"
        registration_token = hmac.new(
            manufacturer_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        print(f"✓ Calculated Registration Token: {registration_token[:16]}...")
        
        # Create device configuration
        config = DeviceConfig(
            device_id=device_id,
            device_secret=device_secret,
            registration_token=registration_token,
            manufacturer=manufacturer
        )
        
        # In real device: burn to secure storage (TPM, secure element, etc.)
        print("\n📱 Device configuration would be burned to secure storage:")
        print(f"  - Device ID: {device_id}")
        print(f"  - Device Secret: [ENCRYPTED]")
        print(f"  - Registration Token: [ENCRYPTED]")
        print(f"  - Manufacturer: {manufacturer}")
        
        return config
    
    def step2_device_registration(self, config: DeviceConfig, skip_if_exists: bool = False) -> bool:
        """
        STEP 2: Device Registration
        This happens when device is first powered on by end user.
        Device registers itself with the cloud platform.
        """
        print("\n" + "="*60)
        print("STEP 2: DEVICE REGISTRATION (First Boot)")
        print("="*60)
        print("Location: End user's location")
        print("Process: Device self-registration with cloud platform...")
        
        # If skip_if_exists is True and we already have credentials, skip registration
        if skip_if_exists and config.api_key and config.mqtt_username and config.mqtt_password:
            print("✓ Device already registered, using existing credentials")
            self.config = config
            return True
        
        # Prepare registration payload
        payload = {
            "device_id": config.device_id,
            "manufacturer": config.manufacturer,
            "registration_token": config.registration_token,
            "device_secret": config.device_secret,
            "name": f"GPS Tracker {config.device_id[-4:]}",
            "device_type": "PARAGLIDER_TRACKER",
            "firmware_version": "2.1.0",
            "device_info": {
                "battery_capacity": 5000,
                "has_gps": True,
                "has_wifi": True,
                "has_bluetooth": True
            }
        }
        
        print(f"\n📡 Connecting to registration endpoint: {self.api_url}/devices/register")
        
        try:
            # Make registration request
            response = requests.post(
                f"{self.api_url}/devices/register",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Save received credentials
                config.api_key = result['api_key']
                config.mqtt_username = result['mqtt_username']
                config.mqtt_password = result['mqtt_password']
                
                print("✅ Registration successful!")
                print(f"✓ Received API Key: {config.api_key[:20]}...")
                print(f"✓ MQTT Username: {config.mqtt_username}")
                print(f"✓ MQTT Password: {'*' * 16}")
                
                # Save the complete config for reuse
                config_file = f"/tmp/device_{config.device_id}_complete.json"
                config.save_to_file(config_file)
                print(f"\n💾 Saved complete device configuration to: {config_file}")
                print("   This file can be reused with --config-file for subsequent flights")
                
                self.config = config
                return True
                
            else:
                print(f"❌ Registration failed: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Registration error: {str(e)}")
            return False
    
    def step3_download_ca_certificate(self) -> bool:
        """
        STEP 3: Download CA Certificate (if needed)
        Device downloads the CA certificate for MQTT TLS connection.
        """
        print("\n" + "="*60)
        print("STEP 3: MQTT TLS SETUP")
        print("="*60)
        
        # If CA cert path already provided, skip download
        if self.ca_cert_path and os.path.exists(self.ca_cert_path):
            print(f"✓ Using existing CA certificate: {self.ca_cert_path}")
            return True
        
        # Try to download from standard location
        ca_cert_url = DEFAULT_CA_CERT_URL
        if not ca_cert_url:
            # Construct from API URL
            base_url = self.api_url.replace('/api/v1', '')
            ca_cert_url = f"{base_url}/ca.crt"
        
        print(f"📥 Attempting to download CA certificate from: {ca_cert_url}")
        
        try:
            # Add user agent to avoid 403 errors
            req = urllib.request.Request(ca_cert_url)
            req.add_header('User-Agent', 'Mozilla/5.0 (HFSS-Device)')
            response = urllib.request.urlopen(req)
            ca_cert_data = response.read()
            
            # Save to temporary location
            self.ca_cert_path = "/tmp/mqtt_ca.crt"
            with open(self.ca_cert_path, 'wb') as f:
                f.write(ca_cert_data)
            
            print(f"✓ CA certificate downloaded and saved to: {self.ca_cert_path}")
            return True
            
        except Exception as e:
            print(f"⚠️  Could not download CA certificate: {str(e)}")
            print("   Will attempt to use local certificate if available...")
            
            # Try local certificate
            local_cert = "./certs/mqtt/ca.crt"
            if os.path.exists(local_cert):
                self.ca_cert_path = local_cert
                print(f"✓ Using local CA certificate: {self.ca_cert_path}")
                return True
            else:
                print("❌ No CA certificate available for TLS connection")
                return False
    
    def step4_mqtt_connection(self) -> bool:
        """
        STEP 4: MQTT Connection
        Device establishes secure MQTT connection using received credentials.
        """
        print("\n" + "="*60)
        print("STEP 4: MQTT CONNECTION")
        print("="*60)
        print(f"Connecting to MQTT broker: {self.mqtt_host}:{self.mqtt_port}")
        
        if not self.config or not self.config.mqtt_username:
            print("❌ No MQTT credentials available. Please register device first.")
            return False
        
        # Create MQTT client
        client_id = f"{self.config.device_id}-{int(time.time())}"
        
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        except:
            self.mqtt_client = mqtt.Client(client_id=client_id)
        
        # Set username and password
        self.mqtt_client.username_pw_set(
            self.config.mqtt_username,
            self.config.mqtt_password
        )
        print(f"📝 Using device-specific MQTT credentials: {self.config.mqtt_username}")
        
        # Setup TLS
        if self.ca_cert_path:
            print(f"🔒 Setting up TLS with CA certificate: {self.ca_cert_path}")
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_REQUIRED
            context.load_verify_locations(cafile=self.ca_cert_path)
            self.mqtt_client.tls_set_context(context=context)
        else:
            print("⚠️  No CA certificate - attempting connection without TLS verification")
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.mqtt_client.tls_set_context(context=context)
        
        # Set callbacks
        def on_connect(client, userdata, flags, rc, properties=None):
            if rc == 0:
                print("✅ MQTT connected successfully!")
                self.connected = True
            else:
                print(f"❌ MQTT connection failed with code: {rc}")
                self.connected = False
        
        def on_disconnect(client, userdata, rc, properties=None, reason_code=None):
            print(f"⚠️  MQTT disconnected with code: {rc}")
            self.connected = False
        
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_disconnect = on_disconnect
        
        # Connect
        try:
            print(f"🔌 Connecting to {self.mqtt_host}:{self.mqtt_port}...")
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, keepalive=60)
            self.mqtt_client.loop_start()
            
            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            return self.connected
            
        except Exception as e:
            print(f"❌ MQTT connection error: {str(e)}")
            return False
    
    def step5_send_gps_data(self, num_messages: int = 5, flight_id: str = None) -> bool:
        """
        STEP 5: Send GPS Data
        Device sends GPS tracking data to the platform.
        Now supports flight sessions with device-generated flight IDs.
        """
        print("\n" + "="*60)
        print("STEP 5: SENDING GPS DATA")
        print("="*60)
        
        if not self.connected:
            print("❌ Not connected to MQTT. Please connect first.")
            return False
        
        # Generate flight ID if not provided
        if flight_id is None:
            import uuid
            flight_id = str(uuid.uuid4())
            print(f"✈️  Starting new flight session: {flight_id}")
        else:
            print(f"✈️  Continuing flight session: {flight_id}")
        
        # Simulate GPS location (Chamonix, France - paragliding location)
        base_lat = 45.9237
        base_lon = 6.8694
        altitude = 2400
        
        print(f"📍 Sending {num_messages} GPS updates...")
        print(f"   Base location: {base_lat:.4f}, {base_lon:.4f}")
        print(f"   Altitude: {altitude}m")
        print()
        
        for i in range(num_messages):
            # Simulate movement
            lat = base_lat + random.uniform(-0.001, 0.001)
            lon = base_lon + random.uniform(-0.001, 0.001)
            altitude += random.uniform(-10, 10)
            
            # Prepare GPS data
            gps_data = {
                "device_id": self.config.device_id,
                "flight_id": flight_id,  # Include flight session ID
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "altitude": round(altitude, 1),
                "speed": round(random.uniform(0, 50), 1),
                "heading": round(random.uniform(0, 360), 1),
                "accuracy": round(random.uniform(3, 10), 1),
                "satellites": random.randint(8, 15),
                "battery_level": round(100 - (i * 0.5), 1),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "device_metadata": {
                    "message_num": i + 1,
                    "test_mode": True,
                    "flight_session": flight_id
                }
            }
            
            # Create HMAC signature
            canonical = json.dumps(gps_data, sort_keys=True, separators=(',', ':'))
            signature = hmac.new(
                self.config.device_secret.encode(),
                canonical.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Prepare MQTT message
            message = {
                "data": gps_data,
                "signature": signature,
                "api_key": self.config.api_key
            }
            
            # Publish to MQTT
            topic = f"gps/{self.config.device_id}/data"
            payload = json.dumps(message)
            
            result = self.mqtt_client.publish(topic, payload, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"✓ Message {i+1}: lat={lat:.6f}, lon={lon:.6f}, alt={altitude:.1f}m")
            else:
                print(f"❌ Failed to send message {i+1}: {result.rc}")
            
            # Wait between messages
            time.sleep(1)
        
        print("\n✅ GPS data transmission complete!")
        return True
    
    def step5_send_gps_batch(self, num_batches: int = 3, batch_size: int = 10, flight_id: str = None):
        """Step 5B: Send GPS data in batches (power-efficient mode)"""
        print("\n" + "="*60)
        print("STEP 5B: SENDING GPS DATA IN BATCHES")
        print("="*60)
        
        if not self.connected:
            print("❌ Not connected to MQTT. Please connect first.")
            return False
        
        # Generate flight ID if not provided
        if flight_id is None:
            import uuid
            flight_id = str(uuid.uuid4())
            print(f"✈️  Starting new flight session: {flight_id}")
        else:
            print(f"✈️  Continuing flight session: {flight_id}")
        
        # Simulate GPS location (Chamonix, France - paragliding location)
        base_lat = 45.9237
        base_lon = 6.8694
        altitude = 2400
        
        print(f"📦 Sending {num_batches} batches of {batch_size} GPS points each...")
        print(f"   Base location: {base_lat:.4f}, {base_lon:.4f}")
        print(f"   Altitude: {altitude}m")
        print()
        
        total_points = 0
        
        for batch_num in range(num_batches):
            # Collect batch of GPS points
            batch_data = []
            
            for i in range(batch_size):
                # Simulate movement
                lat = base_lat + random.uniform(-0.001, 0.001)
                lon = base_lon + random.uniform(-0.001, 0.001)
                altitude += random.uniform(-10, 10)
                
                # Prepare GPS data point
                gps_point = {
                    "device_id": self.config.device_id,
                    "flight_id": flight_id,
                    "latitude": round(lat, 6),
                    "longitude": round(lon, 6),
                    "altitude": round(altitude, 1),
                    "speed": round(random.uniform(0, 50), 1),
                    "heading": round(random.uniform(0, 360), 1),
                    "accuracy": round(random.uniform(3, 10), 1),
                    "satellites": random.randint(8, 15),
                    "battery_level": round(100 - (total_points * 0.5), 1),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "device_metadata": {
                        "batch_num": batch_num + 1,
                        "point_num": i + 1,
                        "test_mode": True,
                        "flight_session": flight_id
                    }
                }
                
                batch_data.append(gps_point)
                total_points += 1
                
                # Small delay to simulate time between readings
                time.sleep(0.1)
            
            # Create HMAC signature for the entire batch
            canonical = json.dumps(batch_data, sort_keys=True, separators=(',', ':'))
            signature = hmac.new(
                self.config.device_secret.encode(),
                canonical.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Prepare MQTT batch message
            batch_message = {
                "data": batch_data,  # Array of GPS points
                "signature": signature,
                "api_key": self.config.api_key
            }
            
            # Publish batch to MQTT
            topic = f"gps/{self.config.device_id}/data"
            payload = json.dumps(batch_message)
            
            result = self.mqtt_client.publish(topic, payload, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"✓ Batch {batch_num + 1}: Sent {batch_size} points")
                print(f"  Size: {len(payload)} bytes")
                print(f"  Last point: lat={lat:.6f}, lon={lon:.6f}, alt={altitude:.1f}m")
            else:
                print(f"❌ Failed to send batch {batch_num + 1}: {result.rc}")
            
            # Wait between batches
            if batch_num < num_batches - 1:
                print("  Waiting 5 seconds before next batch...")
                time.sleep(5)
        
        print(f"\n✅ Batch transmission complete! Sent {total_points} points in {num_batches} batches")
        return True
    
    def test_http_batch(self, num_points: int = 30, flight_id: str = None):
        """Test HTTP batch API endpoint"""
        print("\n" + "="*60)
        print("HTTP BATCH API TEST")
        print("="*60)
        
        if not self.config.api_key:
            print("❌ No API key. Please register device first.")
            return False
        
        # Generate flight ID if not provided
        if flight_id is None:
            import uuid
            flight_id = str(uuid.uuid4())
            print(f"✈️  Starting new flight session: {flight_id}")
        
        # Collect GPS points
        base_lat = 45.9237
        base_lon = 6.8694
        altitude = 2400
        
        print(f"📦 Preparing batch of {num_points} GPS points...")
        
        batch_data = []
        for i in range(num_points):
            # Simulate movement
            lat = base_lat + random.uniform(-0.001, 0.001)
            lon = base_lon + random.uniform(-0.001, 0.001)
            altitude += random.uniform(-10, 10)
            
            gps_point = {
                "device_id": self.config.device_id,
                "flight_id": flight_id,
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "altitude": round(altitude, 1),
                "speed": round(random.uniform(0, 50), 1),
                "heading": round(random.uniform(0, 360), 1),
                "accuracy": round(random.uniform(3, 10), 1),
                "satellites": random.randint(8, 15),
                "battery_level": round(100 - (i * 0.5), 1),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            batch_data.append(gps_point)
        
        # Send via HTTP API
        try:
            response = requests.post(
                f"{self.api_url}/gps/batch",
                json={"data": batch_data},
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ HTTP batch sent successfully!")
                print(f"   Response: {result}")
                return True
            else:
                print(f"❌ HTTP batch failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ HTTP batch error: {e}")
            return False
    
    def run_complete_test(self, device_num: int, manufacturer_secret: str, device_id: str = None,
                          batch_mode: bool = False, batch_size: int = 10, num_batches: int = 3,
                          test_http_batch: bool = False, num_messages: int = 10):
        """Run the complete device lifecycle test"""
        print("\n" + "🚀 " + "="*58)
        print("    MANUFACTURER DEVICE INTEGRATION TEST")
        print("    Simulating Complete Device Lifecycle")
        print("="*60)
        
        # Step 1: Factory provisioning
        config = self.step1_factory_provisioning(device_num, manufacturer_secret, device_id)
        
        # Save config (simulating device storage)
        config_file = f"/tmp/device_config_{device_num}.json"
        config.save_to_file(config_file)
        print(f"\n💾 Device configuration saved to: {config_file}")
        
        # Simulate device shipment and first boot
        print("\n📦 Device shipped to customer...")
        print("⏰ Simulating first boot by end user...")
        time.sleep(2)
        
        # Step 2: Device registration
        if not self.step2_device_registration(config):
            print("\n❌ Device registration failed. Cannot continue.")
            return False
        
        # Step 3: Download CA certificate
        self.step3_download_ca_certificate()
        
        # Step 4: MQTT connection
        if not self.step4_mqtt_connection():
            print("\n❌ MQTT connection failed. Cannot send data.")
            return False
        
        # Step 5: Send GPS data
        if batch_mode:
            if not self.step5_send_gps_batch(num_batches=num_batches, batch_size=batch_size):
                print("\n❌ Failed to send GPS batch data.")
                return False
        else:
            if not self.step5_send_gps_data(num_messages=num_messages):
                print("\n❌ Failed to send GPS data.")
                return False
        
        # Step 6: Test HTTP batch if requested
        if test_http_batch:
            self.test_http_batch(num_points=30)
        
        # Cleanup
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        
        print("\n" + "="*60)
        print("✅ DEVICE INTEGRATION TEST COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nSummary:")
        print(f"  - Device ID: {config.device_id}")
        print(f"  - Registration: Success")
        print(f"  - MQTT Connection: Success")
        print(f"  - GPS Data Sent: Success")
        print("\nThis device is now successfully integrated with the platform!")
        
        return True
    
    def run_flight_only(self, config_file: str, num_messages: int = 5, batch_mode: bool = False,
                        batch_size: int = 10, num_batches: int = 3, test_http_batch: bool = False):
        """Run only the flight portion with existing device config."""
        print("\n" + "✈️ " + "="*58)
        print("    FLIGHT SESSION ONLY")
        print("    Using Existing Device Configuration")
        print("="*60)
        
        # Load existing config
        self.config = DeviceConfig.load_from_file(config_file)
        print(f"\n📱 Loaded device config for: {self.config.device_id}")
        
        # Step 3: Download CA certificate
        self.step3_download_ca_certificate()
        
        # Step 4: MQTT connection
        if not self.step4_mqtt_connection():
            print("\n❌ MQTT connection failed. Cannot send data.")
            return False
        
        # Step 5: Send GPS data with new flight ID
        if batch_mode:
            if not self.step5_send_gps_batch(num_batches=num_batches, batch_size=batch_size):
                print("\n❌ Failed to send GPS batch data.")
                return False
        else:
            if not self.step5_send_gps_data(num_messages=num_messages):
                print("\n❌ Failed to send GPS data.")
                return False
        
        # Test HTTP batch if requested
        if test_http_batch:
            self.test_http_batch(num_points=30)
        
        # Cleanup
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        
        print("\n✅ FLIGHT SESSION COMPLETED!")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Manufacturer Device Integration Test - Simulates complete device lifecycle"
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help="API base URL (default: http://localhost/api/v1)"
    )
    parser.add_argument(
        "--mqtt-host",
        default=DEFAULT_MQTT_HOST,
        help="MQTT broker hostname (default: localhost)"
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=DEFAULT_MQTT_PORT,
        help="MQTT broker port (default: 8883)"
    )
    parser.add_argument(
        "--device-num",
        type=int,
        default=1,
        help="Device number for unique ID generation (default: 1)"
    )
    parser.add_argument(
        "--manufacturer-secret",
        help="Manufacturer secret for device provisioning (required for new devices)"
    )
    parser.add_argument(
        "--ca-cert",
        help="Path to CA certificate for MQTT TLS (optional, will try to download if not provided)"
    )
    parser.add_argument(
        "--device-id",
        help="Specific device ID to use (optional, will generate if not provided)"
    )
    parser.add_argument(
        "--skip-registration",
        action="store_true",
        help="Skip device registration (use existing device)"
    )
    parser.add_argument(
        "--config-file",
        help="Path to existing device config file (for reusing registered device)"
    )
    parser.add_argument(
        "--batch-mode",
        action="store_true",
        help="Send GPS data in batches instead of individual messages"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of GPS points per batch (default: 10)"
    )
    parser.add_argument(
        "--num-batches",
        type=int,
        default=3,
        help="Number of batches to send (default: 3)"
    )
    parser.add_argument(
        "--test-http-batch",
        action="store_true",
        help="Test HTTP batch API endpoint"
    )
    parser.add_argument(
        "--num-messages",
        type=int,
        default=10,
        help="Number of individual GPS messages to send (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Create device simulator
    device = ManufacturerDevice(
        api_url=args.api_url,
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        ca_cert_path=args.ca_cert
    )
    
    # Check if we should run flight only
    if args.config_file:
        success = device.run_flight_only(
            config_file=args.config_file,
            num_messages=args.num_messages,
            batch_mode=args.batch_mode,
            batch_size=args.batch_size,
            num_batches=args.num_batches,
            test_http_batch=args.test_http_batch
        )
    else:
        # Validate required args for new device
        if not args.manufacturer_secret:
            parser.error("--manufacturer-secret is required when creating new devices")
        
        # Run complete test
        success = device.run_complete_test(
            device_num=args.device_num,
            manufacturer_secret=args.manufacturer_secret,
            device_id=args.device_id,
            batch_mode=args.batch_mode,
            batch_size=args.batch_size,
            num_batches=args.num_batches,
            test_http_batch=args.test_http_batch,
            num_messages=args.num_messages
        )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
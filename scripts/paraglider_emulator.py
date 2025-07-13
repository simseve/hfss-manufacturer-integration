#!/usr/bin/env python3
"""
Paraglider Traffic Emulator - Simulates realistic paraglider GPS tracking patterns
including takeoffs, flights, thermals, landings, and device lifecycle.
"""
import json
import time
import random
import math
import threading
import paho.mqtt.client as mqtt
import ssl
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
import argparse
import sys
import os
from dataclasses import dataclass
from typing import List, Dict, Tuple
from enum import Enum
import requests
from dotenv import load_dotenv
import subprocess
import urllib.request

# Load environment variables
load_dotenv()

def download_ca_certificate():
    """Download CA certificate if not present"""
    if not os.path.exists(CA_CERT):
        print(f"📥 Downloading CA certificate from {DEFAULT_DOMAIN}...")
        try:
            # Method 1: Try with urllib
            req = urllib.request.Request(f"https://{DEFAULT_DOMAIN}/ca.crt")
            req.add_header('User-Agent', 'Mozilla/5.0 (Paraglider-Emulator)')
            response = urllib.request.urlopen(req)
            ca_data = response.read()
            
            with open(CA_CERT, 'wb') as f:
                f.write(ca_data)
            print(f"✅ CA certificate downloaded successfully to {CA_CERT}")
        except Exception as e:
            print(f"❌ Failed to download CA certificate: {e}")
            # Method 2: Try with curl as fallback
            try:
                result = subprocess.run(
                    ["curl", "-o", CA_CERT, f"https://{DEFAULT_DOMAIN}/ca.crt"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print(f"✅ CA certificate downloaded successfully using curl")
                else:
                    print(f"❌ Failed to download with curl: {result.stderr}")
                    sys.exit(1)
            except Exception as e2:
                print(f"❌ Failed to download with curl: {e2}")
                sys.exit(1)
    else:
        print(f"✅ CA certificate already exists at {CA_CERT}")

# Configuration
DEFAULT_DOMAIN = "dg-dev.hikeandfly.app"
API_BASE_URL = f"https://{DEFAULT_DOMAIN}/api/v1"
MQTT_HOST = "dg-mqtt.hikeandfly.app"
MQTT_PORT = 8883  # TLS port
MQTT_USER = os.getenv("MQTT_USER", "mqtt_user")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "mqtt_secure_password")
MANUFACTURER = "DIGIFLY"
MANUFACTURER_SECRET = os.getenv("MANUFACTURER_SECRET_DIGIFLY", "GziZ46Tr4ANkhKh75lFnPtOrTkLgfHWe")

# TLS Certificate paths
CA_CERT = "./ca.crt"  # Downloaded from production
CLIENT_CERT = None  # Not needed for production
CLIENT_KEY = None   # Not needed for production

# Known flying sites (lat, lon, takeoff_altitude)
FLYING_SITES = [
    {"name": "Chamonix", "lat": 45.9237, "lon": 6.8694, "alt": 2400, "land_alt": 1050},
    {"name": "Interlaken", "lat": 46.6863, "lon": 7.8632, "alt": 1800, "land_alt": 570},
    {"name": "Annecy", "lat": 45.8992, "lon": 6.1294, "alt": 1450, "land_alt": 450},
    {"name": "Zermatt", "lat": 46.0207, "lon": 7.7491, "alt": 2800, "land_alt": 1620},
    {"name": "Dolomites", "lat": 46.4102, "lon": 11.8440, "alt": 2200, "land_alt": 1000},
]

class FlightPhase(Enum):
    GROUND = "ground"
    TAKEOFF = "takeoff"
    CLIMBING = "climbing"
    GLIDING = "gliding"
    THERMALING = "thermaling"
    LANDING = "landing"
    LANDED = "landed"

@dataclass
class Thermal:
    """Represents a thermal (rising air column)"""
    lat: float
    lon: float
    radius: float  # meters
    strength: float  # m/s vertical speed
    top_altitude: float  # meters

@dataclass
class Paraglider:
    """Represents a paraglider device and pilot"""
    device_id: str
    api_key: str
    device_secret: str
    pilot_name: str
    site: dict
    lat: float
    lon: float
    altitude: float
    speed: float  # km/h
    heading: float  # degrees
    vario: float  # m/s vertical speed
    phase: FlightPhase
    battery: float
    start_time: datetime
    last_update: datetime
    thermal: Thermal = None
    target_landing: Tuple[float, float] = None
    mqtt_client: mqtt.Client = None
    active: bool = True
    flight_time: int = 0  # minutes
    flight_id: str = None  # UUID for flight session

class ParagliderSimulator:
    def __init__(self, num_devices: int, duration_minutes: int = 60):
        self.num_devices = num_devices
        self.duration_minutes = duration_minutes
        self.paragliders: List[Paraglider] = []
        self.thermals: List[Thermal] = []
        self.running = True
        self.start_time = datetime.now()
        self.registered_count = 0
        self.active_flights = 0
        self.total_points_sent = 0
        self.lock = threading.Lock()
        self.mqtt_pool = []  # Connection pool for high device counts
        self.mqtt_pool_lock = threading.Lock()
        self.pool_index = 0
        self.last_throughput_time = time.time()
        self.last_throughput_count = 0
        self.current_throughput = 0.0
        
    def generate_thermals(self, site: dict, num_thermals: int = 10):
        """Generate random thermals around a flying site"""
        thermals = []
        for _ in range(num_thermals):
            # Thermals within 7km of launch for more options
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(300, 7000)  # meters
            
            lat = site["lat"] + (distance * math.cos(angle)) / 111111
            lon = site["lon"] + (distance * math.sin(angle)) / (111111 * math.cos(math.radians(site["lat"])))
            
            thermal = Thermal(
                lat=lat,
                lon=lon,
                radius=random.uniform(50, 300),  # Larger thermals
                strength=random.uniform(1.0, 5.0),  # More variety in strength
                top_altitude=site["alt"] + random.uniform(300, 2000)  # More altitude variation
            )
            thermals.append(thermal)
        return thermals
    
    def register_device(self, device_num: int) -> dict:
        """Register a new paraglider device"""
        # Add timestamp to ensure unique device IDs
        timestamp = int(time.time() * 1000) % 100000
        device_id = f"PARA-{datetime.now().strftime('%Y%m%d')}-{timestamp}-{device_num:04d}"
        device_secret = f"secret_{device_id}_0"
        
        # Generate registration token
        message = f"{MANUFACTURER}:{device_id}:{device_secret}"
        registration_token = hmac.new(
            MANUFACTURER_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        payload = {
            "device_id": device_id,
            "manufacturer": MANUFACTURER,
            "registration_token": registration_token,
            "device_secret": device_secret,
            "name": f"Paraglider Tracker #{device_num}",
            "device_type": "PARAGLIDER_TRACKER",
            "firmware_version": "2.1.0",
            "device_info": {
                "pilot": f"Pilot_{device_num}",
                "glider_model": random.choice(["Advance Omega", "Ozone Enzo", "Gin Boomerang", "Nova Mentor"]),
                "harness": random.choice(["Woody Valley", "Advance", "Supair", "Kortel"]),
                "reserve": "Yes",
                "battery_capacity": 5000
            }
        }
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/devices/register",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30  # Increased timeout for stressed system
            )
            
            if response.status_code == 200:
                result = response.json()
                result['device_secret'] = device_secret
                return result
            elif response.status_code == 400:
                # Device might already exist, try a different ID
                new_device_num = device_num + 1000 + random.randint(0, 999)
                return self.register_device(new_device_num)
            else:
                # Log errors for debugging but don't spam
                if response.status_code != 503:
                    print(f"Registration failed for {device_id}: HTTP {response.status_code}")
                return None
        except requests.exceptions.ConnectionError:
            # Connection error - API might be overwhelmed
            return None
        except Exception as e:
            # Other errors
            if "timeout" not in str(e).lower():
                print(f"Registration error for {device_id}: {type(e).__name__}")
            return None
    
    def create_tls_context(self):
        """Create TLS/SSL context for MQTT"""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(cafile=CA_CERT)
        # Don't load client certificates - we use username/password auth
        return context
    
    def create_mqtt_pool(self, pool_size=50):
        """Create a pool of MQTT connections for high device counts"""
        print(f"Creating MQTT connection pool with {pool_size} connections...")
        # For pool connections, we use the API MQTT credentials since they're shared
        # Individual devices still sign their messages with their own secrets
        for i in range(pool_size):
            try:
                client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"pool-{i}-{int(time.time())}")
            except:
                client = mqtt.Client(client_id=f"pool-{i}-{int(time.time())}")
            
            # Use API MQTT credentials for shared pool connections
            client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
            client.tls_set_context(context=self.create_tls_context())
            
            try:
                client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
                client.loop_start()
                self.mqtt_pool.append(client)
            except Exception as e:
                print(f"Failed to create pool connection {i}: {e}")
        
        print(f"Created {len(self.mqtt_pool)} pool connections")
    
    def get_pool_client(self):
        """Get next available client from pool (round-robin)"""
        with self.mqtt_pool_lock:
            if not self.mqtt_pool:
                return None
            client = self.mqtt_pool[self.pool_index % len(self.mqtt_pool)]
            self.pool_index += 1
            return client
    
    def create_paraglider(self, device_info: dict, site: dict) -> Paraglider:
        """Create a new paraglider instance"""
        # Start position with some randomness
        lat_offset = random.uniform(-0.001, 0.001)
        lon_offset = random.uniform(-0.001, 0.001)
        
        paraglider = Paraglider(
            device_id=device_info['device_id'],
            api_key=device_info['api_key'],
            device_secret=device_info['device_secret'],
            pilot_name=f"Pilot_{device_info['device_id'][-4:]}",
            site=site,
            lat=site["lat"] + lat_offset,
            lon=site["lon"] + lon_offset,
            altitude=site["alt"] + random.uniform(-20, 20),
            speed=0,
            heading=random.uniform(0, 360),
            vario=0,
            phase=FlightPhase.GROUND,
            battery=random.uniform(85, 100),
            start_time=datetime.now(timezone.utc),
            last_update=datetime.now(timezone.utc)
        )
        
        # Setup MQTT client with connection reuse for high device counts
        if self.num_devices > 50:
            # For large simulations, reuse connections in batches
            # This prevents "Too many open files" errors
            paraglider.mqtt_client = None  # Will use shared publishing
        else:
            # For smaller simulations, use individual connections
            try:
                # Use VERSION2 to avoid deprecation warning
                client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"{device_info['device_id']}-{int(time.time())}")
            except:
                # Fallback to old API
                client = mqtt.Client(client_id=f"{device_info['device_id']}-{int(time.time())}")
            
            # Use per-device MQTT credentials from registration
            mqtt_username = device_info.get('mqtt_username', f"device_{device_info['device_id']}")
            mqtt_password = device_info.get('mqtt_password', MQTT_PASSWORD)
            client.username_pw_set(mqtt_username, mqtt_password)
            client.tls_set_context(context=self.create_tls_context())
            
            try:
                client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
                client.loop_start()
                paraglider.mqtt_client = client
                # No delay - start sending immediately
            except Exception as e:
                print(f"MQTT connection failed for {device_info['device_id']}: {e}")
                paraglider.mqtt_client = None
            
        return paraglider
    
    def send_gps_update(self, para: Paraglider):
        """Send GPS update via MQTT"""
        if not para.active:
            return
            
        # Use individual client or pool
        client = para.mqtt_client
        if not client:
            client = self.get_pool_client()
            if not client:
                return
            
        gps_data = {
            "device_id": para.device_id,
            "flight_id": para.flight_id if hasattr(para, 'flight_id') else None,
            "latitude": round(para.lat, 6),
            "longitude": round(para.lon, 6),
            "altitude": round(para.altitude, 1),
            "speed": round(para.speed, 1),
            "heading": round(para.heading, 1),
            "accuracy": round(random.uniform(3, 8), 1),
            "satellites": random.randint(8, 15),
            "battery_level": round(para.battery, 1),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_metadata": {
                "vario": round(para.vario, 1),
                "phase": para.phase.value,
                "flight_time": para.flight_time,
                "pilot": para.pilot_name
            }
        }
        
        # Create signature
        canonical = json.dumps(gps_data, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            para.device_secret.encode(),
            canonical.encode(),
            hashlib.sha256
        ).hexdigest()
        
        message = {
            "data": gps_data,
            "signature": signature,
            "api_key": para.api_key
        }
        
        topic = f"gps/{para.device_id}/data"
        try:
            result = client.publish(topic, json.dumps(message), qos=1)
            # For QoS 1, check rc (return code) instead of is_published()
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                with self.lock:
                    self.total_points_sent += 1
                    
                    # Update throughput calculation
                    current_time = time.time()
                    time_diff = current_time - self.last_throughput_time
                    if time_diff >= 1.0:  # Update throughput every second
                        count_diff = self.total_points_sent - self.last_throughput_count
                        self.current_throughput = count_diff / time_diff
                        self.last_throughput_time = current_time
                        self.last_throughput_count = self.total_points_sent
            else:
                print(f"Failed to publish for {para.device_id}: rc={result.rc}")
        except Exception as e:
            print(f"Failed to send GPS for {para.device_id}: {e}")
    
    def update_paraglider_physics(self, para: Paraglider, dt: float = 1.0):
        """Update paraglider position based on physics"""
        # Battery drain
        para.battery -= random.uniform(0.01, 0.03)
        para.flight_time = int((datetime.now(timezone.utc) - para.start_time).total_seconds() / 60)
        
        # Phase transitions and physics
        if para.phase == FlightPhase.GROUND:
            # Random chance to take off - increased probability
            if random.random() < 0.05:  # 5% chance per update
                para.phase = FlightPhase.TAKEOFF
                para.speed = 25
                para.vario = 2.0
                para.heading = random.uniform(0, 360)  # Random takeoff direction
                # Generate new flight ID for this flight session
                import uuid
                para.flight_id = str(uuid.uuid4())
            else:
                # Small ground movements (taxi, preparation)
                if random.random() < 0.3:  # 30% chance to move on ground
                    para.speed = random.uniform(2, 5)  # Walking speed
                    para.heading += random.uniform(-45, 45)
                    para.heading = para.heading % 360
                
        elif para.phase == FlightPhase.TAKEOFF:
            # Accelerate and climb with dynamic movements
            para.speed = min(40, para.speed + random.uniform(1, 3))
            para.vario = random.uniform(1.5, 3.0)  # Variable climb rate
            para.altitude += para.vario * dt
            
            # Add some turbulence during takeoff
            para.heading += random.uniform(-10, 10)
            para.heading = para.heading % 360
            
            # Transition to climbing after gaining some altitude
            if para.altitude > para.site["alt"] + 50:
                para.phase = FlightPhase.CLIMBING
                
        elif para.phase == FlightPhase.CLIMBING:
            # Dynamic search for thermals with continuous movement
            para.speed = random.uniform(35, 45)  # Maintain flying speed
            para.vario = max(-2, para.vario - random.uniform(0.1, 0.4))  # Variable sink rate
            para.altitude += para.vario * dt
            
            # Actively search for thermals by changing direction
            para.heading += random.uniform(-20, 20)  # Search pattern
            para.heading = para.heading % 360
            
            # Check for nearby thermals
            for thermal in self.thermals:
                dist = self.calculate_distance(para.lat, para.lon, thermal.lat, thermal.lon)
                if dist < thermal.radius and para.altitude < thermal.top_altitude:
                    para.phase = FlightPhase.THERMALING
                    para.thermal = thermal
                    break
            else:
                # No thermal found, start gliding
                if para.vario < -1 or random.random() < 0.1:  # 10% chance to give up searching
                    para.phase = FlightPhase.GLIDING
                    
        elif para.phase == FlightPhase.THERMALING:
            # Circle in thermal with dynamic radius and speed
            if para.thermal:
                # Variable turn rate for realistic circling
                turn_rate = random.uniform(12, 18)  # degrees per second
                para.heading = (para.heading + turn_rate) % 360
                
                # Dynamic spiral radius (tighter or wider circles)
                radius = random.uniform(30, 70)  # meters
                angle_rad = math.radians(para.heading)
                
                # Add drift to thermal (thermals move with wind)
                wind_drift = random.uniform(0, 2) / 3.6  # 0-2 km/h in m/s
                wind_dir = random.uniform(0, 360)
                
                # Update position relative to thermal center with drift
                para.lat = para.thermal.lat + (radius * math.cos(angle_rad)) / 111111
                para.lon = para.thermal.lon + (radius * math.sin(angle_rad)) / (111111 * math.cos(math.radians(para.lat)))
                
                # Variable climb rate in thermal
                para.vario = para.thermal.strength * random.uniform(0.6, 1.2)
                para.altitude += para.vario * dt
                para.speed = random.uniform(30, 40)  # Speed while thermaling
                
                # Leave thermal if too high or randomly
                if para.altitude > para.thermal.top_altitude or random.random() < 0.02:
                    para.phase = FlightPhase.GLIDING
                    para.thermal = None
                    para.speed = random.uniform(40, 50)  # Exit speed
                    
        elif para.phase == FlightPhase.GLIDING:
            # Dynamic gliding with speed variations
            para.vario = random.uniform(-1.8, -0.5)  # Variable sink rate
            para.altitude += para.vario * dt
            para.speed = random.uniform(35, 50)  # Variable glide speed
            
            # More dynamic heading changes (searching, avoiding obstacles)
            heading_change = random.uniform(-15, 15)
            para.heading = (para.heading + heading_change) % 360
            
            # Speed adjustments based on vario
            if para.vario < -1.5:  # Sinking fast
                para.speed = min(55, para.speed + 2)  # Speed up to find lift
            
            # Occasionally find weak lift
            if random.random() < 0.05:  # 5% chance
                para.vario = random.uniform(0, 1.0)  # Weak lift
            
            # Check if need to start landing
            if para.altitude < para.site["land_alt"] + 200:
                para.phase = FlightPhase.LANDING
                # Set landing target
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(100, 1000)
                land_lat = para.site["lat"] + (distance * math.cos(angle)) / 111111
                land_lon = para.site["lon"] + (distance * math.sin(angle)) / (111111 * math.cos(math.radians(para.site["lat"])))
                para.target_landing = (land_lat, land_lon)
                
        elif para.phase == FlightPhase.LANDING:
            # Dynamic final approach with corrections
            if para.target_landing:
                # Navigate towards landing spot with corrections
                bearing = self.calculate_bearing(para.lat, para.lon, para.target_landing[0], para.target_landing[1])
                turn_needed = self.smooth_turn(para.heading, bearing, 15)
                para.heading = turn_needed
                
                # Add some turbulence during landing
                para.heading += random.uniform(-5, 5)
                para.heading = para.heading % 360
                
            # Dynamic speed reduction
            para.speed = max(18, para.speed - random.uniform(1, 3))
            para.vario = max(-4, para.vario - random.uniform(0.1, 0.3))
            para.altitude += para.vario * dt
            
            # Ground effect - reduced sink rate near ground
            if para.altitude < para.site["land_alt"] + 20:
                para.vario = max(-2, para.vario)
            
            # Touchdown
            if para.altitude <= para.site["land_alt"]:
                para.phase = FlightPhase.LANDED
                para.altitude = para.site["land_alt"]
                para.speed = 0
                para.vario = 0
                
        elif para.phase == FlightPhase.LANDED:
            # On ground, pack up and prepare for next flight
            if random.random() < 0.03:  # 3% chance to go again
                # Reset for another flight
                para.phase = FlightPhase.GROUND
                para.lat = para.site["lat"] + random.uniform(-0.001, 0.001)
                para.lon = para.site["lon"] + random.uniform(-0.001, 0.001)
                para.altitude = para.site["alt"]
                para.heading = random.uniform(0, 360)
                para.flight_id = None  # Reset flight_id for next flight
            else:
                # Small movements while packing up
                if random.random() < 0.2:
                    para.lat += random.uniform(-0.00001, 0.00001)
                    para.lon += random.uniform(-0.00001, 0.00001)
                
        # Always update position based on speed and heading
        if para.speed > 0:
            # Convert speed from km/h to m/s
            speed_ms = para.speed / 3.6
            
            # Calculate new position
            distance = speed_ms * dt
            heading_rad = math.radians(para.heading)
            
            # Add wind effect for more dynamic movement
            wind_speed = random.uniform(0, 10) / 3.6  # 0-10 km/h wind
            wind_dir = random.uniform(0, 360)
            wind_rad = math.radians(wind_dir)
            
            # Calculate total movement including wind
            lat_change = (distance * math.cos(heading_rad)) / 111111
            lon_change = (distance * math.sin(heading_rad)) / (111111 * math.cos(math.radians(para.lat)))
            
            # Add wind drift
            lat_change += (wind_speed * dt * math.cos(wind_rad)) / 111111
            lon_change += (wind_speed * dt * math.sin(wind_rad)) / (111111 * math.cos(math.radians(para.lat)))
            
            para.lat += lat_change
            para.lon += lon_change
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in meters"""
        R = 6371000  # Earth radius in meters
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        """Calculate bearing between two points"""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lon = math.radians(lon2 - lon1)
        
        x = math.sin(delta_lon) * math.cos(lat2_rad)
        y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
        
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360
    
    def smooth_turn(self, current_heading, target_heading, max_turn):
        """Smoothly turn towards target heading"""
        diff = target_heading - current_heading
        
        # Normalize to -180 to 180
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360
            
        # Limit turn rate
        if abs(diff) > max_turn:
            diff = max_turn if diff > 0 else -max_turn
            
        return (current_heading + diff) % 360
    
    def simulate_paraglider(self, para: Paraglider):
        """Simulate a single paraglider"""
        update_interval = 1  # seconds - aggressive update rate
        
        while self.running and para.active:
            # Update physics
            self.update_paraglider_physics(para, update_interval)
            
            # Send GPS update
            self.send_gps_update(para)
            
            # Check battery
            if para.battery < 5:
                print(f"🔋 {para.device_id} battery depleted")
                para.active = False
                break
                
            time.sleep(update_interval)
        
        # Cleanup
        if para.mqtt_client:
            para.mqtt_client.loop_stop()
            para.mqtt_client.disconnect()
    
    def print_statistics(self):
        """Print current simulation statistics"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        # Count active flights by phase
        phase_counts = {}
        for para in self.paragliders:
            if para.active:
                phase = para.phase.value
                phase_counts[phase] = phase_counts.get(phase, 0) + 1
        
        print(f"\n📊 Paraglider Traffic Simulation Statistics")
        print(f"{'='*50}")
        print(f"Elapsed Time: {int(elapsed)}s")
        print(f"Registered Devices: {self.registered_count}/{self.num_devices}")
        print(f"Total GPS Points Sent: {self.total_points_sent}")
        print(f"Average Rate: {self.total_points_sent/elapsed:.1f} points/sec")
        print(f"Current Throughput: {self.current_throughput:.1f} msgs/sec")
        print(f"\n🪂 Active Flights by Phase:")
        for phase, count in sorted(phase_counts.items()):
            print(f"  {phase.capitalize()}: {count}")
        print(f"  Total Active: {sum(phase_counts.values())}")
    
    def run(self):
        """Run the paraglider simulation"""
        print(f"🪂 Starting Paraglider Traffic Emulator")
        print(f"Devices: {self.num_devices}")
        print(f"Duration: {self.duration_minutes} minutes")
        print(f"Flying Sites: {len(FLYING_SITES)}")
        print("="*60)
        
        # Generate thermals for each site
        for site in FLYING_SITES:
            self.thermals.extend(self.generate_thermals(site))
        
        # Create connection pool for high device counts
        if self.num_devices > 500:
            pool_size = min(50, max(10, self.num_devices // 20))  # 5% of devices, min 10, max 50
            self.create_mqtt_pool(pool_size)
        
        # Phase 1: Register devices and start transmitting immediately
        print("\n📝 Phase 1: Registering devices and starting flights...")
        from concurrent.futures import ThreadPoolExecutor
        max_threads = min(1000, self.num_devices)  # Increased to 1000 threads
        
        device_infos = []
        self.simulation_executor = ThreadPoolExecutor(max_workers=max_threads)
        
        def register_and_start(device_num):
            # Try to register device with retries
            max_retries = 3
            for attempt in range(max_retries):
                info = self.register_device(device_num)
                if info:
                    with self.lock:
                        device_infos.append(info)
                        self.registered_count += 1
                        if self.registered_count % 100 == 0:
                            print(f"  Registered and started {self.registered_count}/{self.num_devices} devices")
                    
                    # Create paraglider and start transmitting immediately
                    site = FLYING_SITES[device_num % len(FLYING_SITES)]
                    para = self.create_paraglider(info, site)
                    with self.lock:
                        self.paragliders.append(para)
                    
                    # Start simulation immediately
                    self.simulation_executor.submit(self.simulate_paraglider, para)
                    return True
                else:
                    # Failed, wait before retry
                    if attempt < max_retries - 1:
                        time.sleep(random.uniform(1.0, 2.0))
            
            # Failed after all retries
            with self.lock:
                print(f"  Failed to register device {device_num} after {max_retries} attempts")
            return False
        
        # Register and start devices with controlled concurrency
        with ThreadPoolExecutor(max_workers=10) as reg_executor:
            futures = []
            failed_count = 0
            
            # Submit registrations in smaller batches
            batch_size = 20
            for i in range(0, self.num_devices, batch_size):
                batch_futures = []
                for j in range(i, min(i + batch_size, self.num_devices)):
                    future = reg_executor.submit(register_and_start, j)
                    batch_futures.append(future)
                    futures.append(future)
                
                # Delay between batches to avoid overwhelming the API
                time.sleep(1.0)
            
            # Wait for all registrations to complete and count failures
            for future in futures:
                if not future.result():
                    failed_count += 1
            
            if failed_count > 0:
                print(f"\n⚠️  {failed_count} devices failed to register")
        
        print(f"\n✅ Registered {len(device_infos)} devices")
        print(f"🚀 All devices are transmitting!")
        
        # Phase 2: Monitor simulation
        print("\n📡 Phase 2: Monitoring flights...")
        print("Press Ctrl+C to stop\n")
        
        end_time = datetime.now() + timedelta(minutes=self.duration_minutes)
        stats_interval = 10  # seconds
        last_stats = time.time()
        
        try:
            while datetime.now() < end_time and self.running:
                time.sleep(1)
                
                # Print statistics periodically
                if time.time() - last_stats > stats_interval:
                    self.print_statistics()
                    last_stats = time.time()
                    
        except KeyboardInterrupt:
            print("\n\n⚠️ Simulation interrupted by user")
        
        # Cleanup
        print("\n🛑 Stopping simulation...")
        self.running = False
        
        # Shutdown executor
        if hasattr(self, 'simulation_executor'):
            self.simulation_executor.shutdown(wait=False)
        
        # Disconnect all MQTT clients
        print("Disconnecting MQTT clients...")
        # Disconnect individual clients
        for para in self.paragliders:
            if para.mqtt_client:
                try:
                    para.mqtt_client.loop_stop()
                    para.mqtt_client.disconnect()
                except:
                    pass
        
        # Disconnect pool clients
        for client in self.mqtt_pool:
            try:
                client.loop_stop()
                client.disconnect()
            except:
                pass
        
        time.sleep(3)  # Allow threads to finish
        
        # Final statistics
        self.print_statistics()
        
        # Save results
        results = {
            "simulation": {
                "devices": self.num_devices,
                "duration_minutes": self.duration_minutes,
                "total_points": self.total_points_sent,
                "registered_devices": self.registered_count
            },
            "timestamp": datetime.now().isoformat()
        }
        
        with open("paraglider_simulation_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✅ Simulation complete. Results saved to paraglider_simulation_results.json")

def main():
    parser = argparse.ArgumentParser(description="Paraglider Traffic Emulator")
    parser.add_argument("--devices", type=int, default=10, help="Number of paraglider devices to simulate")
    parser.add_argument("--duration", type=int, default=60, help="Simulation duration in minutes")
    parser.add_argument("--domain", type=str, default=DEFAULT_DOMAIN, help="Domain/hostname for API and MQTT connections (default: localhost)")
    
    args = parser.parse_args()
    
    # Download CA certificate if needed
    download_ca_certificate()
    
    # Update configuration with domain
    global API_BASE_URL, MQTT_HOST
    if args.domain != DEFAULT_DOMAIN:
        API_BASE_URL = f"https://{args.domain}/api/v1"
        MQTT_HOST = args.domain
    
    # Validate inputs
    if args.devices < 1:
        print("Error: Number of devices must be at least 1")
        sys.exit(1)
        
    if args.duration < 1 or args.duration > 1440:
        print("Error: Duration must be between 1 and 1440 minutes (24 hours)")
        sys.exit(1)
    
    # Print configuration
    print(f"🌐 Using domain: {args.domain}")
    print(f"📡 MQTT endpoint: {MQTT_HOST}:{MQTT_PORT}")
    print(f"🔗 API endpoint: {API_BASE_URL}")
    print(f"🔐 MQTT user: {MQTT_USER}")
    
    # Check CA certificate
    if not os.path.exists(CA_CERT):
        print("❌ CA certificate not found!")
        print("Run ./scripts/generate_certs.sh to generate certificates")
        sys.exit(1)
    
    # Run simulation
    simulator = ParagliderSimulator(args.devices, args.duration)
    simulator.run()

if __name__ == "__main__":
    main()
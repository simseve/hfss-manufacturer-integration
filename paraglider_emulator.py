#!/usr/bin/env python3
"""
Paraglider Traffic Emulator - Simulates realistic paraglider GPS tracking patterns
including takeoffs, flights, thermals, landings, and device lifecycle.

SAFETY FEATURES:
- Single instance lock to prevent multiple emulators
- Device count limits
- Rate limiting for API calls
- Resource monitoring
- Automatic cleanup on exit
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
import fcntl
import atexit
import signal
import tempfile

# Load environment variables
load_dotenv()

# Configuration
DEFAULT_DOMAIN = "localhost"
API_BASE_URL = f"http://{DEFAULT_DOMAIN}"
MQTT_HOST = DEFAULT_DOMAIN
MQTT_PORT = 8883  # TLS port
MQTT_USER = os.getenv("MQTT_USER", "mqtt_user")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "mqtt_secure_password")
MANUFACTURER = os.getenv("MANUFACTURER", "DIGIFLY")
MANUFACTURER_SECRET = os.getenv(f"MANUFACTURER_SECRET_{MANUFACTURER}", os.getenv("MANUFACTURER_SECRET_DIGIFLY", "GziZ46Tr4ANkhKh75lFnPtOrTkLgfHWe"))

# TLS Certificate paths
CA_CERT = os.getenv("CA_CERT", "./certs/ca.crt")
CLIENT_CERT = os.getenv("CLIENT_CERT", "./certs/client.crt")
CLIENT_KEY = os.getenv("CLIENT_KEY", "./certs/client.key")

# Safety limits
MAX_DEVICES_PER_INSTANCE = int(os.getenv("MAX_DEVICES", "500"))
MAX_DURATION_MINUTES = 1440  # 24 hours
DEFAULT_UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "5"))  # seconds
API_RATE_LIMIT = int(os.getenv("API_RATE_LIMIT", "10"))  # requests per second

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

class RateLimiter:
    """Rate limiter for API calls to prevent overwhelming the server"""
    def __init__(self, max_requests_per_second: int = 10):
        self.max_requests = max_requests_per_second
        self.requests = []
        self.lock = threading.Lock()
        
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        with self.lock:
            now = time.time()
            # Remove requests older than 1 second
            self.requests = [t for t in self.requests if now - t < 1.0]
            
            if len(self.requests) >= self.max_requests:
                # Calculate wait time
                sleep_time = 1.0 - (now - self.requests[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            self.requests.append(time.time())

class ParagliderSimulator:
    def __init__(self, num_devices: int, duration_minutes: int = 60, safe_mode: bool = True):
        # Safety checks
        if num_devices > MAX_DEVICES_PER_INSTANCE:
            raise ValueError(f"Maximum {MAX_DEVICES_PER_INSTANCE} devices allowed per instance. Use --force to override.")
        if duration_minutes > MAX_DURATION_MINUTES:
            raise ValueError(f"Maximum duration is {MAX_DURATION_MINUTES} minutes (24 hours)")
            
        self.num_devices = num_devices
        self.duration_minutes = duration_minutes
        self.safe_mode = safe_mode
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
        
        # Safety features
        self.lock_file_path = os.path.join(tempfile.gettempdir(), "paraglider_emulator.lock")
        self.lock_file = None
        self.rate_limiter = RateLimiter(API_RATE_LIMIT)
        self.update_interval = DEFAULT_UPDATE_INTERVAL if safe_mode else 1
        
        # Acquire instance lock
        self._acquire_lock()
        
        # Register cleanup handlers
        atexit.register(self._cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _acquire_lock(self):
        """Acquire exclusive lock to prevent multiple instances"""
        try:
            self.lock_file = open(self.lock_file_path, 'w')
            fcntl.lockf(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_file.write(f"{os.getpid()}\n")
            self.lock_file.write(f"Started: {datetime.now().isoformat()}\n")
            self.lock_file.write(f"Devices: {self.num_devices}\n")
            self.lock_file.flush()
        except IOError:
            print("❌ ERROR: Another emulator instance is already running!")
            print(f"   Lock file: {self.lock_file_path}")
            
            # Try to read the lock file to show info
            try:
                with open(self.lock_file_path, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        print(f"   PID: {lines[0].strip()}")
                        if len(lines) > 1:
                            print(f"   {lines[1].strip()}")
                        if len(lines) > 2:
                            print(f"   {lines[2].strip()}")
            except:
                pass
                
            print("\nTo force start anyway, first remove the lock file:")
            print(f"  rm {self.lock_file_path}")
            sys.exit(1)
            
    def _release_lock(self):
        """Release lock file"""
        if self.lock_file:
            try:
                fcntl.lockf(self.lock_file, fcntl.LOCK_UN)
                self.lock_file.close()
                os.unlink(self.lock_file_path)
            except:
                pass
                
    def _cleanup(self):
        """Cleanup on exit"""
        self.running = False
        self._release_lock()
        print("\n🧹 Cleanup completed")
        
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        print(f"\n⚠️  Received signal {signum}, shutting down gracefully...")
        self.running = False
        self._cleanup()
        sys.exit(0)
        
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
        # Apply rate limiting in safe mode
        if self.safe_mode:
            self.rate_limiter.wait_if_needed()
            
        # Add timestamp to ensure unique device IDs
        timestamp = int(time.time() * 1000) % 100000
        device_id = f"EMU-PARA-{datetime.now().strftime('%Y%m%d')}-{timestamp}-{device_num:04d}"
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
                f"{API_BASE_URL}/api/v1/devices/register",
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
        context.load_cert_chain(certfile=CLIENT_CERT, keyfile=CLIENT_KEY)
        return context
    
    def create_mqtt_pool(self, pool_size=50):
        """Create a pool of MQTT connections for high device counts"""
        print(f"Creating MQTT connection pool with {pool_size} connections...")
        for i in range(pool_size):
            try:
                client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"pool-{i}-{int(time.time())}")
            except:
                client = mqtt.Client(client_id=f"pool-{i}-{int(time.time())}")
            
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
            client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
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
        # Use configured update interval
        update_interval = self.update_interval
        
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
    parser = argparse.ArgumentParser(
        description="Paraglider Traffic Emulator - Simulate GPS tracking for paraglider devices",
        epilog="Safety features: single instance lock, rate limiting, device count limits"
    )
    parser.add_argument("--devices", type=int, default=10, 
                       help=f"Number of devices to simulate (max: {MAX_DEVICES_PER_INSTANCE})")
    parser.add_argument("--duration", type=int, default=60, 
                       help=f"Simulation duration in minutes (max: {MAX_DURATION_MINUTES})")
    parser.add_argument("--domain", type=str, default=DEFAULT_DOMAIN, 
                       help="Domain/hostname for API and MQTT connections")
    parser.add_argument("--manufacturer", "-m", type=str, default=MANUFACTURER,
                       help="Manufacturer name (default: from env or DIGIFLY)")
    parser.add_argument("--unsafe", action="store_true",
                       help="Disable safety features (1-second updates, no rate limiting)")
    parser.add_argument("--force", action="store_true",
                       help="Force start even if limits are exceeded (use with caution)")
    parser.add_argument("--config", action="store_true",
                       help="Configure manufacturer secrets before running")
    
    args = parser.parse_args()
    
    # Handle configuration mode
    if args.config:
        from config_manager import ConfigManager
        manager = ConfigManager()
        manager.get_manufacturer_config(args.manufacturer)
        print("\nConfiguration complete. Run without --config to start simulation.")
        sys.exit(0)
    
    # Load manufacturer configuration
    global MANUFACTURER, MANUFACTURER_SECRET
    MANUFACTURER = args.manufacturer
    
    # Try to load saved configuration
    try:
        from config_manager import ConfigManager
        manager = ConfigManager()
        mfg_config = manager.get_manufacturer_config(MANUFACTURER)
        MANUFACTURER_SECRET = mfg_config['secret']
    except Exception as e:
        # Fallback to environment variable
        MANUFACTURER_SECRET = os.getenv(f"MANUFACTURER_SECRET_{MANUFACTURER}", 
                                      os.getenv("MANUFACTURER_SECRET_DIGIFLY", ""))
        if not MANUFACTURER_SECRET:
            print(f"❌ No manufacturer secret found for {MANUFACTURER}")
            print(f"   Set MANUFACTURER_SECRET_{MANUFACTURER} environment variable")
            print(f"   Or run with --config to set it up interactively")
            sys.exit(1)
    
    # Update configuration with domain
    global API_BASE_URL, MQTT_HOST
    API_BASE_URL = f"http://{args.domain}"
    MQTT_HOST = args.domain
    
    # Validate inputs
    if args.devices < 1:
        print("❌ Error: Number of devices must be at least 1")
        sys.exit(1)
    
    if not args.force and args.devices > MAX_DEVICES_PER_INSTANCE:
        print(f"❌ Error: Maximum {MAX_DEVICES_PER_INSTANCE} devices allowed per instance")
        print("   Use --force to override (not recommended)")
        sys.exit(1)
        
    if args.duration < 1 or args.duration > MAX_DURATION_MINUTES:
        print(f"❌ Error: Duration must be between 1 and {MAX_DURATION_MINUTES} minutes")
        sys.exit(1)
    
    # Safety mode
    safe_mode = not args.unsafe
    if args.unsafe:
        print("⚠️  WARNING: Running in UNSAFE mode!")
        print("   - 1-second GPS updates (high load)")
        print("   - No API rate limiting")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)
    
    # Print configuration
    print(f"\n🪂 Paraglider Traffic Emulator")
    print(f"{'='*50}")
    print(f"🏭 Manufacturer: {MANUFACTURER}")
    print(f"🌐 Domain: {args.domain}")
    print(f"📡 MQTT: {MQTT_HOST}:{MQTT_PORT}")
    print(f"🔗 API: {API_BASE_URL}")
    print(f"🔐 MQTT User: {MQTT_USER}")
    print(f"🛡️  Safe Mode: {'ON' if safe_mode else 'OFF'}")
    print(f"⏱️  Update Interval: {DEFAULT_UPDATE_INTERVAL if safe_mode else 1} seconds")
    print(f"🚦 API Rate Limit: {API_RATE_LIMIT if safe_mode else 'Disabled'} req/s")
    
    # Check certificates
    cert_paths = [CA_CERT, CLIENT_CERT, CLIENT_KEY]
    if not all(os.path.exists(cert) for cert in cert_paths):
        print("\n❌ TLS certificates not found!")
        print("Please run: python generate_certs.py")
        missing = [cert for cert in cert_paths if not os.path.exists(cert)]
        print(f"Missing: {', '.join(missing)}")
        sys.exit(1)
    
    # Create and run simulator
    try:
        simulator = ParagliderSimulator(args.devices, args.duration, safe_mode)
        simulator.run()
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Simulation interrupted by user")
        sys.exit(0)

if __name__ == "__main__":
    main()
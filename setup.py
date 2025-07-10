#!/usr/bin/env python3
"""
Setup script for Digi Fly Paraglider Emulator
Installs dependencies and prepares the environment
"""
import os
import sys
import subprocess
import shutil

def check_python_version():
    """Ensure Python 3.7+ is being used"""
    if sys.version_info < (3, 7):
        print("❌ Error: Python 3.7 or higher is required.")
        print(f"   You are using Python {sys.version}")
        sys.exit(1)

def install_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing Python dependencies...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies.")
        print("   Try running: pip install -r requirements.txt")
        return False

def setup_certificates():
    """Check and generate certificates if needed"""
    if not os.path.exists("certs/ca.crt"):
        print("\n🔐 No certificates found. Generating test certificates...")
        try:
            subprocess.run([sys.executable, "generate_certs.py"], check=True)
            return True
        except subprocess.CalledProcessError:
            print("⚠️  Failed to generate certificates automatically.")
            print("   You can generate them manually with: python generate_certs.py")
            return False
    else:
        print("\n✅ Certificates already exist in ./certs/")
        return True

def setup_environment():
    """Create .env file from template"""
    if not os.path.exists(".env"):
        print("\n📝 Creating .env configuration file...")
        if os.path.exists(".env.example"):
            shutil.copy(".env.example", ".env")
            print("✅ Created .env file from template.")
            print("\n⚠️  IMPORTANT: Edit .env file with your settings:")
            print("   - API_DOMAIN: Your server domain")
            print("   - MQTT credentials")
            print("   - MANUFACTURER_SECRET_DIGIFLY: Your manufacturer secret")
            return True
        else:
            print("❌ .env.example not found!")
            return False
    else:
        print("\n✅ .env file already exists")
        return True

def print_usage():
    """Print usage instructions"""
    print("\n" + "="*60)
    print("🪂 Digi Fly Paraglider Emulator Setup Complete!")
    print("="*60)
    print("\nTo run the emulator:")
    print("\n1. Basic usage (10 devices, 60 minutes):")
    print("   python paraglider_emulator.py")
    print("\n2. Custom number of devices:")
    print("   python paraglider_emulator.py --devices 50")
    print("\n3. Custom duration (minutes):")
    print("   python paraglider_emulator.py --duration 120")
    print("\n4. Custom server domain:")
    print("   python paraglider_emulator.py --domain your-server.com")
    print("\n5. All options:")
    print("   python paraglider_emulator.py --devices 100 --duration 30 --domain your-server.com")
    print("\nFor help:")
    print("   python paraglider_emulator.py --help")

def main():
    print("🚀 Setting up Digi Fly Paraglider Emulator")
    print("="*60)
    
    # Check Python version
    check_python_version()
    
    # Track success
    all_success = True
    
    # Install dependencies
    if not install_dependencies():
        all_success = False
    
    # Setup certificates
    if not setup_certificates():
        all_success = False
    
    # Setup environment
    if not setup_environment():
        all_success = False
    
    # Print final status
    if all_success:
        print_usage()
    else:
        print("\n⚠️  Setup completed with some warnings.")
        print("   Please address any issues before running the emulator.")
        sys.exit(1)

if __name__ == "__main__":
    main()
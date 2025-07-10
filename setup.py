#!/usr/bin/env python3
"""
Setup script for Digi Fly Paraglider Emulator
Installs dependencies and prepares the environment
"""
import os
import sys
import subprocess
import shutil
import venv

def check_python_version():
    """Ensure Python 3.7+ is being used"""
    if sys.version_info < (3, 7):
        print("❌ Error: Python 3.7 or higher is required.")
        print(f"   You are using Python {sys.version}")
        sys.exit(1)

def setup_virtual_environment():
    """Create virtual environment using Python 3.12 if available"""
    venv_path = os.path.join(os.getcwd(), "venv")
    
    if os.path.exists(venv_path):
        print("✅ Virtual environment already exists at ./venv")
        return venv_path
    
    print("\n🐍 Creating virtual environment...")
    
    # Try to use Python 3.12 specifically if available
    python_cmd = None
    for cmd in ["python3.12", "python3", "python"]:
        try:
            result = subprocess.run([cmd, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version_str = result.stdout.strip()
                if "3.12" in version_str or (cmd in ["python3", "python"] and sys.version_info >= (3, 7)):
                    python_cmd = cmd
                    print(f"   Using {cmd} ({version_str})")
                    break
        except FileNotFoundError:
            continue
    
    if not python_cmd:
        print("❌ Error: Could not find suitable Python installation (3.7+)")
        sys.exit(1)
    
    try:
        # Create virtual environment
        subprocess.run([python_cmd, "-m", "venv", "venv"], check=True)
        print("✅ Virtual environment created successfully!")
        
        # Determine pip path based on OS
        if sys.platform == "win32":
            pip_path = os.path.join(venv_path, "Scripts", "pip")
            activate_cmd = os.path.join(venv_path, "Scripts", "activate.bat")
        else:
            pip_path = os.path.join(venv_path, "bin", "pip")
            activate_cmd = f"source {os.path.join(venv_path, 'bin', 'activate')}"
        
        print(f"\n📌 To activate the virtual environment manually, run:")
        print(f"   {activate_cmd}")
        
        return venv_path
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create virtual environment: {e}")
        sys.exit(1)

def install_dependencies(venv_path):
    """Install Python dependencies in the virtual environment"""
    print("\n📦 Installing Python dependencies in virtual environment...")
    
    # Determine pip path based on OS
    if sys.platform == "win32":
        pip_path = os.path.join(venv_path, "Scripts", "pip")
    else:
        pip_path = os.path.join(venv_path, "bin", "pip")
    
    try:
        # Upgrade pip first
        subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)
        
        # Install dependencies
        subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencies installed successfully in virtual environment!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies.")
        print(f"   Try running: {pip_path} install -r requirements.txt")
        return False

def setup_certificates(venv_path):
    """Check and generate certificates if needed"""
    if not os.path.exists("certs/ca.crt"):
        print("\n🔐 No certificates found. Generating test certificates...")
        
        # Use virtual environment's Python
        if sys.platform == "win32":
            python_path = os.path.join(venv_path, "Scripts", "python")
        else:
            python_path = os.path.join(venv_path, "bin", "python")
            
        try:
            subprocess.run([python_path, "generate_certs.py"], check=True)
            return True
        except subprocess.CalledProcessError:
            print("⚠️  Failed to generate certificates automatically.")
            print(f"   You can generate them manually with: {python_path} generate_certs.py")
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

def create_run_script(venv_path):
    """Create a run script that ensures virtual environment is activated"""
    script_name = "run_emulator.sh" if sys.platform != "win32" else "run_emulator.bat"
    
    if sys.platform == "win32":
        # Windows batch script
        script_content = f"""@echo off
call "{os.path.join(venv_path, 'Scripts', 'activate.bat')}"
python paraglider_emulator.py %*
"""
    else:
        # Unix shell script
        script_content = f"""#!/bin/bash
source "{os.path.join(venv_path, 'bin', 'activate')}"
python paraglider_emulator.py "$@"
"""
    
    try:
        with open(script_name, 'w') as f:
            f.write(script_content)
        
        # Make executable on Unix
        if sys.platform != "win32":
            os.chmod(script_name, 0o755)
        
        print(f"✅ Created {script_name} to run emulator with virtual environment")
        return script_name
    except Exception as e:
        print(f"⚠️  Failed to create run script: {e}")
        return None

def print_usage(venv_path):
    """Print usage instructions"""
    script_name = "run_emulator.sh" if sys.platform != "win32" else "run_emulator.bat"
    
    print("\n" + "="*60)
    print("🪂 Digi Fly Paraglider Emulator Setup Complete!")
    print("="*60)
    print("\n⚠️  IMPORTANT: Always use the virtual environment!")
    print("\nTo run the emulator:")
    print("\n1. Basic usage (10 devices, 60 minutes):")
    print(f"   ./{script_name}")
    print("\n2. Custom number of devices:")
    print(f"   ./{script_name} --devices 50")
    print("\n3. Custom duration (minutes):")
    print(f"   ./{script_name} --duration 120")
    print("\n4. Custom server domain:")
    print(f"   ./{script_name} --domain your-server.com")
    print("\n5. All options:")
    print(f"   ./{script_name} --devices 100 --duration 30 --domain your-server.com")
    print("\nFor help:")
    print(f"   ./{script_name} --help")
    print("\n📌 Alternative: Manually activate virtual environment first:")
    if sys.platform == "win32":
        print(f"   {os.path.join(venv_path, 'Scripts', 'activate.bat')}")
    else:
        print(f"   source {os.path.join(venv_path, 'bin', 'activate')}")
    print("   python paraglider_emulator.py [options]")

def main():
    print("🚀 Setting up Digi Fly Paraglider Emulator")
    print("="*60)
    
    # Check Python version
    check_python_version()
    
    # Setup virtual environment first
    venv_path = setup_virtual_environment()
    
    # Track success
    all_success = True
    
    # Install dependencies in virtual environment
    if not install_dependencies(venv_path):
        all_success = False
    
    # Setup certificates using virtual environment
    if not setup_certificates(venv_path):
        all_success = False
    
    # Setup environment
    if not setup_environment():
        all_success = False
    
    # Create run script
    if not create_run_script(venv_path):
        all_success = False
    
    # Update run_safe.sh to use virtual environment
    update_run_safe_script(venv_path)
    
    # Print final status
    if all_success:
        print_usage(venv_path)
    else:
        print("\n⚠️  Setup completed with some warnings.")
        print("   Please address any issues before running the emulator.")
        sys.exit(1)

def update_run_safe_script(venv_path):
    """Update run_safe.sh to use virtual environment"""
    if os.path.exists("run_safe.sh"):
        try:
            with open("run_safe.sh", 'r') as f:
                content = f.read()
            
            # Add virtual environment activation after the shebang
            if "source" not in content or "venv/bin/activate" not in content:
                lines = content.split('\n')
                # Insert activation after the first line (shebang)
                activation_line = f'\n# Activate virtual environment\nsource "{os.path.join(venv_path, "bin", "activate")}"\n'
                lines.insert(1, activation_line)
                
                with open("run_safe.sh", 'w') as f:
                    f.write('\n'.join(lines))
                
                print("✅ Updated run_safe.sh to use virtual environment")
        except Exception as e:
            print(f"⚠️  Could not update run_safe.sh: {e}")

if __name__ == "__main__":
    main()
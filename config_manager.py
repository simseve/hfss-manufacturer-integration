#!/usr/bin/env python3
"""
Configuration manager for the Paraglider Emulator
Handles manufacturer secrets and other sensitive configuration
"""
import os
import json
import getpass
from pathlib import Path
import stat

class ConfigManager:
    """Manage emulator configuration including manufacturer secrets"""
    
    def __init__(self):
        # Use XDG_CONFIG_HOME or fallback to ~/.config
        config_home = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        self.config_dir = Path(config_home) / 'paraglider_emulator'
        self.config_file = self.config_dir / 'config.json'
        self.secrets_file = self.config_dir / 'secrets.json'
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure secrets file has restricted permissions
        if self.secrets_file.exists():
            os.chmod(self.secrets_file, stat.S_IRUSR | stat.S_IWUSR)  # 600
    
    def load_config(self):
        """Load configuration from files"""
        config = {
            'manufacturers': {},
            'defaults': {
                'domain': 'localhost',
                'mqtt_user': 'mqtt_user',
                'max_devices': 500,
                'update_interval': 5,
                'api_rate_limit': 10
            }
        }
        
        # Load general config
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                saved_config = json.load(f)
                config['defaults'].update(saved_config.get('defaults', {}))
        
        # Load secrets
        if self.secrets_file.exists():
            with open(self.secrets_file, 'r') as f:
                secrets = json.load(f)
                config['manufacturers'] = secrets.get('manufacturers', {})
        
        return config
    
    def save_config(self, config):
        """Save configuration to files"""
        # Separate secrets from general config
        general_config = {
            'defaults': config.get('defaults', {})
        }
        
        secrets_config = {
            'manufacturers': config.get('manufacturers', {})
        }
        
        # Save general config
        with open(self.config_file, 'w') as f:
            json.dump(general_config, f, indent=2)
        
        # Save secrets with restricted permissions
        with open(self.secrets_file, 'w') as f:
            json.dump(secrets_config, f, indent=2)
        os.chmod(self.secrets_file, stat.S_IRUSR | stat.S_IWUSR)  # 600
    
    def get_manufacturer_config(self, manufacturer_name):
        """Get or prompt for manufacturer configuration"""
        config = self.load_config()
        
        # Check if manufacturer config exists
        if manufacturer_name in config['manufacturers']:
            mfg_config = config['manufacturers'][manufacturer_name]
            print(f"✅ Using saved configuration for manufacturer: {manufacturer_name}")
            return mfg_config
        
        # Prompt for new manufacturer configuration
        print(f"\n🔧 Setting up new manufacturer: {manufacturer_name}")
        print("Please provide the following information:")
        
        mfg_config = {}
        
        # Get manufacturer secret
        while True:
            secret = getpass.getpass(f"Manufacturer secret for {manufacturer_name}: ")
            if len(secret) < 16:
                print("⚠️  Secret should be at least 16 characters for security")
                continue
            confirm = getpass.getpass("Confirm secret: ")
            if secret != confirm:
                print("❌ Secrets don't match, please try again")
                continue
            mfg_config['secret'] = secret
            break
        
        # Get API key (if needed)
        api_key = input(f"API key for {manufacturer_name} (press Enter if not needed): ").strip()
        if api_key:
            mfg_config['api_key'] = api_key
        
        # Ask if user wants to save
        save = input("\nSave this configuration for future use? (y/N): ").lower()
        if save == 'y':
            config['manufacturers'][manufacturer_name] = mfg_config
            self.save_config(config)
            print(f"✅ Configuration saved to {self.secrets_file}")
            print("   Note: Secrets are stored with restricted permissions (600)")
        
        return mfg_config
    
    def list_manufacturers(self):
        """List configured manufacturers"""
        config = self.load_config()
        manufacturers = list(config['manufacturers'].keys())
        
        if manufacturers:
            print("\n📋 Configured manufacturers:")
            for mfg in manufacturers:
                print(f"   - {mfg}")
        else:
            print("\n📋 No manufacturers configured yet")
        
        return manufacturers
    
    def remove_manufacturer(self, manufacturer_name):
        """Remove a manufacturer configuration"""
        config = self.load_config()
        
        if manufacturer_name in config['manufacturers']:
            del config['manufacturers'][manufacturer_name]
            self.save_config(config)
            print(f"✅ Removed configuration for {manufacturer_name}")
        else:
            print(f"❌ No configuration found for {manufacturer_name}")
    
    def get_defaults(self):
        """Get default configuration values"""
        config = self.load_config()
        return config.get('defaults', {})
    
    def update_defaults(self, updates):
        """Update default configuration values"""
        config = self.load_config()
        config['defaults'].update(updates)
        self.save_config(config)

def main():
    """CLI for managing configurations"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage Paraglider Emulator configurations")
    parser.add_argument('command', choices=['list', 'add', 'remove', 'show-defaults'],
                       help='Command to execute')
    parser.add_argument('--manufacturer', '-m', help='Manufacturer name')
    
    args = parser.parse_args()
    
    manager = ConfigManager()
    
    if args.command == 'list':
        manager.list_manufacturers()
    
    elif args.command == 'add':
        if not args.manufacturer:
            print("❌ Please specify manufacturer with -m/--manufacturer")
            return
        manager.get_manufacturer_config(args.manufacturer)
    
    elif args.command == 'remove':
        if not args.manufacturer:
            print("❌ Please specify manufacturer with -m/--manufacturer")
            return
        manager.remove_manufacturer(args.manufacturer)
    
    elif args.command == 'show-defaults':
        defaults = manager.get_defaults()
        print("\n📋 Default configuration:")
        for key, value in defaults.items():
            print(f"   {key}: {value}")

if __name__ == "__main__":
    main()
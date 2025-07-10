#!/usr/bin/env python3
"""
Generate self-signed certificates for MQTT TLS connection testing.
For production, use proper certificates from your Certificate Authority.
"""
import os
import subprocess
import sys

def generate_test_certificates():
    """Generate self-signed certificates for testing"""
    print("🔐 Generating test certificates for MQTT TLS...")
    
    # Create certs directory if it doesn't exist
    os.makedirs("certs", exist_ok=True)
    
    try:
        # Generate CA key and certificate
        print("  Creating Certificate Authority...")
        subprocess.run([
            "openssl", "req", "-new", "-x509", "-days", "365",
            "-keyout", "certs/ca.key", "-out", "certs/ca.crt", "-nodes",
            "-subj", "/C=US/ST=Test/L=Test/O=DigiFly/CN=DigiFlyTestCA"
        ], check=True, capture_output=True)
        
        # Generate client key and certificate request
        print("  Creating client certificate request...")
        subprocess.run([
            "openssl", "req", "-new", "-keyout", "certs/client.key",
            "-out", "certs/client.csr", "-nodes",
            "-subj", "/C=US/ST=Test/L=Test/O=DigiFly/CN=DigiFlyClient"
        ], check=True, capture_output=True)
        
        # Sign client certificate with CA
        print("  Signing client certificate...")
        subprocess.run([
            "openssl", "x509", "-req", "-in", "certs/client.csr",
            "-CA", "certs/ca.crt", "-CAkey", "certs/ca.key",
            "-CAcreateserial", "-out", "certs/client.crt", "-days", "365"
        ], check=True, capture_output=True)
        
        # Cleanup temporary files
        if os.path.exists("certs/client.csr"):
            os.remove("certs/client.csr")
        if os.path.exists("certs/ca.srl"):
            os.remove("certs/ca.srl")
        
        # Set appropriate permissions
        os.chmod("certs/ca.key", 0o600)
        os.chmod("certs/client.key", 0o600)
        
        print("✅ Test certificates generated successfully!")
        print("\nCertificates created in ./certs/:")
        print("  - ca.crt       : Certificate Authority")
        print("  - client.crt   : Client certificate")
        print("  - client.key   : Client private key")
        print("\n⚠️  These are self-signed certificates for TESTING ONLY.")
        print("   For production, use certificates from a trusted CA.")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating certificates: {e}")
        print("\nMake sure OpenSSL is installed:")
        print("  - macOS: brew install openssl")
        print("  - Ubuntu/Debian: apt-get install openssl")
        print("  - CentOS/RHEL: yum install openssl")
        return False
    except FileNotFoundError:
        print("❌ OpenSSL not found. Please install OpenSSL first.")
        return False

def check_existing_certificates():
    """Check if certificates already exist"""
    cert_files = ["certs/ca.crt", "certs/client.crt", "certs/client.key"]
    return all(os.path.exists(f) for f in cert_files)

def main():
    if check_existing_certificates():
        print("ℹ️  Certificates already exist in ./certs/")
        response = input("Do you want to regenerate them? (y/N): ")
        if response.lower() != 'y':
            print("Using existing certificates.")
            return
    
    if generate_test_certificates():
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
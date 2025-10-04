#!/usr/bin/env python3
"""
Create SSL certificates for Outlook add-in development using Python cryptography library.
This script generates self-signed certificates without requiring OpenSSL.
"""

import os
import sys
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import ipaddress

def create_self_signed_cert(cert_file, key_file, hostname="localhost"):
    """Create a self-signed SSL certificate."""
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Create certificate subject
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "NY"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Arcade"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Koike Aronson Inc."),
        x509.NameAttribute(NameOID.COMMON_NAME, hostname),
    ])
    
    # Create certificate
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.now()
    ).not_valid_after(
        datetime.now() + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(hostname),
            x509.DNSName("127.0.0.1"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    ).add_extension(
        x509.ExtendedKeyUsage([
            ExtendedKeyUsageOID.SERVER_AUTH,
        ]),
        critical=True,
    ).sign(private_key, hashes.SHA256(), default_backend())
    
    # Write certificate to file
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    # Write private key to file
    with open(key_file, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    print(f"✅ Created certificate: {cert_file}")
    print(f"✅ Created private key: {key_file}")
    return True

def install_cryptography():
    """Install cryptography library if not available."""
    try:
        import cryptography
        print("✅ cryptography library already installed")
        return True
    except ImportError:
        print("📦 Installing cryptography library...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"])
            print("✅ cryptography library installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install cryptography: {e}")
            return False

def main():
    """Main function to create SSL certificates."""
    print("🔐 Creating SSL certificates for Outlook add-in development...")
    
    # Install cryptography if needed
    if not install_cryptography():
        print("❌ Cannot proceed without cryptography library")
        return False
    
    # Create certificates for add-in server
    print("\n📋 Creating certificates for add-in server (port 3000)...")
    if not create_self_signed_cert("cert.pem", "key.pem", "localhost"):
        return False
    
    # Create certificates for Flask backend
    print("\n📋 Creating certificates for Flask backend (port 5000)...")
    if not create_self_signed_cert("flask_cert.pem", "flask_key.pem", "localhost"):
        return False
    
    print("\n🎉 SSL certificates created successfully!")
    print("\n📝 Next steps:")
    print("1. Accept the self-signed certificates in your browser")
    print("2. Start your Flask backend: python app.py")
    print("3. Start the add-in server: python outlook_addin_server.py")
    print("4. Install the add-in in Outlook using manifest.xml")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error creating certificates: {e}")
        print("\n💡 Alternative: You can also use online tools to generate certificates")
        print("   or install OpenSSL for Windows from: https://slproweb.com/products/Win32OpenSSL.html")
        sys.exit(1)

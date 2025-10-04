#!/usr/bin/env python3
"""
Setup script for the Outlook PO Processor Add-in
This script helps set up the development environment for the Outlook add-in.
"""

import os
import subprocess
import sys
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or later is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def install_dependencies():
    """Install required Python packages."""
    print("📦 Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", 
                             "flask", "flask-cors", "requests"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_ssl_certificates():
    """Create SSL certificates for development."""
    print("🔐 Creating SSL certificates for development...")
    
    # Check if certificates already exist
    if os.path.exists("cert.pem") and os.path.exists("key.pem"):
        print("✅ SSL certificates already exist")
        return True
    
    try:
        # Generate self-signed certificate
        subprocess.check_call([
            "openssl", "req", "-x509", "-newkey", "rsa:4096",
            "-keyout", "key.pem", "-out", "cert.pem",
            "-days", "365", "-nodes", "-subj", 
            "/C=US/ST=NY/L=Arcade/O=Koike Aronson/CN=localhost"
        ])
        print("✅ SSL certificates created successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to create SSL certificates")
        print("💡 Make sure OpenSSL is installed on your system")
        return False
    except FileNotFoundError:
        print("❌ OpenSSL not found")
        print("💡 Please install OpenSSL or create certificates manually")
        return False

def create_directories():
    """Create necessary directories."""
    print("📁 Creating directories...")
    directories = ["assets", "logs"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")

def create_placeholder_icons():
    """Create placeholder icon files."""
    print("🎨 Creating placeholder icons...")
    
    # Simple SVG icons as placeholders
    icons = {
        "assets/icon-16.png": """<svg width="16" height="16" xmlns="http://www.w3.org/2000/svg">
            <rect width="16" height="16" fill="#007bff"/>
            <text x="8" y="12" text-anchor="middle" fill="white" font-size="10" font-family="Arial">PO</text>
        </svg>""",
        "assets/icon-32.png": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
            <rect width="32" height="32" fill="#007bff"/>
            <text x="16" y="22" text-anchor="middle" fill="white" font-size="16" font-family="Arial">PO</text>
        </svg>""",
        "assets/icon-64.png": """<svg width="64" height="64" xmlns="http://www.w3.org/2000/svg">
            <rect width="64" height="64" fill="#007bff"/>
            <text x="32" y="42" text-anchor="middle" fill="white" font-size="24" font-family="Arial">PO</text>
        </svg>""",
        "assets/icon-80.png": """<svg width="80" height="80" xmlns="http://www.w3.org/2000/svg">
            <rect width="80" height="80" fill="#007bff"/>
            <text x="40" y="52" text-anchor="middle" fill="white" font-size="28" font-family="Arial">PO</text>
        </svg>"""
    }
    
    for filename, svg_content in icons.items():
        try:
            # Convert SVG to PNG (simplified - in production you'd use a proper converter)
            with open(filename.replace('.png', '.svg'), 'w') as f:
                f.write(svg_content)
            print(f"✅ Created placeholder icon: {filename.replace('.png', '.svg')}")
        except Exception as e:
            print(f"⚠️  Could not create icon {filename}: {e}")

def update_manifest_id():
    """Generate a unique ID for the manifest."""
    import uuid
    
    new_id = str(uuid.uuid4())
    manifest_path = "manifest.xml"
    
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r') as f:
            content = f.read()
        
        # Replace the default ID with a new one
        content = content.replace(
            '<Id>12345678-1234-1234-1234-123456789012</Id>',
            f'<Id>{new_id}</Id>'
        )
        
        with open(manifest_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated manifest with unique ID: {new_id}")
    else:
        print("⚠️  Manifest file not found")

def print_next_steps():
    """Print instructions for next steps."""
    print("\n" + "="*60)
    print("🎉 Outlook Add-in Setup Complete!")
    print("="*60)
    print("\n📋 Next Steps:")
    print("1. Start your Flask backend:")
    print("   python app.py")
    print("\n2. Start the Outlook add-in server:")
    print("   python outlook_addin_server.py")
    print("\n3. Install the add-in in Outlook:")
    print("   - Copy manifest.xml to your Outlook add-ins")
    print("   - Or sideload it through File > Get Add-ins")
    print("\n4. Test with a PO email!")
    print("\n📖 For detailed instructions, see OUTLOOK_ADDIN_README.md")
    print("\n🔧 Troubleshooting:")
    print("   - Make sure both servers are running (ports 3000 and 5000)")
    print("   - Check that SSL certificates are valid")
    print("   - Verify your Flask backend is accessible")

def main():
    """Main setup function."""
    print("🚀 Setting up Outlook PO Processor Add-in...")
    print("="*50)
    
    success = True
    
    # Check Python version
    if not check_python_version():
        success = False
    
    # Install dependencies
    if not install_dependencies():
        success = False
    
    # Create directories
    create_directories()
    
    # Create SSL certificates
    if not create_ssl_certificates():
        print("⚠️  SSL certificates not created - you'll need to create them manually")
    
    # Create placeholder icons
    create_placeholder_icons()
    
    # Update manifest with unique ID
    update_manifest_id()
    
    if success:
        print_next_steps()
    else:
        print("\n❌ Setup completed with some issues. Please resolve them before proceeding.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Startup script for the Outlook PO Processor Add-in.
This script starts both the Flask backend and the Outlook add-in server.
"""

import subprocess
import sys
import time
import threading
import os
from pathlib import Path

def start_flask_backend():
    """Start the Flask backend server."""
    print("🚀 Starting Flask backend server...")
    try:
        subprocess.run([sys.executable, "app.py"], cwd=os.getcwd())
    except KeyboardInterrupt:
        print("\n🛑 Flask backend stopped by user")

def start_addin_server():
    """Start the Outlook add-in server."""
    print("🚀 Starting Outlook add-in server...")
    try:
        subprocess.run([sys.executable, "outlook_addin_server.py"], cwd=os.getcwd())
    except KeyboardInterrupt:
        print("\n🛑 Add-in server stopped by user")

def check_certificates():
    """Check if SSL certificates exist."""
    cert_files = ['cert.pem', 'key.pem', 'flask_cert.pem', 'flask_key.pem']
    missing = []
    
    for cert_file in cert_files:
        if not os.path.exists(cert_file):
            missing.append(cert_file)
    
    if missing:
        print("❌ Missing SSL certificates:")
        for cert in missing:
            print(f"   - {cert}")
        print("\n💡 Run: python create_ssl_cert.py")
        return False
    
    print("✅ All SSL certificates found")
    return True

def main():
    """Main startup function."""
    print("🎯 Starting Outlook PO Processor Add-in...")
    print("="*50)
    
    # Check if certificates exist
    if not check_certificates():
        return
    
    print("\n📋 Starting servers...")
    print("   - Flask backend: https://localhost:5000")
    print("   - Add-in server: https://localhost:3000")
    print("\n💡 Press Ctrl+C to stop both servers")
    print("="*50)
    
    try:
        # Start Flask backend in a separate thread
        flask_thread = threading.Thread(target=start_flask_backend, daemon=True)
        flask_thread.start()
        
        # Wait a moment for Flask to start
        time.sleep(3)
        
        # Start add-in server in main thread
        start_addin_server()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down servers...")
        print("✅ Servers stopped")

if __name__ == "__main__":
    main()

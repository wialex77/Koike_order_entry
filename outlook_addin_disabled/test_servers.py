#!/usr/bin/env python3
"""
Test script to verify both servers are running properly.
"""

import requests
import urllib3
import time

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_flask_backend():
    """Test Flask backend server."""
    # Try HTTPS first
    try:
        response = requests.get('https://localhost:5000/api/health', verify=False, timeout=5)
        if response.status_code == 200:
            print("✅ Flask backend (port 5000) is running with HTTPS")
            return True
    except requests.exceptions.RequestException:
        pass
    
    # Try HTTP as fallback
    try:
        response = requests.get('http://localhost:5000/api/health', timeout=5)
        if response.status_code == 200:
            print("✅ Flask backend (port 5000) is running with HTTP")
            return True
        else:
            print(f"❌ Flask backend returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Flask backend not accessible: {e}")
        return False

def test_addin_server():
    """Test Outlook add-in server."""
    try:
        response = requests.get('https://localhost:3000/health', verify=False, timeout=5)
        if response.status_code == 200:
            print("✅ Outlook add-in server (port 3000) is running")
            return True
        else:
            print(f"❌ Add-in server returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Add-in server not accessible: {e}")
        return False

def main():
    """Test both servers."""
    print("🧪 Testing Outlook Add-in Servers...")
    print("="*50)
    
    # Wait a moment for servers to start
    print("⏳ Waiting for servers to start...")
    time.sleep(3)
    
    flask_ok = test_flask_backend()
    addin_ok = test_addin_server()
    
    print("\n" + "="*50)
    if flask_ok and addin_ok:
        print("🎉 Both servers are running successfully!")
        print("\n📋 Next steps:")
        print("1. Open Outlook")
        print("2. Go to File > Get Add-ins")
        print("3. Click 'Add a custom add-in' > 'Add from file'")
        print("4. Select your manifest.xml file")
        print("5. Test with a PO email!")
    else:
        print("⚠️  Some servers are not running properly.")
        print("\n🔧 Troubleshooting:")
        if not flask_ok:
            print("- Start Flask backend: python app.py")
        if not addin_ok:
            print("- Start add-in server: python outlook_addin_server.py")
        print("- Check that no other applications are using ports 3000 or 5000")

if __name__ == "__main__":
    main()

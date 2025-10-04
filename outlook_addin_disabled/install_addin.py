#!/usr/bin/env python3
"""
Installation helper script for the Outlook PO Processor Add-in.
This script helps guide you through the installation process.
"""

import os
import webbrowser
import time
import subprocess
import sys

def check_servers():
    """Check if both servers are running."""
    print("🔍 Checking if servers are running...")
    
    try:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Test Flask backend
        try:
            response = requests.get('https://localhost:5000/api/health', verify=False, timeout=3)
            flask_ok = response.status_code == 200
        except:
            flask_ok = False
        
        # Test add-in server
        try:
            response = requests.get('https://localhost:3000/health', verify=False, timeout=3)
            addin_ok = response.status_code == 200
        except:
            addin_ok = False
        
        if flask_ok and addin_ok:
            print("✅ Both servers are running successfully!")
            return True
        else:
            print("❌ Some servers are not running:")
            if not flask_ok:
                print("   - Flask backend (port 5000)")
            if not addin_ok:
                print("   - Add-in server (port 3000)")
            return False
            
    except ImportError:
        print("⚠️  requests library not available, cannot check servers")
        return True

def open_browser_pages():
    """Open browser pages to accept SSL certificates."""
    print("🌐 Opening browser pages to accept SSL certificates...")
    
    urls = [
        "https://localhost:3000",
        "https://localhost:5000/api/health"
    ]
    
    for url in urls:
        print(f"   Opening: {url}")
        webbrowser.open(url)
        time.sleep(2)

def show_installation_steps():
    """Show step-by-step installation instructions."""
    print("\n" + "="*60)
    print("📋 OUTLOOK ADD-IN INSTALLATION STEPS")
    print("="*60)
    
    print("\n1️⃣  ACCEPT SSL CERTIFICATES (if not done already)")
    print("   - The browser pages should have opened automatically")
    print("   - Click 'Advanced' → 'Proceed to localhost (unsafe)' for each page")
    print("   - Or manually visit:")
    print("     • https://localhost:3000")
    print("     • https://localhost:5000/api/health")
    
    print("\n2️⃣  INSTALL IN OUTLOOK DESKTOP")
    print("   - Open Outlook")
    print("   - Go to File → Get Add-ins")
    print("   - Click 'Add a custom add-in' → 'Add from file'")
    print("   - Select: manifest_fixed.xml")
    print("   - Click 'Install'")
    
    print("\n3️⃣  INSTALL IN OUTLOOK ON THE WEB (Alternative)")
    print("   - Go to https://outlook.office.com")
    print("   - Click gear icon → Get Add-ins")
    print("   - Click 'Upload My Add-in'")
    print("   - Upload: manifest_fixed.xml")
    
    print("\n4️⃣  TEST THE ADD-IN")
    print("   - Open an email with 'Purchase Order' in the subject")
    print("   - Look for 'PO Processor' button in the message ribbon")
    print("   - Click 'Process PO' to open the task pane")
    
    print("\n" + "="*60)
    print("🔧 TROUBLESHOOTING")
    print("="*60)
    print("If installation fails:")
    print("1. Make sure both servers are running")
    print("2. Accept all SSL certificates in your browser")
    print("3. Use manifest_fixed.xml (not manifest.xml)")
    print("4. Check TROUBLESHOOTING_OUTLOOK_ADDIN.md for detailed help")
    print("5. Try restarting Outlook and clearing add-in cache")

def main():
    """Main installation helper function."""
    print("🚀 Outlook PO Processor Add-in Installation Helper")
    print("="*60)
    
    # Check if manifest file exists
    if not os.path.exists('manifest_fixed.xml'):
        print("❌ manifest_fixed.xml not found!")
        print("   Make sure you're in the correct directory")
        return
    
    # Check servers
    servers_ok = check_servers()
    
    if not servers_ok:
        print("\n🔧 To start the servers:")
        print("   Terminal 1: python app.py")
        print("   Terminal 2: python outlook_addin_server.py")
        print("\n   Or run: python start_outlook_addin.py")
        return
    
    # Open browser pages
    open_browser_pages()
    
    # Show installation steps
    show_installation_steps()
    
    print(f"\n📁 Manifest file location: {os.path.abspath('manifest_fixed.xml')}")
    print("\n🎉 Ready to install! Follow the steps above.")

if __name__ == "__main__":
    main()

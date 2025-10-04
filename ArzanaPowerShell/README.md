# Arzana Outlook Monitor - PowerShell Solution

A PowerShell script that automatically monitors Outlook for purchase order emails and processes them using your existing Flask server.

## 🚀 **Features**

- ✅ **True Background Processing** - Runs 24/7 without user interaction
- ✅ **Automatic PO Detection** - Uses advanced AI-powered detection
- ✅ **Email Tagging** - Automatically tags emails based on processing results
- ✅ **Flask Integration** - Connects to your existing Flask server
- ✅ **Comprehensive Logging** - Detailed logs for troubleshooting
- ✅ **Easy Installation** - One-click setup script

## 📋 **Prerequisites**

- **Windows 10/11** with PowerShell 5.1 or later
- **Microsoft Outlook** (desktop version)
- **Your Flask server** running on http://127.0.0.1:5000
- **Administrator privileges** for installation

## 🛠️ **Installation**

### **Quick Install:**
1. **Download all files** to a folder
2. **Right-click** `Install-ArzanaMonitor.ps1`
3. **"Run with PowerShell"** (as Administrator)
4. **Follow the prompts**

### **Manual Install:**
1. **Copy files** to `C:\ArzanaMonitor\`
2. **Edit** `config.json` with your settings
3. **Run** `ArzanaOutlookMonitor.ps1`

## ⚙️ **Configuration**

Edit `config.json` to customize:

```json
{
    "FlaskServerUrl": "http://127.0.0.1:5000",
    "CheckIntervalSeconds": 30,
    "LogPath": "C:\\ArzanaMonitor\\logs\\",
    "MinConfidence": 50
}
```

## 🏃 **Running the Monitor**

### **Option 1: Desktop Shortcut**
- **Double-click** "Arzana Monitor" on desktop

### **Option 2: Command Line**
```powershell
cd C:\ArzanaMonitor
.\ArzanaOutlookMonitor.ps1
```

### **Option 3: As Windows Service**
1. **Download NSSM** from https://nssm.cc/download
2. **Run** `Install-Service.ps1`
3. **Service runs** automatically in background

## 📊 **Email Tags**

The monitor automatically tags emails with:

- 🟢 **Arzana-Ready** - Customer matched and parts mapped
- 🔵 **Arzana-CustomerMatched** - Customer found, parts need review
- 🟠 **Arzana-NeedsReview** - Customer needs manual review
- 🔴 **Arzana-Error** - Processing error occurred
- ⚪ **Arzana-MissingInfo** - Missing required information

## 📝 **Logging**

Logs are saved to: `C:\ArzanaMonitor\logs\ArzanaMonitor.log`

**Log levels:**
- **INFO** - Normal operations
- **WARN** - Warnings (non-critical issues)
- **ERROR** - Errors that need attention

## 🔧 **Troubleshooting**

### **Monitor Not Starting:**
1. **Check Outlook** is running and accessible
2. **Check Flask server** is running on correct port
3. **Check logs** for error messages
4. **Run as Administrator**

### **No Emails Being Processed:**
1. **Check PO detection** keywords in config
2. **Check email content** matches detection criteria
3. **Check Flask server** is responding
4. **Check logs** for processing errors

### **Permission Errors:**
1. **Run PowerShell as Administrator**
2. **Check Outlook** is not in restricted mode
3. **Check execution policy**: `Get-ExecutionPolicy`

## 📁 **File Structure**

```
ArzanaPowerShell/
├── ArzanaOutlookMonitor.ps1    # Main monitoring script
├── config.json                 # Configuration file
├── Install-ArzanaMonitor.ps1   # Installation script
├── Install-Service.ps1         # Service installation
└── README.md                   # This file
```

## 🔄 **How It Works**

1. **Monitors Outlook** every 30 seconds for new emails
2. **Detects PO emails** using keyword analysis and confidence scoring
3. **Processes emails** by sending to your Flask server
4. **Tags emails** based on processing results
5. **Logs everything** for monitoring and debugging

## 🎯 **Advantages Over Office.js**

- ✅ **True background processing** - no user interaction needed
- ✅ **Processes ALL emails** - not just current email
- ✅ **Works 24/7** - even when you're not at computer
- ✅ **No Visual Studio needed** - just PowerShell
- ✅ **Easy deployment** - single script installation
- ✅ **Full Outlook access** - can read, modify, tag any email

## 🚨 **Important Notes**

- **Outlook must be running** for the monitor to work
- **Flask server must be running** for processing to work
- **Monitor runs in foreground** unless installed as service
- **Check logs regularly** for any issues
- **Test with sample PO emails** before going live

## 📞 **Support**

For issues or questions:
1. **Check the logs** first
2. **Verify Flask server** is running and accessible
3. **Test with simple PO emails** to verify detection
4. **Check Outlook** is not in restricted mode

---

**This PowerShell solution gives you the automatic processing you wanted, similar to what VSTO would have provided, but without the Visual Studio complexity!**

# Arzana Outlook Monitor - Microsoft Graph API Version

This version uses Microsoft Graph API instead of COM, making it more reliable and platform-independent.

## Setup Instructions

### 1. Complete Azure App Registration

You've already done this! Your credentials:
- **Application ID:** `a92ff10d-c813-4cd3-a5de-bd66ceef1e87`
- **Tenant ID:** `27d88747-62fe-4596-8e98-aa7036b05259`
- **Client Secret:** (you need to create this and copy it)

### 2. Create Client Secret (if not done yet)

1. Go to https://portal.azure.com
2. Navigate to **App registrations** → **Arzana PO Processor**
3. Click **"Certificates & secrets"**
4. Click **"+ New client secret"**
5. Description: `Arzana Monitor Secret`
6. Expires: `24 months`
7. Click **"Add"**
8. **IMMEDIATELY COPY THE SECRET VALUE** (shown once!)

### 3. Add API Permissions

1. In your app registration, click **"API permissions"**
2. Click **"+ Add a permission"**
3. Select **"Microsoft Graph"**
4. Select **"Application permissions"** (NOT Delegated)
5. Add these permissions:
   - ✅ `Mail.Read` - Read mail in all mailboxes
   - ✅ `Mail.ReadWrite` - Read and write mail in all mailboxes
6. Click **"Add permissions"**
7. Click **"Grant admin consent for [Your Organization]"** ← VERY IMPORTANT!
8. Click **"Yes"**

### 4. Configure the Monitor

1. Open `config.json`
2. Replace `YOUR_CLIENT_SECRET_HERE` with your actual client secret
3. Replace `YOUR_EMAIL@DOMAIN.COM` with your email address (e.g., william@arzana.ai)
4. Save the file

### 5. Run the Monitor

**Option 1: Double-click**
- Double-click `Start-ArzanaGraphMonitor.bat`

**Option 2: Command line**
```cmd
cd C:\Users\willt\Downloads\Koike\ArzanaGraphAPI
Start-ArzanaGraphMonitor.bat
```

## Features

✅ **No COM issues** - Uses REST API instead of Outlook COM
✅ **More reliable** - OAuth 2.0 authentication
✅ **Scans entire inbox** - Finds all unprocessed emails
✅ **Color-coded tags:**
   - 🟢 Green: "Approved" (manual)
   - 🟡 Yellow: "Pending Approval" (high confidence, ready)
   - 🔴 Red: "Missing Info" (needs attention)
✅ **Works without Outlook desktop** - Accesses mailbox directly
✅ **Can run on any machine** - Even servers without Outlook installed

## Troubleshooting

### "Failed to get access token: unauthorized_client"
- Make sure you granted admin consent for the API permissions
- Wait a few minutes after granting consent

### "Failed to get access token: invalid_client"
- Check that your client secret is correct in `config.json`
- Secrets expire - create a new one if needed

### "Forbidden" or "Access denied"
- Make sure you added **Application permissions** (not Delegated)
- Make sure you clicked "Grant admin consent"
- Use the correct email address in `config.json`

### No emails found
- Check that `user_email` in `config.json` is correct
- Make sure emails are in the Inbox folder
- Check the monitor.log file for details

## Configuration Options

Edit `config.json`:
- `check_interval_seconds`: How often to check for new emails (default: 30)
- `flask_server_url`: Your Flask server URL (default: http://127.0.0.1:5000)

## Logs

All activity is logged to `monitor.log` in the same directory.

# Outlook Add-in Installation Troubleshooting

## Common Installation Issues and Solutions

### 1. "Add-in installation failed" Error

**Possible Causes:**
- SSL certificate issues
- Manifest validation errors
- Missing icon files
- Server not accessible

**Solutions:**

#### Step 1: Verify Servers are Running
```bash
# Test Flask backend
python test_servers.py

# Or manually check:
# Visit https://localhost:5000/api/health in your browser
# Visit https://localhost:3000/health in your browser
```

#### Step 2: Accept SSL Certificates
1. Open your browser
2. Go to `https://localhost:3000`
3. Click "Advanced" → "Proceed to localhost (unsafe)"
4. Go to `https://localhost:5000/api/health`
5. Click "Advanced" → "Proceed to localhost (unsafe)"

#### Step 3: Use the Fixed Manifest
Use `manifest_fixed.xml` instead of `manifest.xml`:
- Copy `manifest_fixed.xml` to `manifest.xml`
- The fixed version has corrected URLs and icon references

#### Step 4: Check Outlook Version
- Outlook 2016 or later required
- Outlook on the web (modern Outlook) recommended for development

### 2. "Cannot load add-in" Error

**Solutions:**

#### Clear Outlook Cache
1. Close Outlook completely
2. Delete cache files:
   - Windows: `%LOCALAPPDATA%\Microsoft\Office\16.0\Wef\`
   - Or search for "Wef" folder in your AppData
3. Restart Outlook

#### Reset Add-ins
1. Open Outlook
2. File → Options → Add-ins
3. Remove any failed add-ins
4. Try installing again

### 3. "Add-in button not appearing" Error

**Solutions:**

#### Check Email Type
- Add-in only appears on **email messages**, not calendar items
- Open a regular email (not appointment)

#### Check Message Read Surface
- Add-in appears in the **message ribbon** when reading emails
- Look for "PO Processor" group in the ribbon

#### Enable Developer Mode (if needed)
1. File → Options → Trust Center → Trust Center Settings
2. Trusted Add-in Catalogs
3. Check "Show in Menu" if available

### 4. "Task pane not loading" Error

**Solutions:**

#### Check Browser Compatibility
- Use modern browser (Chrome, Edge, Firefox)
- Disable ad blockers for localhost

#### Check Console Errors
1. Open browser developer tools (F12)
2. Check Console tab for JavaScript errors
3. Check Network tab for failed requests

### 5. "Backend API errors" Error

**Solutions:**

#### Verify Flask Backend
```bash
# Check if Flask is running
python app.py

# Test API endpoint
curl -k https://localhost:5000/api/health
```

#### Check CORS Settings
The Flask backend should have CORS enabled for localhost:3000

## Step-by-Step Installation Guide

### Method 1: Sideloading (Recommended for Development)

1. **Start both servers:**
   ```bash
   # Terminal 1
   python app.py
   
   # Terminal 2
   python outlook_addin_server.py
   ```

2. **Accept SSL certificates in browser:**
   - Visit `https://localhost:3000`
   - Visit `https://localhost:5000/api/health`
   - Accept self-signed certificates

3. **Install in Outlook Desktop:**
   - Open Outlook
   - File → Get Add-ins
   - Click "Add a custom add-in" → "Add from file"
   - Select `manifest_fixed.xml`
   - Click "Install"

4. **Install in Outlook on the web:**
   - Go to Outlook on the web
   - Click gear icon → Get Add-ins
   - Click "Upload My Add-in"
   - Upload `manifest_fixed.xml`

### Method 2: Network Share (Alternative)

1. **Share the manifest file:**
   - Copy `manifest_fixed.xml` to a network share
   - Or use a web server to host it

2. **Install from URL:**
   - Use the network share URL in Outlook
   - Or use `https://localhost:3000/manifest_fixed.xml`

## Testing the Add-in

1. **Open a test email** with PO content:
   - Subject: "Purchase Order #12345"
   - Body with PO keywords
   - PDF attachment (optional)

2. **Look for the add-in button:**
   - Should appear in message ribbon
   - Look for "PO Processor" group
   - Click "Process PO" button

3. **Verify task pane loads:**
   - Should show PO detection status
   - Should process email content
   - Should display JSON payload

## Advanced Troubleshooting

### Enable Outlook Add-in Logging

1. **Registry Edit (Windows):**
   ```
   HKEY_CURRENT_USER\Software\Microsoft\Office\16.0\WEF\Developer
   Create DWORD: EnableRuntimeLogging = 1
   ```

2. **Check logs:**
   - `%LOCALAPPDATA%\Microsoft\Office\16.0\Wef\Logs\`

### Manifest Validation

Use Microsoft's manifest validator:
- Visit: https://docs.microsoft.com/en-us/office/dev/add-ins/testing/troubleshoot-manifest
- Upload your manifest file for validation

### Network Issues

If localhost doesn't work:
1. Use your computer's IP address instead
2. Update manifest URLs to use IP address
3. Ensure firewall allows connections

## Getting Help

If issues persist:

1. **Check server logs:**
   - Flask backend console output
   - Add-in server console output

2. **Browser developer tools:**
   - F12 → Console tab for JavaScript errors
   - Network tab for failed requests

3. **Outlook add-in logs:**
   - Check Windows Event Viewer
   - Look for Office add-in related errors

4. **Test with minimal manifest:**
   - Use only basic TaskPane mode
   - Remove VersionOverrides temporarily

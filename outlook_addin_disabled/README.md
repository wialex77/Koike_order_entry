# Outlook Add-in (Disabled)

This folder contains all the Outlook add-in related files that have been disabled to improve performance and reduce complexity.

## Files in this folder:

- `OUTLOOK_ADDIN_README.md` - Original documentation for the Outlook add-in
- `OUTLOOK_ADDIN_SUMMARY.md` - Summary of the add-in functionality
- `TROUBLESHOOTING_OUTLOOK_ADDIN.md` - Troubleshooting guide
- `install_addin.py` - Installation helper script
- `setup_outlook_addin.py` - Setup script for the add-in
- `start_outlook_addin.py` - Script to start the add-in server
- `outlook_addin_server.py` - Flask server for the add-in
- `test_servers.py` - Test script for both servers
- `create_ssl_cert.py` - SSL certificate creation for development
- `manifest.xml` - Outlook add-in manifest
- `manifest_fixed.xml` - Fixed version of the manifest
- `taskpane.html` - HTML interface for the add-in

## To re-enable:

1. Move the files back to the root directory
2. Uncomment the Outlook add-in related code in `app.py`
3. Install any additional dependencies if needed
4. Follow the original setup instructions in `OUTLOOK_ADDIN_README.md`

## Current Status:

The main Flask application (`app.py`) has the Outlook add-in functionality commented out to improve performance. The core PO processing functionality remains fully functional.

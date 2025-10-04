"""
Simple web server to host the Outlook add-in files.
This serves the HTML, CSS, and JavaScript files needed for the Outlook add-in.
"""

import os
import ssl
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for Outlook add-in

# Serve static files from the current directory
@app.route('/')
def index():
    return send_from_directory('.', 'taskpane.html')

@app.route('/<path:filename>')
def serve_file(filename):
    """Serve static files for the Outlook add-in."""
    if filename == 'taskpane.html':
        return send_from_directory('.', 'taskpane.html')
    elif filename.endswith('.js'):
        return send_from_directory('.', filename)
    elif filename.endswith('.css'):
        return send_from_directory('.', filename)
    elif filename.endswith('.png'):
        return send_from_directory('.', filename)
    else:
        return send_from_directory('.', filename)

# Health check endpoint
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'outlook-addin-server'})

if __name__ == '__main__':
    print("Starting Outlook Add-in Server...")
    print("This server hosts the files needed for the Outlook add-in.")
    print("Access the add-in at: https://localhost:3000")
    
    # Create self-signed certificate for HTTPS (required by Outlook)
    try:
        # For development, you can create a self-signed certificate
        # In production, use a proper SSL certificate
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.load_cert_chain('cert.pem', 'key.pem')
        
        app.run(host='0.0.0.0', port=3000, ssl_context=context, debug=True)
    except FileNotFoundError:
        print("SSL certificate files not found. Please create cert.pem and key.pem")
        print("For development, you can generate them with:")
        print("openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes")
        app.run(host='0.0.0.0', port=3000, debug=True)

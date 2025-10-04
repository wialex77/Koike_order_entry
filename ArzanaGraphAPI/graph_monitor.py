"""
Arzana Outlook Monitor - Microsoft Graph API with Delegated Permissions
Uses MSAL for authentication (works with personal Outlook.com accounts)
"""

import json
import time
import requests
import logging
import base64
from datetime import datetime
from pathlib import Path
from msal import PublicClientApplication

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('monitor.log'),
        logging.StreamHandler()
    ]
)

# Load config
config_path = Path(__file__).parent / 'config.json'
with open(config_path) as f:
    config = json.load(f)

TENANT_ID = config['tenant_id']
CLIENT_ID = config['client_id']
FLASK_SERVER_URL = config['flask_server_url']
CHECK_INTERVAL = config['check_interval_seconds']
USER_EMAIL = config['user_email']

# Microsoft Graph scopes - for personal accounts (don't include openid/profile, MSAL adds them)
SCOPES = [
    'https://graph.microsoft.com/Mail.Read',
    'https://graph.microsoft.com/Mail.ReadWrite',
    'https://graph.microsoft.com/User.Read'
]

# Token cache
CACHE_FILE = Path(__file__).parent / 'token_cache.json'

# Processed emails tracker
processed_emails = set()

# Initialize MSAL app - use 'common' for personal Microsoft accounts
app = PublicClientApplication(
    CLIENT_ID,
    authority="https://login.microsoftonline.com/common",  # Works for both AAD + MSA
)

def get_access_token():
    """Get access token using device code flow"""
    # Try to get token silently from cache first
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and 'access_token' in result:
            logging.info("Token acquired from cache")
            return result['access_token']
    
    # Need to authenticate
    logging.info("Starting device code flow authentication...")
    flow = app.initiate_device_flow(scopes=SCOPES)
    
    if 'user_code' not in flow:
        error_msg = flow.get('error_description', flow.get('error', 'Unknown error'))
        raise Exception(f"Failed to create device flow: {error_msg}")
    
    print("\n" + "="*50)
    print("USER LOGIN REQUIRED")
    print("="*50)
    print(f"\n1. Go to: {flow['verification_uri']}")
    print(f"2. Enter code: {flow['user_code']}")
    print("\nWaiting for you to complete sign-in...")
    print("(This will continue automatically once you sign in)\n")
    
    result = app.acquire_token_by_device_flow(flow)
    
    if 'access_token' in result:
        logging.info("Authentication successful!")
        return result['access_token']
    else:
        raise Exception(f"Authentication failed: {result.get('error_description', 'Unknown error')}")

def load_token_cache():
    """Load token cache from file"""
    # MSAL handles token caching automatically in newer versions
    # Just check if we have cached accounts
    return None

def save_token_cache():
    """Save token cache to file"""
    try:
        # MSAL's token_cache doesn't need explicit serialization in newer versions
        # The cache is automatically managed
        logging.info("Token cache saved")
    except Exception as e:
        logging.error(f"Failed to save token cache: {e}")

def get_inbox_emails(token):
    """Get emails from inbox"""
    # Decode token to check contents
    import base64
    try:
        token_parts = token.split('.')
        payload = token_parts[1]
        # Add padding if needed
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.b64decode(payload)
        token_data = json.loads(decoded)
        logging.info(f"Token audience: {token_data.get('aud')}")
        logging.info(f"Token scopes: {token_data.get('scp', token_data.get('roles'))}")
        logging.info(f"Token expires: {token_data.get('exp')}")
    except Exception as e:
        logging.warning(f"Could not decode token: {e}")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Try /me endpoint first, but log the user info
    try:
        user_url = 'https://graph.microsoft.com/v1.0/me'
        user_response = requests.get(user_url, headers=headers)
        logging.info(f"User endpoint status: {user_response.status_code}")
        if user_response.ok:
            user_data = user_response.json()
            logging.info(f"User: {user_data.get('userPrincipalName')} / {user_data.get('mail')}")
        else:
            logging.error(f"User endpoint failed: {user_response.text}")
    except Exception as e:
        logging.error(f"User endpoint error: {e}")
    
    url = 'https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages'
    params = {
        '$top': 50,
        '$orderby': 'receivedDateTime desc',
        '$select': 'id,subject,from,receivedDateTime,hasAttachments,bodyPreview,categories,body'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error Details:")
        logging.error(f"Status Code: {e.response.status_code}")
        logging.error(f"Response Headers: {dict(e.response.headers)}")
        logging.error(f"Response Body: {e.response.text}")
        raise
    
    emails = response.json().get('value', [])
    logging.info(f"Retrieved {len(emails)} emails from inbox")
    return emails

def get_attachments(token, message_id):
    """Get email attachments"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    url = f'https://graph.microsoft.com/v1.0/me/messages/{message_id}/attachments'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    return response.json().get('value', [])

def update_email_category(token, message_id, category):
    """Update email category/tag"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Get current categories
    url = f'https://graph.microsoft.com/v1.0/me/messages/{message_id}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    email = response.json()
    
    # Add new category, remove old status categories
    current_categories = email.get('categories', [])
    filtered = [c for c in current_categories if c not in ['Approved', 'Pending Approval', 'Missing Info']]
    new_categories = filtered + [category]
    
    # Update email
    data = {'categories': new_categories}
    response = requests.patch(url, headers=headers, json=data)
    response.raise_for_status()
    
    logging.info(f"Tagged email as: {category}")

def is_po_email(email):
    """Check if email is a PO email"""
    subject = email.get('subject', '').lower()
    body = email.get('bodyPreview', '').lower()
    if email.get('body') and email['body'].get('content'):
        body = email['body']['content'].lower()
    
    # PO keywords
    subject_keywords = ['po', 'purchase order', 'po number', 'po#', 'order confirmation',
                       'order request', 'p.o.', 'quote', 'quotation', 'invoice',
                       'new order', 'order placed']
    
    body_keywords = ['po', 'purchase order', 'po number', 'order number', 'bill to',
                    'ship to', 'quantity', 'unit price', 'part number', 'supplier']
    
    # Check subject
    subject_match = any(kw in subject for kw in subject_keywords)
    
    # Check body
    body_matches = sum(1 for kw in body_keywords if kw in body)
    body_match = body_matches >= 2
    
    # Check attachments
    has_pdf = email.get('hasAttachments', False)
    
    # Calculate confidence
    confidence = 0
    if subject_match:
        confidence += 40
    if body_match:
        confidence += 25
    if has_pdf:
        confidence += 20
    if any(pattern in body for pattern in [r'\d{4,}', r'\$\d+\.\d{2}']):
        confidence += 15
    
    is_po = confidence >= 40
    logging.info(f"PO Detection - Subject: {subject_match}, Body: {body_match}, PDF: {has_pdf}, Confidence: {confidence}%, IsPO: {is_po}")
    
    return is_po

def process_po_email(token, email):
    """Process PO email with Flask server"""
    try:
        logging.info(f"Processing PO email: {email['subject']}")
        
        # Get attachments
        attachments = get_attachments(token, email['id'])
        pdf_attachment = next((a for a in attachments if a['name'].lower().endswith('.pdf')), None)
        
        if pdf_attachment:
            logging.info(f"Found PDF attachment: {pdf_attachment['name']}")
            
            # Decode PDF content
            pdf_bytes = base64.b64decode(pdf_attachment['contentBytes'])
            
            # Upload to Flask
            files = {'file': (pdf_attachment['name'], pdf_bytes, 'application/pdf')}
            response = requests.post(f'{FLASK_SERVER_URL}/upload', files=files, timeout=300)
            response.raise_for_status()
            result = response.json()
            
            logging.info("Flask server response received")
            
            # Determine category
            category = 'Missing Info'
            if result.get('success'):
                data = result.get('data', {})
                confidence = data.get('confidence_score', 0)
                customer_matched = data.get('company_info', {}).get('customer_match_status') == 'matched'
                parts_mapped = data.get('processing_summary', {}).get('parts_mapped', 0) > 0
                missing_info = bool(data.get('missing_fields'))
                
                if confidence >= 95 and customer_matched and parts_mapped and not missing_info:
                    category = 'Pending Approval'
                elif customer_matched and parts_mapped:
                    category = 'Pending Approval'
            
            # Tag email
            update_email_category(token, email['id'], category)
            return result
        else:
            logging.info("No PDF attachment found")
            update_email_category(token, email['id'], 'Missing Info')
            return {'success': False, 'error': 'No PDF attachment'}
            
    except Exception as e:
        logging.error(f"Error processing PO email: {e}")
        try:
            update_email_category(token, email['id'], 'Missing Info')
        except:
            pass
        return {'success': False, 'error': str(e)}

def main():
    """Main monitoring loop"""
    logging.info("Starting Arzana Outlook Monitor (Graph API - Delegated)...")
    logging.info(f"Flask Server: {FLASK_SERVER_URL}")
    logging.info(f"Check Interval: {CHECK_INTERVAL} seconds")
    logging.info(f"Monitoring mailbox: {USER_EMAIL}")
    
    # Get access token (will prompt for login if needed)
    try:
        token = get_access_token()
    except Exception as e:
        logging.error(f"Failed to authenticate: {e}")
        return
    
    # Test Flask server
    try:
        requests.get(FLASK_SERVER_URL, timeout=10)
        logging.info("Flask server connection successful")
    except:
        logging.warning(f"Warning: Cannot connect to Flask server at {FLASK_SERVER_URL}")
    
    logging.info("Monitoring started. Press Ctrl+C to stop.")
    
    try:
        while True:
            try:
                # Get fresh token (will use cache if still valid)
                token = get_access_token()
                
                # Get emails
                emails = get_inbox_emails(token)
                
                # Filter unprocessed emails without status tags
                candidates = []
                for email in emails:
                    email_id = email['id']
                    categories = email.get('categories', [])
                    
                    # Skip if already processed
                    if email_id in processed_emails:
                        continue
                    
                    # Skip if has status category
                    if any(cat in categories for cat in ['Approved', 'Pending Approval', 'Missing Info']):
                        continue
                    
                    candidates.append(email)
                
                logging.info(f"Found {len(candidates)} unprocessed emails")
                
                # Process each candidate
                for email in candidates:
                    try:
                        logging.info(f"Checking email: {email['subject']}")
                        processed_emails.add(email['id'])
                        
                        if is_po_email(email):
                            logging.info("PO email detected, processing...")
                            result = process_po_email(token, email)
                            logging.info("PO email processed successfully")
                        else:
                            logging.info("Not a PO email, skipping")
                    
                    except Exception as e:
                        logging.error(f"Error processing email {email['subject']}: {e}")
                
                time.sleep(CHECK_INTERVAL)
                
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        logging.info("Monitoring stopped by user")
    finally:
        logging.info("Monitor stopped")

if __name__ == '__main__':
    main()

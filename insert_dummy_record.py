#!/usr/bin/env python3
"""
Script to insert a new row with dummy data into processing_results table using Supabase REST API
This script uses the same IPv4 workaround method that successfully retrieved data.
"""

import os
import json
import requests
import socket
from datetime import datetime
from dotenv import load_dotenv

def force_ipv4():
    """Force IPv4 connections by monkey-patching socket."""
    original_getaddrinfo = socket.getaddrinfo
    
    def getaddrinfo_ipv4(*args, **kwargs):
        responses = original_getaddrinfo(*args, **kwargs)
        # Filter to only IPv4 addresses
        return [response for response in responses if response[0] == socket.AF_INET]
    
    socket.getaddrinfo = getaddrinfo_ipv4

def load_env_file(env_file_path):
    """Load environment variables from a .env file."""
    if not os.path.exists(env_file_path):
        print(f"Environment file not found: {env_file_path}")
        return False
    
    with open(env_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
    return True

def create_dummy_processing_result():
    """Create a dummy processing result record."""
    now = datetime.now()
    
    # Generate a unique filename based on timestamp
    timestamp = now.strftime('%Y%m%d_%H%M%S')
    filename = f"processed_{timestamp}.json"
    
    dummy_data = {
        'filename': filename,
        'original_filename': 'dummy_test_file.pdf',
        'file_size': 123456,
        'processing_status': 'completed',
        'validation_status': 'correct',
        'processing_start_time': now.isoformat(),
        'processing_end_time': now.isoformat(),
        'processing_duration': 45.67,
        'total_parts': 25,
        'parts_mapped': 22,
        'parts_not_found': 2,
        'parts_manual_review': 1,
        'mapping_success_rate': 0.88,
        'customer_matched': True,
        'customer_match_confidence': 0.95,
        'error_types': json.dumps(['account_number', 'shipping_address']),
        'error_details': 'Minor formatting issues with account number and shipping address',
        'manual_corrections_made': 3,
        'epicor_ready': True,
        'epicor_ready_with_one_click': True,
        'missing_info_count': 0,
        'processed_file_path': f'processed/{filename}',
        'epicor_json_path': f'epicor/{filename}',
        'raw_json_data': json.dumps({
            'customer': 'Test Customer Inc.',
            'parts': [
                {'part_number': 'TEST001', 'quantity': 5},
                {'part_number': 'TEST002', 'quantity': 3}
            ],
            'total_amount': 1250.50
        }),
        'notes': 'This is a test record created via REST API',
        'created_at': now.isoformat(),
        'updated_at': now.isoformat()
    }
    
    return dummy_data

def insert_dummy_record():
    """Insert a dummy record into the processing_results table using Supabase REST API with IPv4."""
    
    # Force IPv4 connections
    force_ipv4()
    
    # Load environment variables
    env_file = os.path.join(os.path.dirname(__file__), 'config.env')
    if not load_env_file(env_file):
        return
    
    # Extract project reference from database host
    db_host = os.environ.get('DB_HOST', 'db.lctdvwthxetczwyslibv.supabase.co')
    project_ref = db_host.replace('db.', '').replace('.supabase.co', '')
    supabase_url = f"https://{project_ref}.supabase.co"
    
    print(f"Inserting dummy record via Supabase REST API at: {supabase_url}")
    print("Using IPv4 connectivity workaround...")
    
    # Get the API key from environment
    api_key = os.environ.get('SUPABASE_ANON_KEY')
    
    if not api_key:
        print("No Supabase API key found in environment variables.")
        print("Make sure SUPABASE_ANON_KEY is set in config.env")
        return
    
    print(f"Using Supabase API key: {api_key[:20]}...")
    headers = {
        'apikey': api_key,
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Create dummy data
        dummy_data = create_dummy_processing_result()
        
        print("\n" + "="*80)
        print("INSERTING DUMMY RECORD")
        print("="*80)
        
        print("Dummy data to insert:")
        for key, value in dummy_data.items():
            if isinstance(value, str) and len(value) > 100:
                print(f"   {key}: {value[:100]}...")
            else:
                print(f"   {key}: {value}")
        
        # Insert the record
        insert_url = f"{supabase_url}/rest/v1/processing_results"
        
        print(f"\nInserting record at: {insert_url}")
        response = requests.post(insert_url, headers=headers, json=dummy_data, timeout=30)
        
        if response.status_code == 201:
            print("✅ Successfully inserted dummy record!")
            inserted_data = response.json()
            
            if inserted_data:
                print(f"\nInserted record details:")
                for key, value in inserted_data[0].items():
                    if isinstance(value, str) and len(value) > 100:
                        print(f"   {key}: {value[:100]}...")
                    else:
                        print(f"   {key}: {value}")
            
            # Verify the insertion by querying the record
            print("\n" + "="*80)
            print("VERIFYING INSERTION")
            print("="*80)
            
            # Query for the record we just inserted
            query_url = f"{supabase_url}/rest/v1/processing_results"
            params = {
                'select': '*',
                'filename': f'eq.{dummy_data["filename"]}'
            }
            
            verify_response = requests.get(query_url, headers=headers, params=params, timeout=30)
            
            if verify_response.status_code == 200:
                verify_data = verify_response.json()
                if verify_data:
                    print(f"✅ Verification successful! Found {len(verify_data)} record(s)")
                    print(f"Record ID: {verify_data[0]['id']}")
                    print(f"Filename: {verify_data[0]['filename']}")
                    print(f"Processing Status: {verify_data[0]['processing_status']}")
                    print(f"Validation Status: {verify_data[0]['validation_status']}")
                else:
                    print("❌ Verification failed - record not found")
            else:
                print(f"❌ Verification query failed with status: {verify_response.status_code}")
                print(f"Response: {verify_response.text}")
            
        elif response.status_code == 400:
            print("❌ Bad request (400)")
            print("Possible issues:")
            print("1. Invalid data format")
            print("2. Missing required fields")
            print("3. Data type mismatches")
            print(f"Response: {response.text}")
            
        elif response.status_code == 401:
            print("❌ Authentication failed (401)")
            print("Check your Supabase API key")
            
        elif response.status_code == 403:
            print("❌ Forbidden (403)")
            print("Your API key doesn't have INSERT permissions")
            print("Make sure you're using the 'anon' key with proper RLS policies")
            
        else:
            print(f"❌ Insert failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    insert_dummy_record()

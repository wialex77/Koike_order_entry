#!/usr/bin/env python3
"""
Workaround script to query processing_results table using Supabase REST API
This script forces IPv4 connectivity and bypasses the PostgreSQL connection issue.
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

def query_supabase_rest_api():
    """Query the processing_results table using Supabase REST API with IPv4."""
    
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
    
    print(f"Querying Supabase REST API at: {supabase_url}")
    print("Using IPv4 connectivity workaround...")
    
    # Try to get the API key from environment
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
        # Test connection
        print("Testing connection...")
        test_response = requests.get(supabase_url, headers=headers, timeout=10)
        print(f"Connection test status: {test_response.status_code}")
        
        if test_response.status_code == 404:
            print("✅ Supabase REST API is accessible (404 is expected for root endpoint)")
        elif test_response.status_code == 200:
            print("✅ Supabase REST API is accessible")
        else:
            print(f"⚠️ Unexpected status: {test_response.status_code}")
        
        # Query the processing_results table
        print("\n" + "="*80)
        print("QUERYING PROCESSING RESULTS TABLE")
        print("="*80)
        
        query_url = f"{supabase_url}/rest/v1/processing_results"
        
        # Get all records (with limit)
        params = {
            'select': '*',
            'limit': '100'
        }
        
        print(f"Querying: {query_url}")
        response = requests.get(query_url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Successfully retrieved {len(data)} records")
            
            if not data:
                print("No records found in processing_results table.")
                return
            
            # Display sample records
            print(f"\nSample records (showing first 5):")
            print("-" * 80)
            
            for i, record in enumerate(data[:5], 1):
                print(f"\nRecord #{i}:")
                for key, value in record.items():
                    if value is not None:
                        # Truncate long values for display
                        if isinstance(value, str) and len(value) > 100:
                            value = value[:100] + "..."
                        print(f"   {key}: {value}")
                    else:
                        print(f"   {key}: NULL")
            
            # Get basic statistics
            print("\n" + "="*80)
            print("BASIC STATISTICS")
            print("="*80)
            
            # Count by processing status
            status_counts = {}
            validation_counts = {}
            total_duration = 0
            duration_count = 0
            
            for record in data:
                # Processing status
                status = record.get('processing_status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Validation status
                validation = record.get('validation_status', 'unknown')
                validation_counts[validation] = validation_counts.get(validation, 0) + 1
                
                # Processing duration
                duration = record.get('processing_duration')
                if duration is not None:
                    total_duration += duration
                    duration_count += 1
            
            print("Processing Status Distribution:")
            for status, count in status_counts.items():
                print(f"   {status}: {count}")
            
            print("\nValidation Status Distribution:")
            for status, count in validation_counts.items():
                print(f"   {status}: {count}")
            
            if duration_count > 0:
                avg_duration = total_duration / duration_count
                print(f"\nAverage Processing Duration: {avg_duration:.2f} seconds")
            
            # Save results to JSON file
            print("\n" + "="*80)
            print("SAVING RESULTS TO JSON")
            print("="*80)
            
            output_data = {
                'query_timestamp': datetime.now().isoformat(),
                'total_records': len(data),
                'supabase_url': supabase_url,
                'statistics': {
                    'processing_status_distribution': status_counts,
                    'validation_status_distribution': validation_counts,
                    'average_processing_duration': total_duration / duration_count if duration_count > 0 else None
                },
                'records': data
            }
            
            output_file = f"processing_results_rest_api_ipv4_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"Results saved to: {output_file}")
            
        elif response.status_code == 401:
            print("❌ Authentication required (401)")
            print("\nTo fix this:")
            print("1. Go to https://supabase.com/dashboard")
            print("2. Select your project")
            print("3. Go to Settings > API")
            print("4. Copy your 'anon' key")
            print("5. Add it to config.env: SUPABASE_ANON_KEY=your-anon-key-here")
            print("6. Run this script again")
            
        elif response.status_code == 404:
            print("❌ Table not found (404)")
            print("The 'processing_results' table might not exist in your Supabase database.")
            print("Check your Supabase dashboard to verify the table exists.")
            
        else:
            print(f"❌ Query failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        print("\nPossible solutions:")
        print("1. Check your internet connection")
        print("2. Try using a VPN")
        print("3. Check if your firewall is blocking the connection")
        print("4. Try from a different network")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    query_supabase_rest_api()

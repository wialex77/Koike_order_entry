#!/usr/bin/env python3
"""
Simple script to query processing_results table using Supabase REST API.
Add your SUPABASE_ANON_KEY to config.env and run this script.
"""

import os
import json
import requests
from datetime import datetime

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

def query_processing_results():
    """Query the processing_results table using Supabase REST API."""
    
    # Load environment variables
    env_file = os.path.join(os.path.dirname(__file__), 'config.env')
    if not load_env_file(env_file):
        return
    
    # Extract project reference from database host
    db_host = os.environ.get('DB_HOST', 'db.lctdvwthxetczwyslibv.supabase.co')
    project_ref = db_host.replace('db.', '').replace('.supabase.co', '')
    supabase_url = f"https://{project_ref}.supabase.co"
    
    # Get API key
    api_key = os.environ.get('SUPABASE_ANON_KEY')
    if not api_key:
        print("SUPABASE_ANON_KEY not found in config.env")
        print("Please add your Supabase anon key to config.env:")
        print("SUPABASE_ANON_KEY=your-anon-key-here")
        print("\nTo get your anon key:")
        print("1. Go to https://supabase.com/dashboard")
        print("2. Select your project")
        print("3. Go to Settings > API")
        print("4. Copy the 'anon' key")
        return
    
    headers = {
        'apikey': api_key,
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        print(f"Querying Supabase at: {supabase_url}")
        
        # Query processing_results table
        query_url = f"{supabase_url}/rest/v1/processing_results"
        params = {
            'select': '*',
            'limit': '100'
        }
        
        response = requests.get(query_url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Successfully retrieved {len(data)} records")
            
            if not data:
                print("No records found in processing_results table.")
                return
            
            # Display sample records
            print(f"\nSample records (showing first 3):")
            print("-" * 80)
            
            for i, record in enumerate(data[:3], 1):
                print(f"\nRecord #{i}:")
                for key, value in record.items():
                    if value is not None:
                        if isinstance(value, str) and len(value) > 100:
                            value = value[:100] + "..."
                        print(f"   {key}: {value}")
                    else:
                        print(f"   {key}: NULL")
            
            # Save results to JSON file
            output_file = f"processing_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"\nResults saved to: {output_file}")
            
        else:
            print(f"Query failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    query_processing_results()

#!/usr/bin/env python3
"""
Test script to debug the PostgreSQL connection with Transaction Pooler
"""

import os
import json
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

def test_postgres_connection():
    """Test PostgreSQL connection with Transaction Pooler."""
    
    # Force IPv4 connections
    force_ipv4()
    
    # Load environment variables
    env_file = os.path.join(os.path.dirname(__file__), 'config.env')
    if not load_env_file(env_file):
        return
    
    # Set environment to production to use PostgreSQL
    os.environ['FLASK_ENV'] = 'production'
    
    print("Testing PostgreSQL connection with Transaction Pooler...")
    
    try:
        # Import the database config
        from database_config import db_config
        
        print(f"Database config: {db_config.engine}")
        
        # Test basic connection
        test_sql = "SELECT 1 as test"
        result = db_config.execute_raw_sql_single(test_sql)
        print(f"✅ Basic connection test: {result}")
        
        # Test table existence
        table_check_sql = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'processing_results'
        """
        table_result = db_config.execute_raw_sql_single(table_check_sql)
        print(f"✅ Table exists: {table_result}")
        
        # Test raw query
        raw_sql = "SELECT * FROM processing_results LIMIT 3"
        raw_results = db_config.execute_raw_sql(raw_sql)
        print(f"✅ Raw query results: {len(raw_results)} rows")
        
        if raw_results:
            print("Sample raw row:")
            for i, row in enumerate(raw_results):
                print(f"Row {i}: {row}")
                if i >= 2:  # Show max 3 rows
                    break
        
        # Test count
        count_sql = "SELECT COUNT(*) FROM processing_results"
        count_result = db_config.execute_raw_sql_single(count_sql)
        print(f"✅ Total records: {count_result[0]}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_postgres_connection()

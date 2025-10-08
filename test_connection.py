#!/usr/bin/env python3
"""
Test database connection with IPv6 support
"""

import os
import psycopg2
import socket
from dotenv import load_dotenv

def test_connection():
    """Test database connection with IPv6 support."""
    
    load_dotenv('config.env')
    
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'postgres')
    db_user = os.environ.get('DB_USER', 'postgres')
    db_password = os.environ.get('DB_PASSWORD')
    
    print(f"Testing connection to: {db_host}:{db_port}")
    
    try:
        # Test DNS resolution
        print("Testing DNS resolution...")
        ip_addresses = socket.getaddrinfo(db_host, int(db_port), socket.AF_UNSPEC, socket.SOCK_STREAM)
        print(f"Resolved to: {ip_addresses}")
        
        # Try connecting with IPv6 support
        print("Attempting connection...")
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=10
        )
        
        print("✅ Connection successful!")
        
        # Test a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"PostgreSQL version: {version[0][:50]}...")
        
        # Test processing_results table
        cursor.execute("SELECT COUNT(*) FROM processing_results;")
        count = cursor.fetchone()[0]
        print(f"Processing results table has {count} records")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()

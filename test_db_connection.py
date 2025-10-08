#!/usr/bin/env python3
"""
Database Connection Diagnostic Script
Tests the PostgreSQL connection and identifies issues.
"""

import os
import psycopg2
from urllib.parse import quote_plus
from dotenv import load_dotenv

def test_database_connection():
    """Test database connection with detailed error reporting."""
    
    # Load environment variables
    load_dotenv('config.env')
    
    # Get environment variables
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'postgres')
    db_user = os.environ.get('DB_USER', 'postgres')
    db_password = os.environ.get('DB_PASSWORD')
    
    print("=== Database Connection Diagnostic ===")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"Host: {db_host}")
    print(f"Port: {db_port}")
    print(f"Database: {db_name}")
    print(f"User: {db_user}")
    print(f"Password: {'***' if db_password else 'NOT SET'}")
    print()
    
    # Check for missing variables
    missing_vars = []
    if not db_host:
        missing_vars.append('DB_HOST')
    if not db_password:
        missing_vars.append('DB_PASSWORD')
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("These need to be set in your AWS App Runner environment variables.")
        return False
    
    try:
        print("Attempting database connection...")
        
        # Test connection
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=10
        )
        
        print("✅ Connection successful!")
        
        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"PostgreSQL version: {version[0][:50]}...")
        
        # Test if processing_results table exists
        print("\nChecking for processing_results table...")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'processing_results'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("✅ processing_results table exists")
            
            # Check table structure
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'processing_results'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            print(f"Table has {len(columns)} columns:")
            for col_name, col_type in columns[:5]:  # Show first 5 columns
                print(f"  - {col_name}: {col_type}")
            if len(columns) > 5:
                print(f"  ... and {len(columns) - 5} more columns")
                
        else:
            print("❌ processing_results table does not exist")
            print("You need to create this table in your Supabase database.")
        
        # Test inserting a record
        print("\nTesting insert operation...")
        try:
            cursor.execute("""
                INSERT INTO processing_results (
                    filename, original_filename, file_size, processing_status, 
                    validation_status, processing_start_time, processed_file_path, 
                    raw_json_data, created_at, updated_at
                ) VALUES (
                    'test_connection.json', 'test.txt', 100, 'processing', 
                    'pending_review', NOW(), 'test.json', '{"test": true}', 
                    NOW(), NOW()
                ) RETURNING id;
            """)
            test_id = cursor.fetchone()[0]
            print(f"✅ Insert test successful! Created record with ID: {test_id}")
            
            # Clean up test record
            cursor.execute("DELETE FROM processing_results WHERE id = %s;", (test_id,))
            print("✅ Cleanup successful")
            
        except Exception as insert_error:
            print(f"❌ Insert test failed: {insert_error}")
        
        cursor.close()
        conn.close()
        print("\n✅ All tests passed! Database connection is working.")
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed (Operational Error): {e}")
        if "timeout" in str(e).lower():
            print("This might be a network connectivity issue.")
        elif "authentication" in str(e).lower():
            print("This might be a credentials issue.")
        return False
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_database_connection()
    if not success:
        print("\n=== Troubleshooting Tips ===")
        print("1. Check AWS App Runner environment variables")
        print("2. Verify Supabase database credentials")
        print("3. Ensure processing_results table exists")
        print("4. Check network connectivity from App Runner to Supabase")

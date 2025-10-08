#!/usr/bin/env python3
"""
Database Schema Diagnostic Script
Checks if the processing_results table exists and has the correct structure.
"""

import os
import psycopg2
from dotenv import load_dotenv

def check_database_schema():
    """Check database schema and table structure."""
    
    # Load environment variables
    load_dotenv('config.env')
    
    # Get environment variables
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'postgres')
    db_user = os.environ.get('DB_USER', 'postgres')
    db_password = os.environ.get('DB_PASSWORD')
    
    print("=== Database Schema Diagnostic ===")
    print(f"Host: {db_host}")
    print(f"Database: {db_name}")
    print()
    
    if not db_host or not db_password:
        print("❌ Missing database environment variables")
        return False
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=10
        )
        
        cursor = conn.cursor()
        
        # Check if processing_results table exists
        print("1. Checking if processing_results table exists...")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'processing_results'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("❌ processing_results table does not exist!")
            print("\nYou need to create this table in your Supabase database.")
            print("Go to Supabase Dashboard → SQL Editor and run:")
            print("""
CREATE TABLE processing_results (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size INTEGER NOT NULL,
    processing_status VARCHAR(50) NOT NULL,
    validation_status VARCHAR(50) NOT NULL,
    processing_start_time TIMESTAMP NOT NULL,
    processing_end_time TIMESTAMP,
    processing_duration FLOAT,
    total_parts INTEGER DEFAULT 0,
    parts_mapped INTEGER DEFAULT 0,
    parts_not_found INTEGER DEFAULT 0,
    parts_manual_review INTEGER DEFAULT 0,
    mapping_success_rate FLOAT DEFAULT 0.0,
    customer_matched BOOLEAN DEFAULT FALSE,
    customer_match_confidence FLOAT DEFAULT 0.0,
    error_details TEXT DEFAULT '',
    error_types JSON DEFAULT '[]',
    manual_corrections_made INTEGER DEFAULT 0,
    epicor_ready BOOLEAN DEFAULT FALSE,
    epicor_ready_with_one_click BOOLEAN DEFAULT FALSE,
    missing_info_count INTEGER DEFAULT 0,
    processed_file_path VARCHAR(500),
    epicor_json_path VARCHAR(500),
    raw_json_data TEXT DEFAULT '{}',
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
            """)
            return False
        
        print("✅ processing_results table exists")
        
        # Check table structure
        print("\n2. Checking table structure...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'processing_results'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        
        print(f"Table has {len(columns)} columns:")
        for col_name, col_type, nullable, default in columns:
            nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
            default_str = f" DEFAULT {default}" if default else ""
            print(f"  - {col_name}: {col_type} {nullable_str}{default_str}")
        
        # Check if we can insert a test record
        print("\n3. Testing insert operation...")
        try:
            cursor.execute("""
                INSERT INTO processing_results (
                    filename, original_filename, file_size, processing_status, 
                    validation_status, processing_start_time, processed_file_path, 
                    raw_json_data
                ) VALUES (
                    'schema_test.json', 'test.txt', 100, 'processing', 
                    'pending_review', NOW(), 'test.json', '{"test": true}'
                ) RETURNING id;
            """)
            test_id = cursor.fetchone()[0]
            print(f"✅ Insert test successful! Created record with ID: {test_id}")
            
            # Test retrieving the record
            print("\n4. Testing select operation...")
            cursor.execute("SELECT * FROM processing_results WHERE id = %s;", (test_id,))
            row = cursor.fetchone()
            
            if row:
                print(f"✅ Select test successful! Retrieved {len(row)} columns")
                print(f"Record data: ID={row[0]}, filename={row[1]}, status={row[4]}")
            else:
                print("❌ Select test failed - no data returned")
            
            # Clean up test record
            cursor.execute("DELETE FROM processing_results WHERE id = %s;", (test_id,))
            print("✅ Cleanup successful")
            
        except Exception as insert_error:
            print(f"❌ Insert test failed: {insert_error}")
            return False
        
        cursor.close()
        conn.close()
        print("\n✅ All schema tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == "__main__":
    success = check_database_schema()
    if not success:
        print("\n=== Next Steps ===")
        print("1. Create the processing_results table in Supabase")
        print("2. Verify your database credentials")
        print("3. Check network connectivity")

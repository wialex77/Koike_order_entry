#!/usr/bin/env python3
"""
Simple database test - just provide credentials as environment variables
"""

import os
import psycopg2
import json
from datetime import datetime
from dotenv import load_dotenv

def test_with_env_vars():
    """Test database using environment variables."""
    
    # Load environment variables
    load_dotenv('config.env')
    
    # Get credentials from environment
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'postgres')
    db_user = os.environ.get('DB_USER', 'postgres')
    db_password = os.environ.get('DB_PASSWORD')
    
    print("=== Database Test with Environment Variables ===")
    print(f"Host: {db_host}")
    print(f"Port: {db_port}")
    print(f"Database: {db_name}")
    print(f"User: {db_user}")
    print(f"Password: {'***' if db_password else 'NOT SET'}")
    print()
    
    if not db_host or not db_password:
        print("❌ Missing DB_HOST or DB_PASSWORD environment variables")
        print("Set them in your config.env file or environment")
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
        
        print("✅ Database connection successful!")
        
        cursor = conn.cursor()
        
        # Test the exact query from the code
        print("\nTesting the exact query from get_processing_result...")
        cursor.execute("""
            SELECT id, filename, original_filename, file_size, processing_status, 
                   validation_status, processing_start_time, processing_end_time, 
                   processing_duration, total_parts, parts_mapped, parts_not_found, 
                   parts_manual_review, mapping_success_rate, customer_matched, 
                   customer_match_confidence, error_details, error_types, 
                   manual_corrections_made, epicor_ready, epicor_ready_with_one_click, 
                   missing_info_count, processed_file_path, epicor_json_path, 
                   raw_json_data, notes, created_at, updated_at
            FROM processing_results ORDER BY id DESC LIMIT 1
        """)
        
        row = cursor.fetchone()
        if row:
            print(f"✅ Query successful! Retrieved {len(row)} columns")
            print(f"Sample record: ID={row[0]}, filename={row[1]}, status={row[4]}")
            
            # Test JSON parsing of error_types
            print(f"\nTesting error_types parsing...")
            print(f"Raw error_types (column 17): {repr(row[17])}")
            
            try:
                error_types = json.loads(row[17] or '[]')
                print(f"✅ JSON parsing successful: {error_types}")
            except Exception as e:
                print(f"❌ JSON parsing failed: {e}")
                print("This might be the issue!")
        else:
            print("❌ No records found in processing_results table")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Database test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_with_env_vars()

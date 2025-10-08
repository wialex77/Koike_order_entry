#!/usr/bin/env python3
"""
Test the exact same database connection logic used in the app
"""

import os
import psycopg2
from dotenv import load_dotenv

def test_app_database_logic():
    """Test the exact database logic from the app."""
    
    load_dotenv('config.env')
    
    # This mimics the database_config.py logic
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'postgres')
    db_user = os.environ.get('DB_USER', 'postgres')
    db_password = os.environ.get('DB_PASSWORD')
    
    print("=== Testing App Database Logic ===")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"Host: {db_host}")
    print(f"Port: {db_port}")
    print(f"Database: {db_name}")
    print(f"User: {db_user}")
    print(f"Password: {'***' if db_password else 'NOT SET'}")
    print()
    
    if not db_host or not db_password:
        print("❌ Missing required environment variables")
        return False
    
    try:
        # Test the exact connection string format
        connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        print(f"Connection string: postgresql://{db_user}:***@{db_host}:{db_port}/{db_name}")
        
        conn = psycopg2.connect(connection_string)
        print("✅ Connection successful!")
        
        cursor = conn.cursor()
        
        # Test the exact query from get_processing_result
        print("\nTesting get_processing_result query...")
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
            print(f"Sample: ID={row[0]}, filename={row[1]}, status={row[4]}")
            
            # Test error_types parsing
            print(f"\nTesting error_types parsing...")
            print(f"Raw error_types: {repr(row[17])}")
            
            import json
            try:
                error_types = json.loads(row[17] or '[]')
                print(f"✅ JSON parsing successful: {error_types}")
            except Exception as e:
                print(f"❌ JSON parsing failed: {e}")
        else:
            print("❌ No records found")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nThis is likely the same error you're seeing in AWS.")
        return False

if __name__ == "__main__":
    test_app_database_logic()

#!/usr/bin/env python3
"""
Comprehensive Database Test Script
Tests the actual Supabase database connection and table structure.
"""

import os
import psycopg2
import json
from datetime import datetime
from dotenv import load_dotenv

def test_database_comprehensive():
    """Test database connection and table structure comprehensively."""
    
    print("=== Comprehensive Database Test ===")
    print("Please provide your Supabase database credentials:")
    
    # Get credentials from user
    db_host = input("DB_HOST (e.g., db.xxxxx.supabase.co): ").strip()
    db_port = input("DB_PORT (default 5432): ").strip() or "5432"
    db_name = input("DB_NAME (default postgres): ").strip() or "postgres"
    db_user = input("DB_USER (default postgres): ").strip() or "postgres"
    db_password = input("DB_PASSWORD: ").strip()
    
    print(f"\nTesting connection to: {db_host}:{db_port}/{db_name}")
    print(f"User: {db_user}")
    print()
    
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
        
        # Test 1: Check table structure
        print("\n1. Checking table structure...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'processing_results'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        
        print(f"Table has {len(columns)} columns:")
        expected_columns = [
            'id', 'filename', 'original_filename', 'file_size', 'processing_status',
            'validation_status', 'processing_start_time', 'processing_end_time',
            'processing_duration', 'total_parts', 'parts_mapped', 'parts_not_found',
            'parts_manual_review', 'mapping_success_rate', 'customer_matched',
            'customer_match_confidence', 'error_types', 'error_details',
            'manual_corrections_made', 'epicor_ready', 'epicor_ready_with_one_click',
            'missing_info_count', 'processed_file_path', 'epicor_json_path',
            'raw_json_data', 'notes', 'created_at', 'updated_at'
        ]
        
        for i, (col_name, col_type, nullable, default) in enumerate(columns):
            expected = expected_columns[i] if i < len(expected_columns) else "UNEXPECTED"
            match = "✅" if col_name == expected else "❌"
            print(f"  {i:2d}: {col_name:25} ({col_type:15}) {match} {expected}")
        
        # Test 2: Check existing data
        print("\n2. Checking existing data...")
        cursor.execute("SELECT COUNT(*) FROM processing_results;")
        count = cursor.fetchone()[0]
        print(f"Total records: {count}")
        
        if count > 0:
            cursor.execute("SELECT id, filename, processing_status FROM processing_results ORDER BY id DESC LIMIT 3;")
            recent = cursor.fetchall()
            print("Recent records:")
            for record in recent:
                print(f"  ID {record[0]}: {record[1]} ({record[2]})")
        
        # Test 3: Test insert operation
        print("\n3. Testing insert operation...")
        test_filename = f"test_{int(datetime.now().timestamp())}.json"
        
        cursor.execute("""
            INSERT INTO processing_results (
                filename, original_filename, file_size, processing_status, 
                validation_status, processing_start_time, processed_file_path, 
                raw_json_data
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id;
        """, (
            test_filename, 'test.txt', 100, 'processing', 
            'pending_review', datetime.now(), 'test.json', '{"test": true}'
        ))
        
        test_id = cursor.fetchone()[0]
        print(f"✅ Insert successful! Created record with ID: {test_id}")
        
        # Test 4: Test select operation (matching the code's query)
        print("\n4. Testing select operation...")
        cursor.execute("""
            SELECT id, filename, original_filename, file_size, processing_status, 
                   validation_status, processing_start_time, processing_end_time, 
                   processing_duration, total_parts, parts_mapped, parts_not_found, 
                   parts_manual_review, mapping_success_rate, customer_matched, 
                   customer_match_confidence, error_details, error_types, 
                   manual_corrections_made, epicor_ready, epicor_ready_with_one_click, 
                   missing_info_count, processed_file_path, epicor_json_path, 
                   raw_json_data, notes, created_at, updated_at
            FROM processing_results WHERE id = %s
        """, (test_id,))
        
        row = cursor.fetchone()
        if row:
            print(f"✅ Select successful! Retrieved {len(row)} columns")
            print(f"Record: ID={row[0]}, filename={row[1]}, status={row[4]}")
            
            # Test JSON parsing
            try:
                error_types = json.loads(row[17] or '[]')
                print(f"✅ JSON parsing successful: {error_types}")
            except Exception as e:
                print(f"❌ JSON parsing failed: {e}")
        else:
            print("❌ Select failed - no data returned")
        
        # Test 5: Test update operation
        print("\n5. Testing update operation...")
        cursor.execute("""
            UPDATE processing_results 
            SET processing_status = %s, processing_end_time = %s, processing_duration = %s
            WHERE id = %s
        """, ('completed', datetime.now(), 1.5, test_id))
        
        if cursor.rowcount > 0:
            print("✅ Update successful!")
        else:
            print("❌ Update failed")
        
        # Clean up test record
        cursor.execute("DELETE FROM processing_results WHERE id = %s;", (test_id,))
        print("✅ Cleanup successful")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 All tests passed! Database is working correctly.")
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_database_comprehensive()
    if not success:
        print("\n=== Troubleshooting ===")
        print("1. Check your Supabase database credentials")
        print("2. Ensure the processing_results table exists")
        print("3. Verify network connectivity")

#!/usr/bin/env python3
"""
Simple test to check what's in the processing_results table
"""

import os
import psycopg2
from dotenv import load_dotenv

def test_table_contents():
    """Test what's actually in the processing_results table."""
    
    # Load environment variables
    load_dotenv('config.env')
    
    # Get environment variables
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'postgres')
    db_user = os.environ.get('DB_USER', 'postgres')
    db_password = os.environ.get('DB_PASSWORD')
    
    if not db_host or not db_password:
        print("❌ Missing database environment variables")
        return
    
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
        
        # Check what's in the table
        print("=== Processing Results Table Contents ===")
        cursor.execute("SELECT COUNT(*) FROM processing_results;")
        count = cursor.fetchone()[0]
        print(f"Total records: {count}")
        
        if count > 0:
            # Get the latest record
            cursor.execute("SELECT * FROM processing_results ORDER BY id DESC LIMIT 1;")
            latest = cursor.fetchone()
            print(f"\nLatest record has {len(latest)} columns:")
            for i, value in enumerate(latest):
                print(f"  Column {i}: {value}")
        
        # Check table structure
        print("\n=== Table Structure ===")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'processing_results'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        print(f"Table has {len(columns)} columns:")
        for i, (col_name, col_type) in enumerate(columns):
            print(f"  {i}: {col_name} ({col_type})")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_table_contents()

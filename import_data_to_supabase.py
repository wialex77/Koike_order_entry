#!/usr/bin/env python3
"""
Import parts.csv and customer_list.csv data into Supabase database
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
from datetime import datetime

# Database connection details
DB_CONFIG = {
    'host': 'db.lctdvwthxetczwyslibv.supabase.co',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': '%duym2Bs&+NyhQk'
}

def connect_to_db():
    """Connect to Supabase PostgreSQL database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected to Supabase database")
        return conn
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return None

def import_parts_data(conn):
    """Import parts data from CSV"""
    try:
        # Read CSV
        df = pd.read_csv('data/parts.csv')
        print(f"📊 Loaded {len(df)} parts from CSV")
        
        # Prepare data for insertion
        parts_data = []
        for _, row in df.iterrows():
            parts_data.append((
                row['part_number'],
                row['description'],
                datetime.now(),
                datetime.now()
            ))
        
        # Insert data
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO parts (part_number, description, created_at, updated_at)
            VALUES %s
            ON CONFLICT (part_number) DO UPDATE SET
                description = EXCLUDED.description,
                updated_at = EXCLUDED.updated_at
        """
        
        execute_values(cursor, insert_query, parts_data)
        conn.commit()
        
        print(f"✅ Imported {len(parts_data)} parts successfully")
        cursor.close()
        
    except Exception as e:
        print(f"❌ Error importing parts: {e}")
        conn.rollback()

def import_customers_data(conn):
    """Import customers data from CSV"""
    try:
        # Read CSV
        df = pd.read_csv('data/customer_list.csv')
        print(f"📊 Loaded {len(df)} customers from CSV")
        
        # Prepare data for insertion
        customers_data = []
        for _, row in df.iterrows():
            customers_data.append((
                int(row['customer_id']),
                row['company_name'],
                row.get('address', ''),
                row.get('city', ''),
                row.get('state_prov', ''),
                row.get('postal_code', ''),
                row.get('country', ''),
                datetime.now(),
                datetime.now()
            ))
        
        # Insert data
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO customers (customer_id, company_name, address, city, state_prov, postal_code, country, created_at, updated_at)
            VALUES %s
            ON CONFLICT (customer_id) DO UPDATE SET
                company_name = EXCLUDED.company_name,
                address = EXCLUDED.address,
                city = EXCLUDED.city,
                state_prov = EXCLUDED.state_prov,
                postal_code = EXCLUDED.postal_code,
                country = EXCLUDED.country,
                updated_at = EXCLUDED.updated_at
        """
        
        execute_values(cursor, insert_query, customers_data)
        conn.commit()
        
        print(f"✅ Imported {len(customers_data)} customers successfully")
        cursor.close()
        
    except Exception as e:
        print(f"❌ Error importing customers: {e}")
        conn.rollback()

def main():
    """Main import function"""
    print("🚀 Starting data import to Supabase...")
    
    # Connect to database
    conn = connect_to_db()
    if not conn:
        return
    
    try:
        # Import parts data
        print("\n📦 Importing parts data...")
        import_parts_data(conn)
        
        # Import customers data
        print("\n👥 Importing customers data...")
        import_customers_data(conn)
        
        print("\n🎉 Data import completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during import: {e}")
    finally:
        conn.close()
        print("🔌 Database connection closed")

if __name__ == "__main__":
    main()

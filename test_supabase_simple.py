#!/usr/bin/env python3
"""
Simple test to verify Supabase connection and data retrieval
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config.env')

# Set environment to production to use PostgreSQL
os.environ['FLASK_ENV'] = 'production'

# Now import our modules
from step3_databases_supabase import SupabaseDatabaseManager

def test_supabase_connection():
    """Test the Supabase connection and data retrieval."""
    print("🚀 Testing Supabase Database Connection")
    print("=" * 50)
    
    try:
        # Initialize the database manager
        print("Initializing Supabase database manager...")
        db_manager = SupabaseDatabaseManager()
        
        # Test parts data
        print(f"\n📦 Parts Database:")
        print(f"Total parts loaded: {len(db_manager.get_parts_dataframe())}")
        
        # Test a simple search
        search_results = db_manager.search_parts("FS00101229", limit=3)
        print(f"Search results for 'FS00101229': {len(search_results)}")
        for result in search_results:
            print(f"  - {result['internal_part_number']}: {result['description'][:50]}...")
        
        # Test customers data
        print(f"\n👥 Customers Database:")
        print(f"Total customers loaded: {len(db_manager.get_customers_dataframe())}")
        
        # Test customer search
        customer_results = db_manager.search_customers("DO NOT USE", limit=3)
        print(f"Search results for 'DO NOT USE': {len(customer_results)}")
        for result in customer_results:
            print(f"  - {result['account_number']}: {result['company_name']}")
        
        print("\n✅ All tests passed! Supabase connection is working.")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_supabase_connection()

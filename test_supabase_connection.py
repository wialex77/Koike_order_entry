#!/usr/bin/env python3
"""
Test script to verify PostgreSQL/Supabase database connection
"""

import os
import sys
from dotenv import load_dotenv

# Force PostgreSQL mode
os.environ['FLASK_ENV'] = 'production'

# Load environment variables
load_dotenv('config.env')

# Add current directory to path so we can import our modules
sys.path.append('.')

def test_supabase_connection():
    """Test the Supabase PostgreSQL connection"""
    print("🧪 Testing Supabase PostgreSQL connection...")
    
    try:
        # Import our modules
        from step5_metrics_db_postgres import MetricsDatabase
        from database_config import db_config
        
        print(f"📊 Database config - is_postgres: {db_config.is_postgres}")
        print(f"📊 Database config - engine: {db_config.engine}")
        
        # Test the MetricsDatabase initialization
        print("\n🔍 Testing MetricsDatabase initialization...")
        metrics_db = MetricsDatabase()
        
        print("\n✅ Database connection test completed successfully!")
        
        # Test a simple query to make sure we can actually query the database
        print("\n🔍 Testing actual database query...")
        test_sql = "SELECT COUNT(*) as count FROM processing_results"
        result = db_config.execute_raw_sql_single(test_sql)
        if result:
            print(f"✅ Query successful - processing_results table has {result[0]} records")
        else:
            print("⚠️ Query returned no results")
            
        return True
        
    except Exception as e:
        print(f"❌ Error during database test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Supabase PostgreSQL connection test...")
    success = test_supabase_connection()
    
    if success:
        print("\n🎉 All tests passed! The code should work on AWS.")
    else:
        print("\n💥 Tests failed! Check the errors above.")
        sys.exit(1)
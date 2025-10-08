#!/usr/bin/env python3
"""
Simplified test script for the comprehensive hybrid database manager
Tests each component individually with timeouts
"""

import os
import json
import signal
from datetime import datetime
from dotenv import load_dotenv

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

def load_env_file(env_file_path):
    """Load environment variables from a .env file."""
    if not os.path.exists(env_file_path):
        print(f"Environment file not found: {env_file_path}")
        return False
    
    with open(env_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
    return True

def test_database_connection():
    """Test basic database connection."""
    print("🔍 Testing basic database connection...")
    
    try:
        from database_config import db_config
        
        # Test basic connection
        test_sql = "SELECT 1 as test"
        result = db_config.execute_raw_sql_single(test_sql)
        print(f"✅ Basic connection test: {result}")
        
        # Test table existence
        tables_sql = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """
        tables_result = db_config.execute_raw_sql(tables_sql)
        tables = [row[0] for row in tables_result]
        print(f"✅ Available tables: {tables}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_parts_table():
    """Test parts table specifically."""
    print("\n📦 Testing parts table...")
    
    try:
        from database_config import db_config
        
        # Test parts table existence
        parts_check_sql = """
            SELECT COUNT(*) FROM parts
        """
        parts_count = db_config.execute_raw_sql_single(parts_check_sql)[0]
        print(f"✅ Parts table accessible: {parts_count} records")
        
        # Test a small sample
        sample_sql = "SELECT part_number, description FROM parts LIMIT 5"
        sample_results = db_config.execute_raw_sql(sample_sql)
        print(f"✅ Sample parts query successful: {len(sample_results)} records")
        
        for i, row in enumerate(sample_results, 1):
            print(f"   {i}. {row[0]}: {row[1][:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Parts table test failed: {e}")
        return False

def test_customers_table():
    """Test customers table specifically."""
    print("\n👥 Testing customers table...")
    
    try:
        from database_config import db_config
        
        # Test customers table existence
        customers_check_sql = """
            SELECT COUNT(*) FROM customers
        """
        customers_count = db_config.execute_raw_sql_single(customers_check_sql)[0]
        print(f"✅ Customers table accessible: {customers_count} records")
        
        # Test a small sample
        sample_sql = "SELECT customer_id, company_name FROM customers LIMIT 5"
        sample_results = db_config.execute_raw_sql(sample_sql)
        print(f"✅ Sample customers query successful: {len(sample_results)} records")
        
        for i, row in enumerate(sample_results, 1):
            print(f"   {i}. {row[0]}: {row[1]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Customers table test failed: {e}")
        return False

def test_processing_results_table():
    """Test processing results table specifically."""
    print("\n📋 Testing processing results table...")
    
    try:
        from database_config import db_config
        
        # Test processing results table existence
        pr_check_sql = """
            SELECT COUNT(*) FROM processing_results
        """
        pr_count = db_config.execute_raw_sql_single(pr_check_sql)[0]
        print(f"✅ Processing results table accessible: {pr_count} records")
        
        # Test a small sample
        sample_sql = "SELECT id, filename, processing_status FROM processing_results LIMIT 5"
        sample_results = db_config.execute_raw_sql(sample_sql)
        print(f"✅ Sample processing results query successful: {len(sample_results)} records")
        
        for i, row in enumerate(sample_results, 1):
            print(f"   {i}. ID {row[0]}: {row[1]} - {row[2]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Processing results table test failed: {e}")
        return False

def test_comprehensive_hybrid_database():
    """Test the comprehensive hybrid database manager with individual components."""
    
    # Load environment variables
    env_file = os.path.join(os.path.dirname(__file__), 'config.env')
    if not load_env_file(env_file):
        return
    
    print("🧪 Testing Comprehensive Hybrid Database Manager (Simplified)")
    print("="*80)
    
    # Test basic connection first
    if not test_database_connection():
        print("❌ Basic database connection failed, stopping tests")
        return
    
    # Test individual tables
    parts_ok = test_parts_table()
    customers_ok = test_customers_table()
    processing_ok = test_processing_results_table()
    
    # Summary
    print("\n📊 Test Summary:")
    print(f"   Database connection: ✅")
    print(f"   Parts table: {'✅' if parts_ok else '❌'}")
    print(f"   Customers table: {'✅' if customers_ok else '❌'}")
    print(f"   Processing results table: {'✅' if processing_ok else '❌'}")
    
    if parts_ok and customers_ok and processing_ok:
        print("\n✅ All individual table tests passed!")
        
        # Now try the comprehensive manager with a timeout
        print("\n🔍 Testing comprehensive manager initialization...")
        try:
            # Set a timeout for the comprehensive manager initialization
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)  # 30 second timeout
            
            from comprehensive_hybrid_database_manager import ComprehensiveHybridDatabaseManager
            db_manager = ComprehensiveHybridDatabaseManager()
            
            signal.alarm(0)  # Cancel timeout
            
            print("✅ Comprehensive manager initialized successfully!")
            
            # Test connection status
            status = db_manager.get_connection_status()
            print(f"   Connection method: {status['connection_method']}")
            print(f"   Parts loaded: {status['parts_loaded']}")
            print(f"   Customers loaded: {status['customers_loaded']}")
            
        except TimeoutError:
            print("❌ Comprehensive manager initialization timed out")
            print("   This suggests the customers table might be very large")
            print("   Consider adding LIMIT clauses to the queries")
        except Exception as e:
            print(f"❌ Comprehensive manager initialization failed: {e}")
    else:
        print("\n❌ Some table tests failed, skipping comprehensive manager test")

if __name__ == "__main__":
    test_comprehensive_hybrid_database()


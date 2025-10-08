#!/usr/bin/env python3
"""
Test script for the comprehensive hybrid database manager
Tests all three databases: parts, customers, and processing results
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv

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

def test_comprehensive_hybrid_database():
    """Test the comprehensive hybrid database manager."""
    
    # Load environment variables
    env_file = os.path.join(os.path.dirname(__file__), 'config.env')
    if not load_env_file(env_file):
        return
    
    print("🧪 Testing Comprehensive Hybrid Database Manager")
    print("="*80)
    
    try:
        # Import the comprehensive hybrid database manager
        from comprehensive_hybrid_database_manager import ComprehensiveHybridDatabaseManager
        
        # Initialize the manager
        print("🔍 Initializing comprehensive hybrid database manager...")
        db_manager = ComprehensiveHybridDatabaseManager()
        
        # Test connection status
        print("\n📊 Connection Status:")
        status = db_manager.get_connection_status()
        for key, value in status.items():
            print(f"   {key}: {value}")
        
        # Test parts database
        print("\n📦 Testing Parts Database:")
        parts_count = len(db_manager.get_parts_dataframe())
        print(f"   Total parts loaded: {parts_count}")
        
        if parts_count > 0:
            # Test parts search
            search_results = db_manager.search_parts("TEST", limit=3)
            print(f"   Search results for 'TEST': {len(search_results)}")
            for result in search_results:
                print(f"     - {result['internal_part_number']}: {result['description'][:50]}...")
        
        # Test customers database
        print("\n👥 Testing Customers Database:")
        customers_count = len(db_manager.get_customers_dataframe())
        print(f"   Total customers loaded: {customers_count}")
        
        if customers_count > 0:
            # Test customer search
            customer_results = db_manager.search_customers("DO NOT USE", limit=3)
            print(f"   Search results for 'DO NOT USE': {len(customer_results)}")
            for result in customer_results:
                print(f"     - {result['account_number']}: {result['company_name']}")
        
        # Test processing results
        print("\n📋 Testing Processing Results:")
        processing_results = db_manager.get_processing_results(limit=5)
        print(f"   Total processing results: {len(processing_results)}")
        
        if processing_results:
            print("   Recent results:")
            for i, result in enumerate(processing_results[:3], 1):
                print(f"     {i}. {result.filename} - {result.processing_status.value}")
        
        # Test dashboard metrics
        print("\n📈 Testing Dashboard Metrics:")
        metrics = db_manager.get_dashboard_metrics()
        print(f"   Total files: {metrics['total_files']}")
        print(f"   Successful files: {metrics['successful_files']}")
        print(f"   Success rate: {metrics['success_rate']:.1f}%")
        print(f"   Average processing time: {metrics['avg_processing_time']:.2f}s")
        
        print("\n✅ All tests completed successfully!")
        
        # Save test results
        test_results = {
            'test_timestamp': datetime.now().isoformat(),
            'connection_status': status,
            'parts_count': parts_count,
            'customers_count': customers_count,
            'processing_results_count': len(processing_results),
            'dashboard_metrics': metrics,
            'test_status': 'PASSED'
        }
        
        output_file = f"comprehensive_hybrid_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Test results saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_comprehensive_hybrid_database()

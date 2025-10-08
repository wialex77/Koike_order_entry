#!/usr/bin/env python3
"""
Test script for memory-optimized ComprehensiveHybridDatabaseManager.
This tests that the app starts quickly and uses minimal memory.
"""

import os
import sys
import time
import psutil
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_memory_usage():
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def test_memory_optimization():
    """Test the memory-optimized database manager."""
    print("🧪 Testing Memory-Optimized Database Manager")
    print("=" * 60)
    
    # Record initial memory
    initial_memory = get_memory_usage()
    print(f"📊 Initial memory usage: {initial_memory:.2f} MB")
    
    # Test 1: Fast initialization
    print("\n1. Testing fast initialization...")
    start_time = time.time()
    
    try:
        from comprehensive_hybrid_database_manager import ComprehensiveHybridDatabaseManager
        manager = ComprehensiveHybridDatabaseManager()
        
        init_time = time.time() - start_time
        init_memory = get_memory_usage()
        
        print(f"   ✅ Initialization completed in {init_time:.2f} seconds")
        print(f"   📊 Memory after init: {init_memory:.2f} MB")
        print(f"   📈 Memory increase: {init_memory - initial_memory:.2f} MB")
        
        if init_time < 5:
            print("   ✅ Fast initialization (under 5 seconds)")
        else:
            print("   ⚠️ Slow initialization (over 5 seconds)")
            
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        return False
    
    # Test 2: Search functionality without loading all data
    print("\n2. Testing search functionality...")
    search_start = time.time()
    
    try:
        # Test parts search
        parts_results = manager.search_parts("BOLT", limit=5)
        search_time = time.time() - search_start
        search_memory = get_memory_usage()
        
        print(f"   ✅ Parts search completed in {search_time:.2f} seconds")
        print(f"   📊 Memory after search: {search_memory:.2f} MB")
        print(f"   📈 Memory increase: {search_memory - init_memory:.2f} MB")
        print(f"   🔍 Found {len(parts_results)} parts")
        
        if parts_results:
            print(f"   📝 Sample result: {parts_results[0]}")
        
        # Test customer search
        customer_results = manager.search_customers("company", limit=3)
        print(f"   ✅ Customer search found {len(customer_results)} customers")
        
        if customer_results:
            print(f"   📝 Sample customer: {customer_results[0]['company_name']}")
            
    except Exception as e:
        print(f"   ❌ Search failed: {e}")
        return False
    
    # Test 3: Get specific items
    print("\n3. Testing specific item retrieval...")
    
    try:
        # Test getting a specific part
        part = manager.get_part_by_number("BOLT")
        if part:
            print(f"   ✅ Found part: {part['internal_part_number']} - {part['description']}")
        else:
            print("   ⚠️ No part found for 'BOLT'")
        
        # Test getting a specific customer
        customer = manager.get_customer_by_account("1")
        if customer:
            print(f"   ✅ Found customer: {customer['company_name']}")
        else:
            print("   ⚠️ No customer found for account '1'")
            
    except Exception as e:
        print(f"   ❌ Item retrieval failed: {e}")
        return False
    
    # Test 4: Check if data is loaded on demand
    print("\n4. Testing lazy loading...")
    
    try:
        # Check if DataFrames are still None
        parts_df = manager.parts_df
        customers_df = manager.customers_df
        
        if parts_df is None and customers_df is None:
            print("   ✅ DataFrames are still None (lazy loading working)")
        else:
            print("   ⚠️ DataFrames were loaded during search")
        
        # Now explicitly load data
        print("   📥 Explicitly loading data...")
        load_start = time.time()
        
        parts_df = manager.get_parts_dataframe()
        customers_df = manager.get_customers_dataframe()
        
        load_time = time.time() - load_start
        final_memory = get_memory_usage()
        
        print(f"   ✅ Data loaded in {load_time:.2f} seconds")
        print(f"   📊 Final memory usage: {final_memory:.2f} MB")
        print(f"   📈 Total memory increase: {final_memory - initial_memory:.2f} MB")
        print(f"   📊 Parts loaded: {len(parts_df)}")
        print(f"   📊 Customers loaded: {len(customers_df)}")
        
    except Exception as e:
        print(f"   ❌ Lazy loading test failed: {e}")
        return False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 MEMORY OPTIMIZATION SUMMARY")
    print("=" * 60)
    print(f"Initial memory:     {initial_memory:.2f} MB")
    print(f"After init:         {init_memory:.2f} MB")
    print(f"After search:       {search_memory:.2f} MB")
    print(f"After data load:    {final_memory:.2f} MB")
    print(f"Total increase:     {final_memory - initial_memory:.2f} MB")
    print(f"Init time:          {init_time:.2f} seconds")
    print(f"Search time:        {search_time:.2f} seconds")
    print(f"Data load time:     {load_time:.2f} seconds")
    
    if init_time < 5 and (final_memory - initial_memory) < 100:
        print("\n🎉 MEMORY OPTIMIZATION SUCCESSFUL!")
        print("✅ Fast startup and efficient memory usage")
        return True
    else:
        print("\n⚠️ Memory optimization needs improvement")
        return False

if __name__ == "__main__":
    success = test_memory_optimization()
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

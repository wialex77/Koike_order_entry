#!/usr/bin/env python3
"""
Test script for search functionality with memory-optimized database manager.
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_search_functionality():
    """Test search functionality with direct database queries."""
    print("🧪 Testing Search Functionality")
    print("=" * 50)
    
    try:
        from comprehensive_hybrid_database_manager import ComprehensiveHybridDatabaseManager
        manager = ComprehensiveHybridDatabaseManager()
        
        print(f"✅ Manager initialized with connection: {manager.connection_method}")
        
        # Test 1: Parts search
        print("\n1. Testing parts search...")
        search_terms = ["BOLT", "SCREW", "PART", "1", "A"]
        
        for term in search_terms:
            print(f"   Searching for: '{term}'")
            results = manager.search_parts(term, limit=3)
            print(f"   Found {len(results)} results")
            
            if results:
                print(f"   Sample: {results[0]['internal_part_number']} - {results[0]['description']}")
                break
            else:
                print("   No results found")
        
        # Test 2: Customer search
        print("\n2. Testing customer search...")
        customer_terms = ["company", "inc", "corp", "test"]
        
        for term in customer_terms:
            print(f"   Searching for: '{term}'")
            results = manager.search_customers(term, limit=3)
            print(f"   Found {len(results)} results")
            
            if results:
                print(f"   Sample: {results[0]['company_name']}")
                break
            else:
                print("   No results found")
        
        # Test 3: Specific part lookup
        print("\n3. Testing specific part lookup...")
        part = manager.get_part_by_number("BOLT")
        if part:
            print(f"   Found part: {part['internal_part_number']} - {part['description']}")
        else:
            print("   No part found for 'BOLT'")
        
        # Test 4: Specific customer lookup
        print("\n4. Testing specific customer lookup...")
        customer = manager.get_customer_by_account("1")
        if customer:
            print(f"   Found customer: {customer['company_name']}")
        else:
            print("   No customer found for account '1'")
        
        print("\n✅ Search functionality test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_search_functionality()
    if success:
        print("\n🎉 All search tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some search tests failed!")
        sys.exit(1)

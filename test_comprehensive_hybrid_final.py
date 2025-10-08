#!/usr/bin/env python3
"""
Test script for ComprehensiveHybridDatabaseManager with all methods.
This tests both PostgreSQL and REST API functionality.
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Optional

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import required modules
from comprehensive_hybrid_database_manager import ComprehensiveHybridDatabaseManager
from step5_metrics_db_postgres import ProcessingStatus, ValidationStatus, ErrorType

def test_comprehensive_hybrid_manager():
    """Test the ComprehensiveHybridDatabaseManager with all methods."""
    print("🧪 Testing ComprehensiveHybridDatabaseManager")
    print("=" * 80)
    
    try:
        # Initialize the manager
        print("1. Initializing ComprehensiveHybridDatabaseManager...")
        manager = ComprehensiveHybridDatabaseManager()
        
        # Test connection status
        print("\n2. Testing connection status...")
        status = manager.get_connection_status()
        print(f"   Connection Status: {status}")
        
        # Test create_processing_result
        print("\n3. Testing create_processing_result...")
        test_filename = f"test_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        test_original_filename = "test_original.pdf"
        test_file_size = 12345
        test_processing_status = ProcessingStatus.COMPLETED
        test_validation_status = ValidationStatus.CORRECT
        test_processing_start_time = datetime.utcnow()
        test_processed_file_path = f"processed/{test_filename}"
        test_raw_json_data = json.dumps({"test": "data", "timestamp": datetime.utcnow().isoformat()})
        test_notes = "Test record created by comprehensive test"
        
        result_id = manager.create_processing_result(
            filename=test_filename,
            original_filename=test_original_filename,
            file_size=test_file_size,
            processing_status=test_processing_status,
            validation_status=test_validation_status,
            processing_start_time=test_processing_start_time,
            processed_file_path=test_processed_file_path,
            raw_json_data=test_raw_json_data,
            notes=test_notes
        )
        
        if result_id > 0:
            print(f"   ✅ Created processing result with ID: {result_id}")
        else:
            print("   ❌ Failed to create processing result")
            return False
        
        # Test get_processing_result
        print("\n4. Testing get_processing_result...")
        retrieved_result = manager.get_processing_result(result_id)
        if retrieved_result:
            print(f"   ✅ Retrieved processing result: {retrieved_result.filename}")
            print(f"   Status: {retrieved_result.processing_status.value}")
            print(f"   Validation: {retrieved_result.validation_status.value}")
        else:
            print("   ❌ Failed to retrieve processing result")
            return False
        
        # Test update_processing_result
        print("\n5. Testing update_processing_result...")
        update_success = manager.update_processing_result(
            result_id,
            processing_duration=45.67,
            total_parts=25,
            parts_mapped=22,
            parts_not_found=2,
            parts_manual_review=1,
            mapping_success_rate=0.88,
            customer_matched=True,
            customer_match_confidence=0.95,
            error_types=[ErrorType.ACCOUNT_NUMBER, ErrorType.SHIPPING_ADDRESS],
            error_details="Test error details",
            manual_corrections_made=3,
            epicor_ready=True,
            epicor_ready_with_one_click=True,
            missing_info_count=0,
            epicor_json_path=f"epicor/{test_filename}",
            processing_end_time=datetime.utcnow()
        )
        
        if update_success:
            print("   ✅ Successfully updated processing result")
        else:
            print("   ❌ Failed to update processing result")
            return False
        
        # Test get_processing_result_by_filename
        print("\n6. Testing get_processing_result_by_filename...")
        result_by_filename = manager.get_processing_result_by_filename(test_filename)
        if result_by_filename:
            print(f"   ✅ Retrieved by filename: {result_by_filename.filename}")
            print(f"   Duration: {result_by_filename.processing_duration}")
            print(f"   Parts mapped: {result_by_filename.parts_mapped}")
        else:
            print("   ❌ Failed to retrieve by filename")
            return False
        
        # Test mark_as_correct
        print("\n7. Testing mark_as_correct...")
        mark_correct_success = manager.mark_as_correct(result_id)
        if mark_correct_success:
            print("   ✅ Successfully marked as correct")
        else:
            print("   ❌ Failed to mark as correct")
            return False
        
        # Test mark_as_contains_error
        print("\n8. Testing mark_as_contains_error...")
        mark_error_success = manager.mark_as_contains_error(
            result_id,
            error_types=[ErrorType.ACCOUNT_NUMBER],
            error_details="Test error marking"
        )
        if mark_error_success:
            print("   ✅ Successfully marked as contains error")
        else:
            print("   ❌ Failed to mark as contains error")
            return False
        
        # Test add_error_type
        print("\n9. Testing add_error_type...")
        add_error_success = manager.add_error_type(result_id, ErrorType.SHIPPING_ADDRESS)
        if add_error_success:
            print("   ✅ Successfully added error type")
        else:
            print("   ❌ Failed to add error type")
            return False
        
        # Test update_raw_json_data
        print("\n10. Testing update_raw_json_data...")
        new_raw_data = json.dumps({"updated": "data", "timestamp": datetime.utcnow().isoformat()})
        update_raw_success = manager.update_raw_json_data(result_id, new_raw_data)
        if update_raw_success:
            print("   ✅ Successfully updated raw JSON data")
        else:
            print("   ❌ Failed to update raw JSON data")
            return False
        
        # Test update_validation_status
        print("\n11. Testing update_validation_status...")
        update_validation_success = manager.update_validation_status(result_id, ValidationStatus.CORRECT.value)
        if update_validation_success:
            print("   ✅ Successfully updated validation status")
        else:
            print("   ❌ Failed to update validation status")
            return False
        
        # Test get_all_processing_results
        print("\n12. Testing get_all_processing_results...")
        all_results = manager.get_all_processing_results(limit=10, offset=0)
        if all_results:
            print(f"   ✅ Retrieved {len(all_results)} processing results")
            print(f"   Latest result: {all_results[0].filename}")
        else:
            print("   ❌ Failed to retrieve all processing results")
            return False
        
        # Test parts and customers functionality
        print("\n13. Testing parts and customers functionality...")
        parts_df = manager.get_parts_dataframe()
        customers_df = manager.get_customers_dataframe()
        print(f"   Parts loaded: {len(parts_df)}")
        print(f"   Customers loaded: {len(customers_df)}")
        
        if len(parts_df) > 0:
            print("   ✅ Parts database loaded successfully")
        else:
            print("   ❌ Parts database not loaded")
            return False
        
        if len(customers_df) > 0:
            print("   ✅ Customers database loaded successfully")
        else:
            print("   ❌ Customers database not loaded")
            return False
        
        # Test search functionality
        print("\n14. Testing search functionality...")
        
        # Try a few different search terms that are more likely to exist
        search_terms = ["1", "A", "PART", "BOLT", "SCREW"]
        search_success = False
        
        for term in search_terms:
            print(f"   Trying search term: '{term}'")
            search_results = manager.search_parts(term, limit=5)
            if search_results:
                print(f"   ✅ Parts search with '{term}' returned {len(search_results)} results")
                search_success = True
                break
            else:
                print(f"   ❌ Parts search with '{term}' returned 0 results")
        
        if not search_success:
            print("   ❌ All parts search attempts failed")
            return False
        
        # Test customer search
        customer_search_terms = ["test", "company", "inc", "corp", "ltd"]
        customer_search_success = False
        
        for term in customer_search_terms:
            print(f"   Trying customer search term: '{term}'")
            customer_search_results = manager.search_customers(term, limit=5)
            if customer_search_results:
                print(f"   ✅ Customer search with '{term}' returned {len(customer_search_results)} results")
                customer_search_success = True
                break
            else:
                print(f"   ❌ Customer search with '{term}' returned 0 results")
        
        if not customer_search_success:
            print("   ❌ All customer search attempts failed")
            return False
        
        # Test delete_processing_result
        print("\n15. Testing delete_processing_result...")
        delete_success = manager.delete_processing_result(result_id)
        if delete_success:
            print("   ✅ Successfully deleted test processing result")
        else:
            print("   ❌ Failed to delete processing result")
            return False
        
        # Verify deletion
        deleted_result = manager.get_processing_result(result_id)
        if deleted_result is None:
            print("   ✅ Confirmed deletion - result no longer exists")
        else:
            print("   ❌ Deletion verification failed - result still exists")
            return False
        
        print("\n" + "=" * 80)
        print("🎉 ALL TESTS PASSED! ComprehensiveHybridDatabaseManager is working correctly.")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_comprehensive_hybrid_manager()
    if success:
        print("\n✅ All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

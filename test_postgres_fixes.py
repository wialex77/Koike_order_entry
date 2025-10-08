#!/usr/bin/env python3
"""
Test the PostgreSQL fixes
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config.env')

# Set environment to production to use PostgreSQL
os.environ['FLASK_ENV'] = 'production'

# Now import our modules
from step5_metrics_db_postgres import MetricsDatabase, ProcessingStatus, ValidationStatus
from datetime import datetime

def test_postgres_fixes():
    """Test the PostgreSQL parameter binding fixes."""
    print("🚀 Testing PostgreSQL Parameter Binding Fixes")
    print("=" * 50)
    
    try:
        # Initialize the metrics database
        print("Initializing MetricsDatabase...")
        metrics_db = MetricsDatabase()
        
        # Test creating a processing result
        print("Testing create_processing_result...")
        result_id = metrics_db.create_processing_result(
            filename="test_file.json",
            original_filename="test.pdf",
            file_size=1024,
            processing_status=ProcessingStatus.PROCESSING,
            validation_status=ValidationStatus.PENDING_REVIEW,
            processing_start_time=datetime.now(),
            processed_file_path="processed/test_file.json",
            raw_json_data='{"test": "data"}'
        )
        
        print(f"✅ Created processing result with ID: {result_id}")
        
        # Test getting the processing result
        print("Testing get_processing_result...")
        result = metrics_db.get_processing_result(result_id)
        
        if result:
            print(f"✅ Retrieved processing result: {result.filename}")
        else:
            print("❌ Failed to retrieve processing result")
            return False
        
        # Test updating the processing result
        print("Testing update_processing_result...")
        success = metrics_db.update_processing_result(
            result_id,
            processing_status=ProcessingStatus.COMPLETED,
            processing_end_time=datetime.now()
        )
        
        if success:
            print("✅ Updated processing result successfully")
        else:
            print("❌ Failed to update processing result")
            return False
        
        # Test getting all processing results
        print("Testing get_processing_results...")
        all_results = metrics_db.get_processing_results(limit=5)
        print(f"✅ Retrieved {len(all_results)} processing results")
        
        # Test deleting the processing result
        print("Testing delete_processing_result...")
        delete_success = metrics_db.delete_processing_result(result_id)
        
        if delete_success:
            print("✅ Deleted processing result successfully")
        else:
            print("❌ Failed to delete processing result")
            return False
        
        print("\n🎉 All PostgreSQL tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_postgres_fixes()

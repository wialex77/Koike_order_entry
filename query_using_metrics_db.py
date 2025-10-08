#!/usr/bin/env python3
"""
Script to query processing_results table using the same method as step5_metrics_db_postgres.py
This script uses the existing MetricsDatabase class without modifying it.
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config.env')

# Set environment to production to use PostgreSQL
os.environ['FLASK_ENV'] = 'production'

# Import the existing classes
from step5_metrics_db_postgres import MetricsDatabase, ProcessingResult, ProcessingStatus, ValidationStatus, ErrorType

def format_processing_result(result: ProcessingResult) -> dict:
    """Format a ProcessingResult object for display."""
    return {
        'id': result.id,
        'filename': result.filename,
        'original_filename': result.original_filename,
        'file_size': result.file_size,
        'processing_status': result.processing_status.value,
        'validation_status': result.validation_status.value,
        'processing_start_time': result.processing_start_time.isoformat() if result.processing_start_time else None,
        'processing_end_time': result.processing_end_time.isoformat() if result.processing_end_time else None,
        'processing_duration': result.processing_duration,
        'total_parts': result.total_parts,
        'parts_mapped': result.parts_mapped,
        'parts_not_found': result.parts_not_found,
        'parts_manual_review': result.parts_manual_review,
        'mapping_success_rate': result.mapping_success_rate,
        'customer_matched': result.customer_matched,
        'customer_match_confidence': result.customer_match_confidence,
        'error_types': [e.value for e in result.error_types],
        'error_details': result.error_details,
        'manual_corrections_made': result.manual_corrections_made,
        'epicor_ready': result.epicor_ready,
        'epicor_ready_with_one_click': result.epicor_ready_with_one_click,
        'missing_info_count': result.missing_info_count,
        'processed_file_path': result.processed_file_path,
        'epicor_json_path': result.epicor_json_path,
        'notes': result.notes,
        'created_at': result.created_at.isoformat() if result.created_at else None,
        'updated_at': result.updated_at.isoformat() if result.updated_at else None
    }

def main():
    """Main function to query and display processing results using the same method as step5_metrics_db_postgres.py."""
    print("🔍 Querying processing_results table using MetricsDatabase class...")
    print("="*80)
    
    try:
        # Initialize the metrics database (same as step5_metrics_db_postgres.py)
        db = MetricsDatabase()
        
        print("✅ Database connection established using MetricsDatabase")
        
        # Get all processing results using the same method
        print("\n📊 Fetching processing results...")
        results = db.get_all_processing_results(limit=50)  # Limit to 50 for readability
        
        if not results:
            print("📭 No processing results found in the database.")
            return
        
        print(f"✅ Found {len(results)} processing results")
        
        # Display each result
        print("\n" + "="*80)
        print("PROCESSING RESULTS TABLE CONTENTS")
        print("="*80)
        
        for i, result in enumerate(results, 1):
            print(f"\n🔸 Result #{i} (ID: {result.id})")
            print(f"   Filename: {result.filename}")
            print(f"   Original Filename: {result.original_filename}")
            print(f"   File Size: {result.file_size:,} bytes")
            print(f"   Processing Status: {result.processing_status.value}")
            print(f"   Validation Status: {result.validation_status.value}")
            print(f"   Processing Duration: {result.processing_duration:.2f}s" if result.processing_duration else "   Processing Duration: N/A")
            print(f"   Total Parts: {result.total_parts}")
            print(f"   Parts Mapped: {result.parts_mapped}")
            print(f"   Parts Not Found: {result.parts_not_found}")
            print(f"   Parts Manual Review: {result.parts_manual_review}")
            print(f"   Mapping Success Rate: {result.mapping_success_rate:.1%}")
            print(f"   Customer Matched: {result.customer_matched}")
            print(f"   Customer Match Confidence: {result.customer_match_confidence:.1%}")
            print(f"   Epicor Ready: {result.epicor_ready}")
            print(f"   Epicor Ready One-Click: {result.epicor_ready_with_one_click}")
            print(f"   Missing Info Count: {result.missing_info_count}")
            print(f"   Error Types: {[e.value for e in result.error_types]}")
            print(f"   Error Details: {result.error_details[:100]}{'...' if len(result.error_details) > 100 else ''}")
            print(f"   Manual Corrections Made: {result.manual_corrections_made}")
            print(f"   Created: {result.created_at}")
            print(f"   Updated: {result.updated_at}")
            if result.notes:
                print(f"   Notes: {result.notes[:100]}{'...' if len(result.notes) > 100 else ''}")
        
        # Get dashboard metrics using the same method
        print("\n" + "="*80)
        print("DASHBOARD METRICS")
        print("="*80)
        
        metrics = db.get_dashboard_metrics()
        print(f"📈 Total Files Processed: {metrics['total_files']}")
        print(f"✅ Successful Files: {metrics['successful_files']}")
        print(f"📊 Success Rate: {metrics['success_rate']:.1f}%")
        print(f"⏱️  Average Processing Time: {metrics['avg_processing_time']:.2f} seconds")
        
        # Save results to JSON file
        print("\n" + "="*80)
        print("SAVING RESULTS TO JSON")
        print("="*80)
        
        formatted_results = [format_processing_result(result) for result in results]
        output_data = {
            'query_timestamp': datetime.now().isoformat(),
            'total_results': len(results),
            'dashboard_metrics': metrics,
            'processing_results': formatted_results
        }
        
        output_file = f"processing_results_metrics_db_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {output_file}")
        
        # Test individual methods from step5_metrics_db_postgres.py
        print("\n" + "="*80)
        print("TESTING INDIVIDUAL METHODS")
        print("="*80)
        
        # Test get_processing_results method
        recent_results = db.get_processing_results(limit=5)
        print(f"📋 Recent results (get_processing_results): {len(recent_results)}")
        
        # Test get_processing_result_by_filename if we have results
        if results:
            first_filename = results[0].filename
            result_by_filename = db.get_processing_result_by_filename(first_filename)
            if result_by_filename:
                print(f"🔍 Found result by filename '{first_filename}': ID {result_by_filename.id}")
            else:
                print(f"❌ No result found for filename '{first_filename}'")
        
        print("\n✅ All queries completed successfully using MetricsDatabase methods!")
        
    except Exception as e:
        print(f"❌ Error querying database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

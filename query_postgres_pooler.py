#!/usr/bin/env python3
"""
Script to query processing_results table using the working PostgreSQL Transaction Pooler connection
"""

import os
import json
import socket
from datetime import datetime
from dotenv import load_dotenv

def force_ipv4():
    """Force IPv4 connections by monkey-patching socket."""
    original_getaddrinfo = socket.getaddrinfo
    
    def getaddrinfo_ipv4(*args, **kwargs):
        responses = original_getaddrinfo(*args, **kwargs)
        # Filter to only IPv4 addresses
        return [response for response in responses if response[0] == socket.AF_INET]
    
    socket.getaddrinfo = getaddrinfo_ipv4

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

def query_processing_results_postgres():
    """Query processing_results using the working PostgreSQL Transaction Pooler connection."""
    
    # Force IPv4 connections
    force_ipv4()
    
    # Load environment variables
    env_file = os.path.join(os.path.dirname(__file__), 'config.env')
    if not load_env_file(env_file):
        return
    
    # Set environment to production to use PostgreSQL
    os.environ['FLASK_ENV'] = 'production'
    
    print("Querying processing_results using PostgreSQL Transaction Pooler...")
    print("="*80)
    
    try:
        # Import the database config
        from database_config import db_config
        
        print(f"✅ Connected to: {db_config.engine}")
        
        # Get all processing results
        sql = '''
            SELECT * FROM processing_results 
            ORDER BY created_at DESC 
            LIMIT 50
        '''
        
        rows = db_config.execute_raw_sql(sql)
        
        if not rows:
            print("📭 No processing results found.")
            return
        
        print(f"✅ Found {len(rows)} processing results")
        
        # Display each result
        print("\n" + "="*80)
        print("PROCESSING RESULTS TABLE CONTENTS")
        print("="*80)
        
        for i, row in enumerate(rows, 1):
            print(f"\n🔸 Result #{i} (ID: {row[0]})")
            print(f"   Filename: {row[1]}")
            print(f"   Original Filename: {row[2]}")
            print(f"   File Size: {row[3]:,} bytes")
            print(f"   Processing Status: {row[4]}")
            print(f"   Validation Status: {row[5]}")
            print(f"   Processing Start Time: {row[6]}")
            print(f"   Processing End Time: {row[7]}")
            print(f"   Processing Duration: {row[8]}s" if row[8] else "   Processing Duration: N/A")
            print(f"   Total Parts: {row[9]}")
            print(f"   Parts Mapped: {row[10]}")
            print(f"   Parts Not Found: {row[11]}")
            print(f"   Parts Manual Review: {row[12]}")
            print(f"   Mapping Success Rate: {row[13]:.1%}")
            print(f"   Customer Matched: {row[14]}")
            print(f"   Customer Match Confidence: {row[15]:.1%}")
            print(f"   Error Types: {row[16]}")
            print(f"   Error Details: {row[17]}")
            print(f"   Manual Corrections Made: {row[18]}")
            print(f"   Epicor Ready: {row[19]}")
            print(f"   Epicor Ready One-Click: {row[20]}")
            print(f"   Missing Info Count: {row[21]}")
            print(f"   Processed File Path: {row[22]}")
            print(f"   Epicor JSON Path: {row[23]}")
            print(f"   Raw JSON Data: {row[24][:100]}{'...' if len(str(row[24])) > 100 else ''}")
            print(f"   Notes: {row[25]}")
            print(f"   Created: {row[26]}")
            print(f"   Updated: {row[27]}")
        
        # Get basic statistics
        print("\n" + "="*80)
        print("BASIC STATISTICS")
        print("="*80)
        
        # Count by processing status
        status_sql = """
            SELECT processing_status, COUNT(*) as count
            FROM processing_results
            GROUP BY processing_status
            ORDER BY count DESC
        """
        status_results = db_config.execute_raw_sql(status_sql)
        status_counts = {row[0]: row[1] for row in status_results}
        
        print("📊 Processing Status Distribution:")
        for status, count in status_counts.items():
            print(f"   {status}: {count}")
        
        # Count by validation status
        validation_sql = """
            SELECT validation_status, COUNT(*) as count
            FROM processing_results
            GROUP BY validation_status
            ORDER BY count DESC
        """
        validation_results = db_config.execute_raw_sql(validation_sql)
        validation_counts = {row[0]: row[1] for row in validation_results}
        
        print("\n📊 Validation Status Distribution:")
        for status, count in validation_counts.items():
            print(f"   {status}: {count}")
        
        # Average processing duration
        duration_sql = """
            SELECT AVG(processing_duration) as avg_duration
            FROM processing_results
            WHERE processing_duration IS NOT NULL
        """
        duration_result = db_config.execute_raw_sql_single(duration_sql)
        avg_duration = duration_result[0] if duration_result else None
        
        if avg_duration:
            print(f"\n⏱️  Average Processing Duration: {avg_duration:.2f} seconds")
        
        # Save results to JSON file
        print("\n" + "="*80)
        print("SAVING RESULTS TO JSON")
        print("="*80)
        
        # Convert rows to list of dictionaries
        records = []
        for row in rows:
            record = {
                'id': row[0],
                'filename': row[1],
                'original_filename': row[2],
                'file_size': row[3],
                'processing_status': row[4],
                'validation_status': row[5],
                'processing_start_time': row[6].isoformat() if row[6] else None,
                'processing_end_time': row[7].isoformat() if row[7] else None,
                'processing_duration': row[8],
                'total_parts': row[9],
                'parts_mapped': row[10],
                'parts_not_found': row[11],
                'parts_manual_review': row[12],
                'mapping_success_rate': row[13],
                'customer_matched': row[14],
                'customer_match_confidence': row[15],
                'error_types': row[16],
                'error_details': row[17],
                'manual_corrections_made': row[18],
                'epicor_ready': row[19],
                'epicor_ready_with_one_click': row[20],
                'missing_info_count': row[21],
                'processed_file_path': row[22],
                'epicor_json_path': row[23],
                'raw_json_data': row[24],
                'notes': row[25],
                'created_at': row[26].isoformat() if row[26] else None,
                'updated_at': row[27].isoformat() if row[27] else None
            }
            records.append(record)
        
        output_data = {
            'query_timestamp': datetime.now().isoformat(),
            'total_records': len(records),
            'connection_method': 'PostgreSQL Transaction Pooler (IPv4)',
            'statistics': {
                'processing_status_distribution': status_counts,
                'validation_status_distribution': validation_counts,
                'average_processing_duration': float(avg_duration) if avg_duration else None
            },
            'records': records
        }
        
        output_file = f"processing_results_postgres_pooler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {output_file}")
        
        print("\n✅ All queries completed successfully using PostgreSQL Transaction Pooler!")
        
    except Exception as e:
        print(f"❌ Error querying database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    query_processing_results_postgres()

"""
Hybrid Database Connection Manager
Uses PostgreSQL Transaction Pooler as primary method with REST API fallback.
"""

import os
import json
import socket
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from dotenv import load_dotenv

# Import existing classes
from step5_metrics_db_postgres import ProcessingResult, ProcessingStatus, ValidationStatus, ErrorType

class HybridDatabaseManager:
    """Database manager that uses PostgreSQL Transaction Pooler with REST API fallback."""
    
    def __init__(self):
        """Initialize the hybrid database manager."""
        self.use_postgres = True
        self.use_rest_api = False
        self.supabase_url = None
        self.api_key = None
        
        # Load environment variables
        self._load_environment()
        
        # Try PostgreSQL first, fallback to REST API
        self._initialize_connection()
    
    def _load_environment(self):
        """Load environment variables from config.env."""
        env_file = os.path.join(os.path.dirname(__file__), 'config.env')
        if os.path.exists(env_file):
            load_dotenv(env_file)
        
        # Extract Supabase project info
        db_host = os.environ.get('DB_HOST', 'aws-1-us-east-2.pooler.supabase.co')
        if 'pooler.supabase.com' in db_host:
            project_ref = db_host.split('.')[0].replace('aws-1-us-east-2', 'lctdvwthxetczwyslibv')
        else:
            project_ref = db_host.replace('db.', '').replace('.supabase.co', '')
        
        self.supabase_url = f"https://{project_ref}.supabase.co"
        self.api_key = os.environ.get('SUPABASE_ANON_KEY')
    
    def _force_ipv4(self):
        """Force IPv4 connections by monkey-patching socket."""
        original_getaddrinfo = socket.getaddrinfo
        
        def getaddrinfo_ipv4(*args, **kwargs):
            responses = original_getaddrinfo(*args, **kwargs)
            return [response for response in responses if response[0] == socket.AF_INET]
        
        socket.getaddrinfo = getaddrinfo_ipv4
    
    def _initialize_connection(self):
        """Initialize connection, trying PostgreSQL first, then REST API."""
        print("🔍 Initializing hybrid database connection...")
        
        # Try PostgreSQL Transaction Pooler first
        try:
            self._force_ipv4()
            os.environ['FLASK_ENV'] = 'production'
            
            from database_config import db_config
            
            # Test PostgreSQL connection
            test_sql = "SELECT 1 as test"
            result = db_config.execute_raw_sql_single(test_sql)
            
            if result:
                self.use_postgres = True
                self.use_rest_api = False
                print("✅ Using PostgreSQL Transaction Pooler (primary)")
                return
                
        except Exception as e:
            print(f"⚠️ PostgreSQL connection failed: {e}")
        
        # Fallback to REST API
        try:
            if not self.api_key:
                raise Exception("No Supabase API key found")
            
            # Test REST API connection
            headers = {
                'apikey': self.api_key,
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(self.supabase_url, headers=headers, timeout=10)
            
            if response.status_code in [200, 404]:  # 404 is expected for root endpoint
                self.use_postgres = False
                self.use_rest_api = True
                print("✅ Using Supabase REST API (fallback)")
                return
                
        except Exception as e:
            print(f"❌ REST API connection failed: {e}")
        
        # If both fail
        self.use_postgres = False
        self.use_rest_api = False
        print("❌ Both PostgreSQL and REST API connections failed")
    
    def get_processing_results(self, limit: int = 100) -> List[ProcessingResult]:
        """Get recent processing results."""
        if self.use_postgres:
            return self._get_processing_results_postgres(limit)
        elif self.use_rest_api:
            return self._get_processing_results_rest_api(limit)
        else:
            print("❌ No database connection available")
            return []
    
    def _get_processing_results_postgres(self, limit: int) -> List[ProcessingResult]:
        """Get processing results using PostgreSQL."""
        try:
            from database_config import db_config
            
            sql = '''
                SELECT * FROM processing_results 
                ORDER BY created_at DESC 
                LIMIT %s
            '''
            
            rows = db_config.execute_raw_sql(sql, (limit,))
            
            results = []
            for row in rows:
                # Convert row to ProcessingResult object
                error_types = [ErrorType(e) for e in json.loads(row[17] or '[]')]
                
                result = ProcessingResult(
                    id=row[0],
                    filename=row[1],
                    original_filename=row[2],
                    file_size=row[3],
                    processing_status=ProcessingStatus(row[4]),
                    validation_status=ValidationStatus(row[5]),
                    processing_start_time=row[6],
                    processing_end_time=row[7],
                    processing_duration=row[8],
                    total_parts=row[9] or 0,
                    parts_mapped=row[10] or 0,
                    parts_not_found=row[11] or 0,
                    parts_manual_review=row[12] or 0,
                    mapping_success_rate=row[13] or 0.0,
                    customer_matched=row[14] or False,
                    customer_match_confidence=row[15] or 0.0,
                    error_types=error_types,
                    error_details=row[16] or '',
                    manual_corrections_made=row[18] or 0,
                    epicor_ready=row[19] or False,
                    epicor_ready_with_one_click=row[20] or False,
                    missing_info_count=row[21] or 0,
                    processed_file_path=row[22] or '',
                    epicor_json_path=row[23],
                    raw_json_data=row[24] or '',
                    notes=row[25] or '',
                    created_at=row[26],
                    updated_at=row[27]
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"❌ Error getting processing results from PostgreSQL: {e}")
            return []
    
    def _get_processing_results_rest_api(self, limit: int) -> List[ProcessingResult]:
        """Get processing results using REST API."""
        try:
            headers = {
                'apikey': self.api_key,
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            query_url = f"{self.supabase_url}/rest/v1/processing_results"
            params = {
                'select': '*',
                'limit': str(limit),
                'order': 'created_at.desc'
            }
            
            response = requests.get(query_url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                results = []
                for record in data:
                    # Convert REST API record to ProcessingResult object
                    error_types = [ErrorType(e) for e in json.loads(record.get('error_types', '[]'))]
                    
                    result = ProcessingResult(
                        id=record.get('id'),
                        filename=record.get('filename', ''),
                        original_filename=record.get('original_filename', ''),
                        file_size=record.get('file_size', 0),
                        processing_status=ProcessingStatus(record.get('processing_status', 'pending')),
                        validation_status=ValidationStatus(record.get('validation_status', 'pending_review')),
                        processing_start_time=datetime.fromisoformat(record.get('processing_start_time', datetime.now().isoformat()).replace('Z', '+00:00')) if record.get('processing_start_time') else None,
                        processing_end_time=datetime.fromisoformat(record.get('processing_end_time', '').replace('Z', '+00:00')) if record.get('processing_end_time') else None,
                        processing_duration=record.get('processing_duration'),
                        total_parts=record.get('total_parts', 0),
                        parts_mapped=record.get('parts_mapped', 0),
                        parts_not_found=record.get('parts_not_found', 0),
                        parts_manual_review=record.get('parts_manual_review', 0),
                        mapping_success_rate=record.get('mapping_success_rate', 0.0),
                        customer_matched=record.get('customer_matched', False),
                        customer_match_confidence=record.get('customer_match_confidence', 0.0),
                        error_types=error_types,
                        error_details=record.get('error_details', ''),
                        manual_corrections_made=record.get('manual_corrections_made', 0),
                        epicor_ready=record.get('epicor_ready', False),
                        epicor_ready_with_one_click=record.get('epicor_ready_with_one_click', False),
                        missing_info_count=record.get('missing_info_count', 0),
                        processed_file_path=record.get('processed_file_path', ''),
                        epicor_json_path=record.get('epicor_json_path'),
                        raw_json_data=record.get('raw_json_data', ''),
                        notes=record.get('notes', ''),
                        created_at=datetime.fromisoformat(record.get('created_at', datetime.now().isoformat()).replace('Z', '+00:00')) if record.get('created_at') else None,
                        updated_at=datetime.fromisoformat(record.get('updated_at', datetime.now().isoformat()).replace('Z', '+00:00')) if record.get('updated_at') else None
                    )
                    results.append(result)
                
                return results
            else:
                print(f"❌ REST API query failed with status: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting processing results from REST API: {e}")
            return []
    
    def save_processing_result(self, result: ProcessingResult) -> int:
        """Save a processing result."""
        if self.use_postgres:
            return self._save_processing_result_postgres(result)
        elif self.use_rest_api:
            return self._save_processing_result_rest_api(result)
        else:
            print("❌ No database connection available")
            return None
    
    def _save_processing_result_postgres(self, result: ProcessingResult) -> int:
        """Save processing result using PostgreSQL."""
        try:
            from database_config import db_config
            
            # Convert enum lists to JSON strings
            error_types_json = json.dumps([e.value for e in result.error_types])
            
            # Prepare data for insertion
            data = {
                'filename': result.filename,
                'original_filename': result.original_filename,
                'file_size': result.file_size,
                'processing_status': result.processing_status.value,
                'validation_status': result.validation_status.value,
                'processing_start_time': result.processing_start_time,
                'processing_end_time': result.processing_end_time,
                'processing_duration': result.processing_duration,
                'total_parts': result.total_parts,
                'parts_mapped': result.parts_mapped,
                'parts_not_found': result.parts_not_found,
                'parts_manual_review': result.parts_manual_review,
                'mapping_success_rate': result.mapping_success_rate,
                'customer_matched': result.customer_matched,
                'customer_match_confidence': result.customer_match_confidence,
                'error_types': error_types_json,
                'error_details': result.error_details,
                'manual_corrections_made': result.manual_corrections_made,
                'epicor_ready': result.epicor_ready,
                'epicor_ready_with_one_click': result.epicor_ready_with_one_click,
                'missing_info_count': result.missing_info_count,
                'processed_file_path': result.processed_file_path,
                'epicor_json_path': result.epicor_json_path,
                'raw_json_data': result.raw_json_data,
                'notes': result.notes,
                'created_at': result.created_at,
                'updated_at': result.updated_at
            }
            
            # Build INSERT query
            if result.id is None:
                # New record
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['%s' for _ in data.keys()])
                
                sql = f'''
                    INSERT INTO processing_results ({columns})
                    VALUES ({placeholders})
                    RETURNING id
                '''
                values = [data[key] for key in data.keys()]
                result_id = db_config.execute_raw_sql_single(sql, values)[0]
            else:
                # Update existing record
                set_clause = ', '.join([f'{key} = %s' for key in data.keys() if key != 'id'])
                sql = f'''
                    UPDATE processing_results 
                    SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                '''
                data['id'] = result.id
                values = [data[key] for key in data.keys()]
                db_config.execute_raw_sql(sql, values)
                result_id = result.id
            
            return result_id
            
        except Exception as e:
            print(f"❌ Error saving processing result to PostgreSQL: {e}")
            return None
    
    def _save_processing_result_rest_api(self, result: ProcessingResult) -> int:
        """Save processing result using REST API."""
        try:
            headers = {
                'apikey': self.api_key,
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Prepare data for REST API
            data = {
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
                'error_types': json.dumps([e.value for e in result.error_types]),
                'error_details': result.error_details,
                'manual_corrections_made': result.manual_corrections_made,
                'epicor_ready': result.epicor_ready,
                'epicor_ready_with_one_click': result.epicor_ready_with_one_click,
                'missing_info_count': result.missing_info_count,
                'processed_file_path': result.processed_file_path,
                'epicor_json_path': result.epicor_json_path,
                'raw_json_data': result.raw_json_data,
                'notes': result.notes,
                'created_at': result.created_at.isoformat() if result.created_at else None,
                'updated_at': result.updated_at.isoformat() if result.updated_at else None
            }
            
            # Insert or update
            if result.id is None:
                # New record
                insert_url = f"{self.supabase_url}/rest/v1/processing_results"
                response = requests.post(insert_url, headers=headers, json=data, timeout=30)
                
                if response.status_code == 201:
                    inserted_data = response.json()
                    return inserted_data[0]['id'] if inserted_data else None
                else:
                    print(f"❌ REST API insert failed with status: {response.status_code}")
                    return None
            else:
                # Update existing record
                update_url = f"{self.supabase_url}/rest/v1/processing_results"
                params = {'id': f'eq.{result.id}'}
                response = requests.patch(update_url, headers=headers, json=data, params=params, timeout=30)
                
                if response.status_code == 200:
                    return result.id
                else:
                    print(f"❌ REST API update failed with status: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error saving processing result to REST API: {e}")
            return None
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get dashboard metrics."""
        if self.use_postgres:
            return self._get_dashboard_metrics_postgres()
        elif self.use_rest_api:
            return self._get_dashboard_metrics_rest_api()
        else:
            return {
                'total_files': 0,
                'successful_files': 0,
                'success_rate': 0,
                'avg_processing_time': 0
            }
    
    def _get_dashboard_metrics_postgres(self) -> Dict[str, Any]:
        """Get dashboard metrics using PostgreSQL."""
        try:
            from database_config import db_config
            
            # Get total files processed
            total_files_sql = "SELECT COUNT(*) FROM processing_results"
            total_files = db_config.execute_raw_sql_single(total_files_sql)[0] or 0
            
            # Get success rate
            success_sql = "SELECT COUNT(*) FROM processing_results WHERE processing_status = 'completed'"
            successful_files = db_config.execute_raw_sql_single(success_sql)[0] or 0
            success_rate = (successful_files / total_files * 100) if total_files > 0 else 0
            
            # Get average processing time
            avg_time_sql = '''
                SELECT AVG(processing_duration) 
                FROM processing_results 
                WHERE processing_duration IS NOT NULL
            '''
            avg_processing_time = db_config.execute_raw_sql_single(avg_time_sql)[0] or 0
            
            return {
                'total_files': total_files,
                'successful_files': successful_files,
                'success_rate': round(success_rate, 2),
                'avg_processing_time': round(avg_processing_time, 2) if avg_processing_time else 0
            }
            
        except Exception as e:
            print(f"❌ Error getting dashboard metrics from PostgreSQL: {e}")
            return {
                'total_files': 0,
                'successful_files': 0,
                'success_rate': 0,
                'avg_processing_time': 0
            }
    
    def _get_dashboard_metrics_rest_api(self) -> Dict[str, Any]:
        """Get dashboard metrics using REST API."""
        try:
            headers = {
                'apikey': self.api_key,
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Get all records to calculate metrics
            query_url = f"{self.supabase_url}/rest/v1/processing_results"
            params = {'select': 'processing_status,processing_duration'}
            
            response = requests.get(query_url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                total_files = len(data)
                successful_files = len([r for r in data if r.get('processing_status') == 'completed'])
                success_rate = (successful_files / total_files * 100) if total_files > 0 else 0
                
                durations = [r.get('processing_duration') for r in data if r.get('processing_duration') is not None]
                avg_processing_time = sum(durations) / len(durations) if durations else 0
                
                return {
                    'total_files': total_files,
                    'successful_files': successful_files,
                    'success_rate': round(success_rate, 2),
                    'avg_processing_time': round(avg_processing_time, 2)
                }
            else:
                print(f"❌ REST API metrics query failed with status: {response.status_code}")
                return {
                    'total_files': 0,
                    'successful_files': 0,
                    'success_rate': 0,
                    'avg_processing_time': 0
                }
                
        except Exception as e:
            print(f"❌ Error getting dashboard metrics from REST API: {e}")
            return {
                'total_files': 0,
                'successful_files': 0,
                'success_rate': 0,
                'avg_processing_time': 0
            }
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status."""
        return {
            'using_postgres': self.use_postgres,
            'using_rest_api': self.use_rest_api,
            'connection_method': 'PostgreSQL Transaction Pooler' if self.use_postgres else 'REST API' if self.use_rest_api else 'None',
            'supabase_url': self.supabase_url,
            'has_api_key': bool(self.api_key)
        }

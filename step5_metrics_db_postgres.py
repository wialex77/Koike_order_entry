"""
Step 5: PostgreSQL-Compatible Metrics Database Module
Tracks file processing results, accuracy rates, error types, and approval/decline ratios.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from database_config import db_config

class ProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class ValidationStatus(Enum):
    CORRECT = "correct"
    CONTAINS_ERROR = "contains_error"
    PENDING_REVIEW = "pending_review"

class ErrorType(Enum):
    ACCOUNT_NUMBER = "account_number"
    BILLING_ADDRESS = "billing_address"
    SHIPPING_ADDRESS = "shipping_address"
    SHIPPING_METHOD = "shipping_method"
    PART_NUMBER = "part_number"
    SHIPPING_INFO = "shipping_info"
    PART_NUMBERS = "part_numbers"
    COMPANY_INFO = "company_info"
    OTHER = "other"

@dataclass
class ProcessingResult:
    """Represents a file processing result with metrics."""
    id: Optional[int]
    filename: str
    original_filename: str
    file_size: int
    processing_status: ProcessingStatus
    validation_status: ValidationStatus
    processing_start_time: datetime
    processing_end_time: Optional[datetime]
    processing_duration: Optional[float]
    
    # Metrics
    total_parts: int
    parts_mapped: int
    parts_not_found: int
    parts_manual_review: int
    mapping_success_rate: float
    customer_matched: bool
    customer_match_confidence: float
    
    # Error tracking
    error_types: List[ErrorType]
    error_details: str
    manual_corrections_made: int
    
    # Epicor readiness
    epicor_ready: bool
    epicor_ready_with_one_click: bool
    missing_info_count: int
    
    # File paths
    processed_file_path: str
    epicor_json_path: Optional[str]
    
    # Raw JSON data
    raw_json_data: str
    
    # Notes
    notes: str
    
    # Metadata
    created_at: datetime
    updated_at: datetime

class MetricsDatabase:
    """Database manager for tracking processing metrics and results."""
    
    def __init__(self):
        self.db_config = db_config
        self.init_database()
    
    def init_database(self):
        """Initialize the metrics database with required tables."""
        try:
            # Create processing_results table
            create_table_sql = '''
                CREATE TABLE IF NOT EXISTS processing_results (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    original_filename VARCHAR(255) NOT NULL,
                    file_size INTEGER NOT NULL,
                    processing_status VARCHAR(50) NOT NULL,
                    validation_status VARCHAR(50) NOT NULL,
                    processing_start_time TIMESTAMP NOT NULL,
                    processing_end_time TIMESTAMP,
                    processing_duration FLOAT,
                    total_parts INTEGER DEFAULT 0,
                    parts_mapped INTEGER DEFAULT 0,
                    parts_not_found INTEGER DEFAULT 0,
                    parts_manual_review INTEGER DEFAULT 0,
                    mapping_success_rate FLOAT DEFAULT 0.0,
                    customer_matched BOOLEAN DEFAULT FALSE,
                    customer_match_confidence FLOAT DEFAULT 0.0,
                    error_types TEXT,
                    error_details TEXT,
                    manual_corrections_made INTEGER DEFAULT 0,
                    epicor_ready BOOLEAN DEFAULT FALSE,
                    epicor_ready_with_one_click BOOLEAN DEFAULT FALSE,
                    missing_info_count INTEGER DEFAULT 0,
                    processed_file_path TEXT,
                    epicor_json_path TEXT,
                    raw_json_data TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''' if self.db_config.is_postgres else '''
                CREATE TABLE IF NOT EXISTS processing_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    processing_status TEXT NOT NULL,
                    validation_status TEXT NOT NULL,
                    processing_start_time TIMESTAMP NOT NULL,
                    processing_end_time TIMESTAMP,
                    processing_duration REAL,
                    total_parts INTEGER DEFAULT 0,
                    parts_mapped INTEGER DEFAULT 0,
                    parts_not_found INTEGER DEFAULT 0,
                    parts_manual_review INTEGER DEFAULT 0,
                    mapping_success_rate REAL DEFAULT 0.0,
                    customer_matched BOOLEAN DEFAULT 0,
                    customer_match_confidence REAL DEFAULT 0.0,
                    error_types TEXT,
                    error_details TEXT,
                    manual_corrections_made INTEGER DEFAULT 0,
                    epicor_ready BOOLEAN DEFAULT 0,
                    epicor_ready_with_one_click BOOLEAN DEFAULT 0,
                    missing_info_count INTEGER DEFAULT 0,
                    processed_file_path TEXT,
                    epicor_json_path TEXT,
                    raw_json_data TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''
            
            self.db_config.execute_raw_sql(create_table_sql)
            print("✅ Database table 'processing_results' initialized")
            
        except Exception as e:
            print(f"❌ Error initializing database: {e}")
    
    def save_processing_result(self, result: ProcessingResult) -> int:
        """Save a processing result to the database."""
        try:
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
                placeholders = ', '.join([f':{key}' for key in data.keys()])
                
                if self.db_config.is_postgres:
                    sql = f'''
                        INSERT INTO processing_results ({columns})
                        VALUES ({placeholders})
                        RETURNING id
                    '''
                    result_id = self.db_config.execute_raw_sql_single(sql, data)[0]
                else:
                    sql = f'''
                        INSERT INTO processing_results ({columns})
                        VALUES ({placeholders})
                    '''
                    cursor = self.db_config.get_connection().cursor()
                    cursor.execute(sql, data)
                    result_id = cursor.lastrowid
                    cursor.connection.commit()
                    cursor.connection.close()
            else:
                # Update existing record
                set_clause = ', '.join([f'{key} = :{key}' for key in data.keys() if key != 'id'])
                sql = f'''
                    UPDATE processing_results 
                    SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                '''
                data['id'] = result.id
                self.db_config.execute_raw_sql(sql, data)
                result_id = result.id
            
            return result_id
            
        except Exception as e:
            print(f"❌ Error saving processing result: {e}")
            return None
    
    def get_processing_results(self, limit: int = 100) -> List[ProcessingResult]:
        """Get recent processing results."""
        try:
            sql = '''
                SELECT * FROM processing_results 
                ORDER BY created_at DESC 
                LIMIT :limit
            '''
            
            rows = self.db_config.execute_raw_sql(sql, {'limit': limit})
            
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
            print(f"❌ Error getting processing results: {e}")
            return []

    def get_all_processing_results(self, limit: int = 100, offset: int = 0) -> List[ProcessingResult]:
        """Get all processing results with pagination."""
        try:
            sql = '''
                SELECT * FROM processing_results 
                ORDER BY created_at DESC 
                LIMIT :limit OFFSET :offset
            '''
            
            rows = self.db_config.execute_raw_sql(sql, {'limit': limit, 'offset': offset})
            
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
            print(f"❌ Error getting all processing results: {e}")
            return []
    
    def get_processing_result_by_filename(self, filename: str) -> Optional[ProcessingResult]:
        """Get a processing result by filename."""
        try:
            sql = '''
                SELECT * FROM processing_results 
                WHERE filename = :filename 
                ORDER BY created_at DESC 
                LIMIT 1
            '''
            
            row = self.db_config.execute_raw_sql_single(sql, {'filename': filename})
            
            if row:
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
                return result
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting processing result by filename: {e}")
            return None
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get dashboard metrics."""
        try:
            # Get total files processed
            total_files_sql = "SELECT COUNT(*) FROM processing_results"
            total_files = self.db_config.execute_raw_sql_single(total_files_sql)[0] or 0
            
            # Get success rate
            success_sql = "SELECT COUNT(*) FROM processing_results WHERE processing_status = 'completed'"
            successful_files = self.db_config.execute_raw_sql_single(success_sql)[0] or 0
            success_rate = (successful_files / total_files * 100) if total_files > 0 else 0
            
            # Get average processing time
            avg_time_sql = '''
                SELECT AVG(processing_duration) 
                FROM processing_results 
                WHERE processing_duration IS NOT NULL
            '''
            avg_processing_time = self.db_config.execute_raw_sql_single(avg_time_sql)[0] or 0
            
            return {
                'total_files': total_files,
                'successful_files': successful_files,
                'success_rate': round(success_rate, 2),
                'avg_processing_time': round(avg_processing_time, 2) if avg_processing_time else 0
            }
            
        except Exception as e:
            print(f"❌ Error getting dashboard metrics: {e}")
            return {
                'total_files': 0,
                'successful_files': 0,
                'success_rate': 0,
                'avg_processing_time': 0
            }

    def create_processing_result(self, filename: str, original_filename: str, file_size: int, 
                                processing_status: ProcessingStatus, validation_status: ValidationStatus,
                                processing_start_time: datetime, processed_file_path: str, 
                                raw_json_data: str, notes: str = "") -> int:
        """Create a new processing result."""
        try:
            sql = '''
                INSERT INTO processing_results (
                    filename, original_filename, file_size, processing_status, validation_status,
                    processing_start_time, processed_file_path, raw_json_data, notes, created_at, updated_at
                ) VALUES (:filename, :original_filename, :file_size, :processing_status, :validation_status,
                         :processing_start_time, :processed_file_path, :raw_json_data, :notes, :created_at, :updated_at)
                RETURNING id
            '''
            
            now = datetime.utcnow()
            result = self.db_config.execute_raw_sql_single(sql, {
                'filename': filename,
                'original_filename': original_filename,
                'file_size': file_size,
                'processing_status': processing_status.value,
                'validation_status': validation_status.value,
                'processing_start_time': processing_start_time,
                'processed_file_path': processed_file_path,
                'raw_json_data': raw_json_data,
                'notes': notes,
                'created_at': now,
                'updated_at': now
            })
            
            return result[0] if result else 0
            
        except Exception as e:
            print(f"❌ Error creating processing result: {e}")
            return 0

    def update_processing_result(self, result_id: int, **kwargs) -> bool:
        """Update a processing result."""
        try:
            if not kwargs:
                return True
                
            set_clauses = []
            values = []
            
            for key, value in kwargs.items():
                if key == 'error_types' and isinstance(value, list):
                    value = json.dumps([e.value if hasattr(e, 'value') else e for e in value])
                elif hasattr(value, 'value'):  # Enum
                    value = value.value
                elif isinstance(value, datetime):
                    value = value.isoformat()
                    
                set_clauses.append(f"{key} = :{key}")
                values.append(value)
            
            if not set_clauses:
                return True
                
            set_clauses.append("updated_at = :updated_at")
            values.append(datetime.utcnow())
            values.append(result_id)
            
            sql = f'''
                UPDATE processing_results 
                SET {', '.join(set_clauses)}
                WHERE id = :id
            '''
            
            params = {f'param_{i}': val for i, val in enumerate(values[:-1])}
            params['id'] = values[-1]
            params['updated_at'] = datetime.utcnow()
            
            self.db_config.execute_raw_sql(sql, params)
            return True
            
        except Exception as e:
            print(f"❌ Error updating processing result: {e}")
            return False

    def get_processing_result(self, result_id: int) -> Optional[ProcessingResult]:
        """Get a processing result by ID."""
        try:
            sql = """
                SELECT id, filename, original_filename, file_size, processing_status, 
                       validation_status, processing_start_time, processing_end_time, 
                       processing_duration, total_parts, parts_mapped, parts_not_found, 
                       parts_manual_review, mapping_success_rate, customer_matched, 
                       customer_match_confidence, error_details, error_types, 
                       manual_corrections_made, epicor_ready, epicor_ready_with_one_click, 
                       missing_info_count, processed_file_path, epicor_json_path, 
                       raw_json_data, notes, created_at, updated_at
                FROM processing_results WHERE id = :id
            """
            row = self.db_config.execute_raw_sql_single(sql, {'id': result_id})
            
            if row:
                # Parse error_types JSON safely
                try:
                    error_types = [ErrorType(e) for e in json.loads(row[17] or '[]')]
                except (json.JSONDecodeError, ValueError):
                    error_types = []
                
                return ProcessingResult(
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
            return None
            
        except Exception as e:
            print(f"❌ Error getting processing result: {e}")
            return None

    def delete_processing_result(self, result_id: int) -> bool:
        """Delete a processing result."""
        try:
            sql = "DELETE FROM processing_results WHERE id = :id"
            self.db_config.execute_raw_sql(sql, {'id': result_id})
            return True
            
        except Exception as e:
            print(f"❌ Error deleting processing result: {e}")
            return False

    def mark_as_correct(self, result_id: int) -> bool:
        """Mark a processing result as correct."""
        return self.update_processing_result(result_id, validation_status=ValidationStatus.CORRECT)

    def mark_as_contains_error(self, result_id: int, error_types: List[ErrorType], error_details: str = "") -> bool:
        """Mark a processing result as containing errors."""
        return self.update_processing_result(
            result_id, 
            validation_status=ValidationStatus.CONTAINS_ERROR,
            error_types=error_types,
            error_details=error_details
        )

    def update_raw_json_data(self, file_id: int, raw_json_data: str) -> bool:
        """Update raw JSON data for a file."""
        return self.update_processing_result(file_id, raw_json_data=raw_json_data)

    def update_validation_status(self, file_id: int, validation_status: str) -> bool:
        """Update validation status for a file."""
        return self.update_processing_result(file_id, validation_status=validation_status)

    def add_error_type(self, file_id: int, error_type: ErrorType) -> bool:
        """Add an error type to a file."""
        try:
            # Get current error types
            result = self.get_processing_result(file_id)
            if not result:
                return False
                
            current_errors = result.error_types
            if error_type not in current_errors:
                current_errors.append(error_type)
                
            return self.update_processing_result(file_id, error_types=current_errors)
            
        except Exception as e:
            print(f"❌ Error adding error type: {e}")
            return False

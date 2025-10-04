"""
Step 5: Metrics Database Module
Tracks file processing results, accuracy rates, error types, and approval/decline ratios.
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

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
    SHIPPING_INFO = "shipping_info"  # Keep for backward compatibility
    PART_NUMBERS = "part_numbers"    # Keep for backward compatibility
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
    processing_duration: Optional[float]  # in seconds
    
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
    
    def __init__(self, db_path: str = "data/metrics.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the metrics database with required tables."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create processing_results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processing_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    processing_status TEXT NOT NULL,
                    validation_status TEXT NOT NULL DEFAULT 'pending_review',
                    processing_start_time TIMESTAMP NOT NULL,
                    processing_end_time TIMESTAMP,
                    processing_duration REAL,
                    
                    -- Metrics
                    total_parts INTEGER NOT NULL DEFAULT 0,
                    parts_mapped INTEGER NOT NULL DEFAULT 0,
                    parts_not_found INTEGER NOT NULL DEFAULT 0,
                    parts_manual_review INTEGER NOT NULL DEFAULT 0,
                    mapping_success_rate REAL NOT NULL DEFAULT 0.0,
                    customer_matched BOOLEAN NOT NULL DEFAULT FALSE,
                    customer_match_confidence REAL NOT NULL DEFAULT 0.0,
                    
                    -- Error tracking
                    error_types TEXT NOT NULL DEFAULT '[]',  -- JSON array
                    error_details TEXT NOT NULL DEFAULT '',
                    manual_corrections_made INTEGER NOT NULL DEFAULT 0,
                    
                    -- Epicor readiness
                    epicor_ready BOOLEAN NOT NULL DEFAULT FALSE,
                    epicor_ready_with_one_click BOOLEAN NOT NULL DEFAULT FALSE,
                    missing_info_count INTEGER NOT NULL DEFAULT 0,
                    
                    -- File paths
                    processed_file_path TEXT NOT NULL,
                    epicor_json_path TEXT,
                    
                    -- Raw JSON data
                    raw_json_data TEXT NOT NULL DEFAULT '{}',
                    
                    -- Notes
                    notes TEXT NOT NULL DEFAULT '',
                    
                    -- Metadata
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_processing_status ON processing_results(processing_status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_validation_status ON processing_results(validation_status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON processing_results(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_epicor_ready ON processing_results(epicor_ready)')
            
            # Add raw_json_data column if it doesn't exist (migration)
            try:
                cursor.execute('ALTER TABLE processing_results ADD COLUMN raw_json_data TEXT NOT NULL DEFAULT "{}"')
            except sqlite3.OperationalError:
                # Column already exists, ignore the error
                pass
            
            # Add notes column if it doesn't exist (migration)
            try:
                cursor.execute('ALTER TABLE processing_results ADD COLUMN notes TEXT NOT NULL DEFAULT ""')
            except sqlite3.OperationalError:
                # Column already exists, ignore the error
                pass
            
            conn.commit()
    
    def create_processing_result(self, 
                               filename: str,
                               original_filename: str,
                               file_size: int,
                               processed_file_path: str,
                               raw_json_data: str = '{}') -> ProcessingResult:
        """Create a new processing result record."""
        now = datetime.now()
        
        result = ProcessingResult(
            id=None,
            filename=filename,
            original_filename=original_filename,
            file_size=file_size,
            processing_status=ProcessingStatus.PROCESSING,
            validation_status=ValidationStatus.PENDING_REVIEW,
            processing_start_time=now,
            processing_end_time=None,
            processing_duration=None,
            total_parts=0,
            parts_mapped=0,
            parts_not_found=0,
            parts_manual_review=0,
            mapping_success_rate=0.0,
            customer_matched=False,
            customer_match_confidence=0.0,
            error_types=[],
            error_details="",
            manual_corrections_made=0,
            epicor_ready=False,
            epicor_ready_with_one_click=False,
            missing_info_count=0,
            processed_file_path=processed_file_path,
            epicor_json_path=None,
            raw_json_data=raw_json_data,
            notes="",
            created_at=now,
            updated_at=now
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO processing_results (
                    filename, original_filename, file_size, processing_status, validation_status,
                    processing_start_time, processed_file_path, raw_json_data, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.filename, result.original_filename, result.file_size,
                result.processing_status.value, result.validation_status.value,
                result.processing_start_time, result.processed_file_path, result.raw_json_data,
                result.notes, result.created_at, result.updated_at
            ))
            
            result.id = cursor.lastrowid
            conn.commit()
        
        return result
    
    def update_processing_result(self, result_id: int, **kwargs) -> bool:
        """Update a processing result with new data."""
        if not kwargs:
            return False
        
        # Convert ProcessingStatus and ValidationStatus enums to strings
        if 'processing_status' in kwargs and isinstance(kwargs['processing_status'], ProcessingStatus):
            kwargs['processing_status'] = kwargs['processing_status'].value
        
        if 'validation_status' in kwargs and isinstance(kwargs['validation_status'], ValidationStatus):
            kwargs['validation_status'] = kwargs['validation_status'].value
        
        # Convert error_types list to JSON string
        if 'error_types' in kwargs and isinstance(kwargs['error_types'], list):
            kwargs['error_types'] = json.dumps([error.value if isinstance(error, ErrorType) else error for error in kwargs['error_types']])
        
        # Add updated_at timestamp
        kwargs['updated_at'] = datetime.now()
        
        # Build update query
        set_clauses = [f"{key} = ?" for key in kwargs.keys()]
        values = list(kwargs.values()) + [result_id]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                UPDATE processing_results 
                SET {', '.join(set_clauses)}
                WHERE id = ?
            ''', values)
            
            conn.commit()
            return cursor.rowcount > 0
    
    def get_processing_result(self, result_id: int) -> Optional[ProcessingResult]:
        """Get a processing result by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM processing_results WHERE id = ?', (result_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_processing_result(row)
            return None
    
    def get_all_processing_results(self, limit: int = 100, offset: int = 0) -> List[ProcessingResult]:
        """Get all processing results with pagination."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM processing_results 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            rows = cursor.fetchall()
            return [self._row_to_processing_result(row) for row in rows]
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get comprehensive dashboard metrics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total files processed
            cursor.execute('SELECT COUNT(*) FROM processing_results')
            total_files = cursor.fetchone()[0]
            
            # Hallucination rate (files with no missing info that were marked as containing errors)
            # Only count files that were "pending_review" (no missing info) but turned out to have errors
            cursor.execute('''
                SELECT 
                    validation_status,
                    COUNT(*) as count
                FROM processing_results 
                WHERE missing_info_count = 0 AND validation_status IN ('correct', 'contains_error', 'pending_review')
                GROUP BY validation_status
            ''')
            hallucination_data = dict(cursor.fetchall())
            pending_with_no_missing = (hallucination_data.get('correct', 0) + 
                                      hallucination_data.get('contains_error', 0) + 
                                      hallucination_data.get('pending_review', 0))
            errors_in_pending = hallucination_data.get('contains_error', 0)
            hallucination_rate = (errors_in_pending / pending_with_no_missing * 100) if pending_with_no_missing > 0 else 0
            
            # Keep the old accuracy rate for backwards compatibility
            accuracy_rate = 100 - hallucination_rate if pending_with_no_missing > 0 else 0
            
            # Error types breakdown
            cursor.execute('''
                SELECT error_types, error_details, COUNT(*) as count
                FROM processing_results 
                WHERE validation_status = 'contains_error'
                GROUP BY error_types, error_details
            ''')
            error_types_data = cursor.fetchall()
            
            error_types_breakdown = {}
            other_errors = []
            
            for error_types_json, error_details, count in error_types_data:
                try:
                    error_types = json.loads(error_types_json)
                    for error_type in error_types:
                        if error_type == 'other' and error_details:
                            # Each "other" error gets its own entry
                            other_errors.append(error_details)
                        else:
                            error_types_breakdown[error_type] = error_types_breakdown.get(error_type, 0) + count
                except json.JSONDecodeError:
                    continue
            
            # Approval/decline ratios
            cursor.execute('''
                SELECT 
                    epicor_ready_with_one_click,
                    missing_info_count,
                    COUNT(*) as count
                FROM processing_results 
                WHERE processing_status = 'completed'
                GROUP BY epicor_ready_with_one_click, missing_info_count
            ''')
            approval_data = cursor.fetchall()
            
            one_click_ready = sum(count for ready, missing, count in approval_data if ready)
            missing_info = sum(count for ready, missing, count in approval_data if missing > 0)
            total_completed = sum(count for ready, missing, count in approval_data)
            
            one_click_rate = (one_click_ready / total_completed * 100) if total_completed > 0 else 0
            missing_info_rate = (missing_info / total_completed * 100) if total_completed > 0 else 0
            
            # Recent activity (last 30 days)
            cursor.execute('''
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as count
                FROM processing_results 
                WHERE created_at >= datetime('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            ''')
            recent_activity = cursor.fetchall()
            
            # Processing time statistics
            cursor.execute('''
                SELECT 
                    AVG(processing_duration) as avg_duration,
                    MIN(processing_duration) as min_duration,
                    MAX(processing_duration) as max_duration
                FROM processing_results 
                WHERE processing_duration IS NOT NULL
            ''')
            time_stats = cursor.fetchone()
            
            return {
                'total_files': total_files,
                'hallucination_rate': round(hallucination_rate, 2),
                'pending_with_no_missing_count': pending_with_no_missing,
                'errors_in_pending_count': errors_in_pending,
                'accuracy_rate': round(accuracy_rate, 2),
                'error_types_breakdown': error_types_breakdown,
                'other_errors': other_errors,
                'one_click_ready_rate': round(one_click_rate, 2),
                'one_click_ready_count': one_click_ready,
                'missing_info_rate': round(missing_info_rate, 2),
                'missing_info_count': missing_info,
                'total_completed': total_completed,
                'recent_activity': recent_activity,
                'avg_processing_time': round(time_stats[0], 2) if time_stats[0] else 0,
                'min_processing_time': round(time_stats[1], 2) if time_stats[1] else 0,
                'max_processing_time': round(time_stats[2], 2) if time_stats[2] else 0
            }
    
    def delete_processing_result(self, result_id: int) -> bool:
        """Delete a processing result from the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM processing_results WHERE id = ?", (result_id,))
            success = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            
            return success
        except Exception as e:
            print(f"Error deleting processing result: {e}")
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
    
    def _row_to_processing_result(self, row: Tuple) -> ProcessingResult:
        """Convert database row to ProcessingResult object."""
        # Parse error_types JSON
        error_types_json = row[16]  # error_types column
        try:
            if isinstance(error_types_json, str):
                error_types = [ErrorType(error_type) for error_type in json.loads(error_types_json)]
            else:
                error_types = []
        except (json.JSONDecodeError, ValueError, TypeError):
            error_types = []
        
        return ProcessingResult(
            id=row[0],
            filename=row[1],
            original_filename=row[2],
            file_size=row[3],
            processing_status=ProcessingStatus(row[4]),
            validation_status=ValidationStatus(row[5]),
            processing_start_time=datetime.fromisoformat(row[6]),
            processing_end_time=datetime.fromisoformat(row[7]) if row[7] else None,
            processing_duration=row[8],
            total_parts=row[9],
            parts_mapped=row[10],
            parts_not_found=row[11],
            parts_manual_review=row[12],
            mapping_success_rate=row[13],
            customer_matched=bool(row[14]),
            customer_match_confidence=row[15],
            error_types=error_types,
            error_details=row[17],
            manual_corrections_made=row[18],
            epicor_ready=bool(row[19]),
            epicor_ready_with_one_click=bool(row[20]),
            missing_info_count=row[21],
            processed_file_path=row[22],
            epicor_json_path=row[23],
            raw_json_data=row[24],
            notes=row[27],
            created_at=datetime.fromisoformat(row[25]),
            updated_at=datetime.fromisoformat(row[26])
        )
    
    def update_raw_json_data(self, file_id: int, raw_json_data: str) -> bool:
        """Update the raw JSON data for a specific file."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE processing_results 
                SET raw_json_data = ?, updated_at = ?
                WHERE id = ?
            """, (raw_json_data, datetime.now().isoformat(), file_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return success
        except Exception as e:
            print(f"Error updating raw JSON data: {e}")
            return False
    
    def update_validation_status(self, file_id: int, validation_status: str) -> bool:
        """Update the validation status for a specific file."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE processing_results 
                SET validation_status = ?, updated_at = ?
                WHERE id = ?
            """, (validation_status, datetime.now().isoformat(), file_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return success
        except Exception as e:
            print(f"Error updating validation status: {e}")
            return False


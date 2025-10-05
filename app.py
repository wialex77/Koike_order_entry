"""
Main Flask Web Application
Integrates all steps to create a complete purchase order processing web app.
"""

import os
import json
import tempfile
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables from config file
load_dotenv('config.env')

# Import our custom modules
from step1_upload import FileUploadHandler
from step2_ocr_ai import DocumentProcessor
from step3_databases import DatabaseManager
from step4_mapping import PartNumberMapper
from step5_metrics_db_postgres import MetricsDatabase, ProcessingStatus, ValidationStatus, ErrorType
from database_config import db_config

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Change this in production

# Enable CORS for Outlook add-in (permissive for development)
CORS(app, origins=['*'])

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Global progress tracking
current_progress = {'percentage': 0, 'status': 'Ready'}
app.config['PROCESSED_FOLDER'] = 'processed'

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Initialize components
file_handler = FileUploadHandler(app.config['UPLOAD_FOLDER'])
document_processor = DocumentProcessor()
db_manager = DatabaseManager()
part_mapper = PartNumberMapper(db_manager)
metrics_db = MetricsDatabase()

MISSING_FIELDS_TRACKER_PATH = 'data/missing_fields_tracker.json'

def detect_missing_fields(epicor_json):
    """Detect which fields are marked as MISSING in the Epicor JSON."""
    missing = []
    
    try:
        # Check OrderHed fields - use exact Epicor field names
        if epicor_json.get('ds', {}).get('OrderHed'):
            order_hed = epicor_json['ds']['OrderHed'][0]
            if order_hed.get('CustNum') == 'MISSING':
                missing.append('CustNum')
            if order_hed.get('PONum') == 'MISSING':
                missing.append('PONum')
            if order_hed.get('OTSName') == 'MISSING':
                missing.append('OTSName')
            if order_hed.get('OTSAddress1') == 'MISSING':
                missing.append('OTSAddress1')
            if order_hed.get('OTSCity') == 'MISSING':
                missing.append('OTSCity')
            if order_hed.get('OTSState') == 'MISSING':
                missing.append('OTSState')
            if order_hed.get('OTSZip') == 'MISSING':
                missing.append('OTSZip')
        
        # Check OrderDtl fields - use exact Epicor field names
        if epicor_json.get('ds', {}).get('OrderDtl'):
            for item in epicor_json['ds']['OrderDtl']:
                if item.get('PartNum') == 'MISSING':
                    missing.append('PartNum')
                if item.get('DocUnitPrice') == 'MISSING':
                    missing.append('DocUnitPrice')
                if item.get('SellingQuantity') == 'MISSING':
                    missing.append('SellingQuantity')
                if item.get('LineDesc') == 'MISSING':
                    missing.append('LineDesc')
    except Exception as e:
        print(f"Error detecting missing fields: {e}")
    
    return missing

def increment_missing_fields(missing_fields_list):
    """Increment counters for missing fields."""
    try:
        # Load current tracker
        if os.path.exists(MISSING_FIELDS_TRACKER_PATH):
            with open(MISSING_FIELDS_TRACKER_PATH, 'r') as f:
                tracker = json.load(f)
        else:
            tracker = {}
        
        # Increment counters
        for field in missing_fields_list:
            if field not in tracker:
                tracker[field] = 0
            tracker[field] += 1
        
        # Save tracker
        with open(MISSING_FIELDS_TRACKER_PATH, 'w') as f:
            json.dump(tracker, f, indent=2)
            
    except Exception as e:
        print(f"Error incrementing missing fields: {e}")

def get_missing_fields_stats():
    """Get missing fields statistics."""
    try:
        if not os.path.exists(MISSING_FIELDS_TRACKER_PATH):
            return []
        
        with open(MISSING_FIELDS_TRACKER_PATH, 'r') as f:
            tracker = json.load(f)
        
        # Calculate total and percentages
        total = sum(tracker.values())
        if total == 0:
            return []
        
        stats = []
        for field, count in tracker.items():
            if count > 0:  # Only show fields that have been missing at least once
                stats.append({
                    'field_name': field,
                    'count': count,
                    'percentage': round((count / total) * 100, 1)
                })
        
        # Sort by count descending
        stats.sort(key=lambda x: x['count'], reverse=True)
        return stats
        
    except Exception as e:
        print(f"Error getting missing fields stats: {e}")
        return []

@app.route('/')
def index():
    """Main page with file upload form."""
    return render_template('index.html')

@app.route('/progress')
def progress():
    """Server-Sent Events endpoint for real-time progress updates."""
    def generate():
        while True:
            yield f"data: {json.dumps(current_progress)}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/upload-test', methods=['POST'])
def upload_file_test():
    """Test endpoint to isolate 500 error source."""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Test 1: Save file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Test 2: Initialize document processor
        try:
            processor = DocumentProcessor()
            return jsonify({
                'success': True,
                'message': 'File saved and processor initialized',
                'filename': filename,
                'size': os.path.getsize(file_path),
                'processor_init': 'OK'
            })
        except Exception as proc_error:
            return jsonify({
                'success': False,
                'message': f'Processor initialization failed: {str(proc_error)}',
                'filename': filename,
                'size': os.path.getsize(file_path)
            }), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload-simple', methods=['POST'])
def upload_file_simple():
    """Simple file upload test without OCR/AI processing."""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Just save the file and return success
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'filename': filename,
            'size': os.path.getsize(file_path)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing."""
    global current_progress
    
    # Create processing result record
    processing_result = None
    
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Step 1: Validate and save file
        current_progress = {'percentage': 15, 'status': 'Reading file...'}
        success, message, file_path = file_handler.save_file(file)
        if not success:
            return jsonify({'error': message}), 400
        
        # Create processing result record
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        processed_filename = f"processed_{timestamp}.json"
        processed_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
        
        processing_result_id = metrics_db.create_processing_result(
            filename=processed_filename,
            original_filename=file.filename,
            file_size=os.path.getsize(file_path),
            processing_status=ProcessingStatus.PROCESSING,
            validation_status=ValidationStatus.PENDING_REVIEW,
            processing_start_time=datetime.now(),
            processed_file_path=processed_path,
            raw_json_data='{}'  # Will be updated after processing
        )
        
        # Step 2: Process document with OCR/AI
        current_progress = {'percentage': 40, 'status': 'Finding account number and address...'}
        try:
            po_data = document_processor.process_document(file_path)
        except Exception as e:
            # Update processing result with error
            if processing_result_id:
                metrics_db.update_processing_result(
                    processing_result_id,
                    processing_status=ProcessingStatus.ERROR,
                    error_details=f'Document processing failed: {str(e)}'
                )
            # Clean up uploaded file
            file_handler.cleanup_file(file_path)
            return jsonify({'error': f'Document processing failed: {str(e)}'}), 500
        
        # Step 3 & 4: Map part numbers and lookup account
        current_progress = {'percentage': 70, 'status': 'Mapping part numbers...'}
        try:
            mapped_data = part_mapper.process_purchase_order(po_data)
        except Exception as e:
            # Update processing result with error
            if processing_result:
                metrics_db.update_processing_result(
                    processing_result_id,
                    processing_status=ProcessingStatus.ERROR,
                    error_details=f'Mapping failed: {str(e)}'
                )
            # Clean up uploaded file
            file_handler.cleanup_file(file_path)
            return jsonify({'error': f'Mapping failed: {str(e)}'}), 500
        
        # Save processed data
        current_progress = {'percentage': 90, 'status': 'Finalizing results...'}
        
        part_mapper.save_mapped_data(mapped_data, processed_path)
        
        # Generate manual review report
        review_report = part_mapper.generate_manual_review_report(mapped_data)
        
        # Get validation results
        validation = part_mapper.validate_for_epicor_export(mapped_data)
        
        # Calculate metrics
        summary = mapped_data.processing_summary
        error_types = []
        
        # Determine error types based on validation and processing results
        if not validation.get('is_valid', False):
            if not mapped_data.company_info.account_number or mapped_data.company_info.customer_match_status != 'matched':
                error_types.append(ErrorType.ACCOUNT_NUMBER)
            if not mapped_data.company_info.shipping_address:
                error_types.append(ErrorType.SHIPPING_INFO)
            if summary.get('parts_not_found', 0) > 0 or summary.get('parts_manual_review', 0) > 0:
                error_types.append(ErrorType.PART_NUMBERS)
            if not mapped_data.company_info.company_name:
                error_types.append(ErrorType.COMPANY_INFO)
        
        # Calculate missing info count
        missing_info_count = 0
        if not mapped_data.company_info.account_number:
            missing_info_count += 1
        if not mapped_data.company_info.shipping_address:
            missing_info_count += 1
        if summary.get('parts_not_found', 0) > 0:
            missing_info_count += summary.get('parts_not_found', 0)
        if summary.get('parts_manual_review', 0) > 0:
            missing_info_count += summary.get('parts_manual_review', 0)
        
        # Update processing result with metrics and raw JSON data
        processing_end_time = datetime.now()
        # Get the processing result object to access processing_start_time
        processing_result_obj = metrics_db.get_processing_result(processing_result_id)
        if not processing_result_obj:
            raise Exception(f"Processing result with ID {processing_result_id} not found")
        processing_duration = (processing_end_time - processing_result_obj.processing_start_time).total_seconds()
        
        # Get the Epicor JSON data - try to generate it even if validation fails
        try:
            # First try the normal Epicor export with validation
            epicor_json = part_mapper.export_to_epicor_json(mapped_data)
            raw_json_data = json.dumps(epicor_json, indent=2)
        except Exception as e:
            # If Epicor export fails due to validation, try to generate Epicor format anyway
            try:
                # Generate Epicor format without strict validation
                epicor_json = part_mapper._generate_epicor_format_unvalidated(mapped_data)
                raw_json_data = json.dumps(epicor_json, indent=2)
            except Exception as e2:
                # If that also fails, fall back to internal format
                raw_json_data = json.dumps(part_mapper.export_to_json(mapped_data), indent=2)
        
        metrics_db.update_processing_result(
            processing_result_id,
            processing_status=ProcessingStatus.COMPLETED,
            processing_end_time=processing_end_time,
            processing_duration=processing_duration,
            total_parts=summary.get('total_parts', 0),
            parts_mapped=summary.get('parts_mapped', 0),
            parts_not_found=summary.get('parts_not_found', 0),
            parts_manual_review=summary.get('parts_manual_review', 0),
            mapping_success_rate=summary.get('mapping_success_rate', 0.0),
            customer_matched=summary.get('customer_matched', False),
            customer_match_confidence=mapped_data.company_info.customer_match_confidence,
            error_types=error_types,
            error_details=validation.get('errors', ''),
            epicor_ready=validation.get('is_valid', False),
            epicor_ready_with_one_click=validation.get('is_valid', False) and missing_info_count == 0,
            missing_info_count=missing_info_count,
            raw_json_data=raw_json_data
        )
        
        # Detect missing fields in the Epicor JSON for tracking
        missing_fields = detect_missing_fields(epicor_json)
        if missing_fields:
            # Increment missing field counters
            increment_missing_fields(missing_fields)
            
            # Store missing fields as a note
            existing_notes = metrics_db.get_processing_result(processing_result_id).notes or ""
            missing_fields_note = f"Missing fields: {', '.join(missing_fields)}"
            updated_notes = f"{existing_notes}\n{missing_fields_note}" if existing_notes else missing_fields_note
            metrics_db.update_processing_result(
                processing_result_id,
                notes=updated_notes
            )
        
        # Clean up uploaded file
        file_handler.cleanup_file(file_path)
        
        # Final progress update
        current_progress = {'percentage': 100, 'status': 'Complete!'}
        
        # Return results
        return jsonify({
            'success': True,
            'message': 'File processed successfully',
            'data': part_mapper.export_to_json(mapped_data),
            'review_report': review_report,
            'processed_file': processed_filename,
            'validation': validation,
            'processing_result_id': processing_result_id,
            'missing_fields': missing_fields
        })
        
    except Exception as e:
        # Update processing result with error if it exists
        if processing_result_id:
            metrics_db.update_processing_result(
                processing_result_id,
                processing_status=ProcessingStatus.ERROR,
                error_details=f'Unexpected error: {str(e)}'
            )
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/api/preview/<filename>')
def preview_file(filename):
    """Preview processed JSON file in Epicor format."""
    try:
        file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Load the processed data
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        return jsonify({
            'success': True,
            'original_format': json_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download processed JSON file in Epicor format."""
    try:
        file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Load the processed data
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Convert to MappedPurchaseOrderData object
        from step4_mapping import MappedCompanyInfo, MappedLineItem, MappedPurchaseOrderData
        
        company_info = MappedCompanyInfo(**json_data['company_info'])
        line_items = [MappedLineItem(**item) for item in json_data['line_items']]
        
        mapped_data = MappedPurchaseOrderData(
            company_info=company_info,
            line_items=line_items,
            processing_summary=json_data['processing_summary']
        )
        
        # Export to Epicor format
        epicor_json = part_mapper.export_to_epicor_json(mapped_data)
        
        # Create temporary file with Epicor format
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(epicor_json, temp_file, indent=2, ensure_ascii=False)
        temp_file.close()
        
        return send_file(temp_file.name, as_attachment=True, download_name=f"epicor_{filename}")
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/validate/<filename>')
def validate_file(filename):
    """Get validation status for a processed file."""
    try:
        file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Load the processed data
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Convert to MappedPurchaseOrderData object
        from step4_mapping import MappedCompanyInfo, MappedLineItem, MappedPurchaseOrderData
        
        company_info = MappedCompanyInfo(**json_data['company_info'])
        line_items = [MappedLineItem(**item) for item in json_data['line_items']]
        
        mapped_data = MappedPurchaseOrderData(
            company_info=company_info,
            line_items=line_items,
            processing_summary=json_data['processing_summary']
        )
        
        # Get validation status
        validation = part_mapper.validate_for_epicor_export(mapped_data)
        
        return jsonify(validation)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-customer/<filename>', methods=['POST'])
def update_customer_mapping(filename):
    """Update customer mapping with manual correction."""
    try:
        file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        data = request.get_json()
        account_number = data.get('account_number', '').strip()
        
        if not account_number:
            return jsonify({'error': 'Account number is required'}), 400
        
        # Load the processed data
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Convert to MappedPurchaseOrderData object
        from step4_mapping import MappedCompanyInfo, MappedLineItem, MappedPurchaseOrderData
        
        company_info = MappedCompanyInfo(**json_data['company_info'])
        line_items = [MappedLineItem(**item) for item in json_data['line_items']]
        
        mapped_data = MappedPurchaseOrderData(
            company_info=company_info,
            line_items=line_items,
            processing_summary=json_data['processing_summary']
        )
        
        # Update customer mapping
        updated_data = part_mapper.update_customer_mapping(mapped_data, account_number)
        
        # Save updated data
        updated_json = part_mapper.export_to_json(updated_data)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(updated_json, f, indent=2, ensure_ascii=False)
        
        # Return updated data and validation
        return jsonify({
            'success': True,
            'data': updated_json,
            'validation': part_mapper.validate_for_epicor_export(updated_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-part/<filename>', methods=['POST'])
def update_part_mapping(filename):
    """Update part mapping with manual correction."""
    try:
        file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        data = request.get_json()
        line_index = data.get('line_index')
        internal_part_number = data.get('internal_part_number', '').strip()
        
        if line_index is None or not internal_part_number:
            return jsonify({'error': 'Line index and internal part number are required'}), 400
        
        # Load the processed data
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Convert to MappedPurchaseOrderData object
        from step4_mapping import MappedCompanyInfo, MappedLineItem, MappedPurchaseOrderData
        
        company_info = MappedCompanyInfo(**json_data['company_info'])
        line_items = [MappedLineItem(**item) for item in json_data['line_items']]
        
        mapped_data = MappedPurchaseOrderData(
            company_info=company_info,
            line_items=line_items,
            processing_summary=json_data['processing_summary']
        )
        
        # Update part mapping
        updated_data = part_mapper.update_part_mapping(mapped_data, line_index, internal_part_number)
        
        # Save updated data
        updated_json = part_mapper.export_to_json(updated_data)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(updated_json, f, indent=2, ensure_ascii=False)
        
        # Return updated data and validation
        return jsonify({
            'success': True,
            'data': updated_json,
            'validation': part_mapper.validate_for_epicor_export(updated_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/dashboard')
def dashboard():
    """View dashboard with metrics."""
    return render_template('dashboard.html')

@app.route('/files')
def file_management():
    """View file management with correct/error buttons."""
    return render_template('files.html')

@app.route('/api/dashboard/metrics')
def get_dashboard_metrics():
    """Get dashboard metrics data."""
    try:
        metrics = metrics_db.get_dashboard_metrics()
        # Add missing fields stats
        metrics['missing_fields_stats'] = get_missing_fields_stats()
        return jsonify(metrics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files')
def get_processing_files():
    """Get all processing files with pagination."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        offset = (page - 1) * per_page
        
        results = metrics_db.get_all_processing_results(limit=per_page, offset=offset)
        
        # Convert to serializable format
        files_data = []
        for result in results:
            # Create processing summary from the individual fields
            processing_summary = {
                'total_parts': result.total_parts,
                'parts_mapped': result.parts_mapped,
                'parts_not_found': result.parts_not_found,
                'parts_manual_review': result.parts_manual_review,
                'mapping_success_rate': result.mapping_success_rate,
                'customer_matched': result.customer_matched,
                'customer_confidence': result.customer_match_confidence,
                'requires_manual_review': result.parts_manual_review > 0 or not result.customer_matched
            }
            
            files_data.append({
                'id': result.id,
                'filename': result.filename,
                'original_filename': result.original_filename,
                'file_size': result.file_size,
                'processing_status': result.processing_status.value,
                'validation_status': result.validation_status.value,
                'processing_start_time': result.processing_start_time.isoformat(),
                'processing_end_time': result.processing_end_time.isoformat() if result.processing_end_time else None,
                'processing_duration': result.processing_duration,
                'total_parts': result.total_parts,
                'parts_mapped': result.parts_mapped,
                'parts_not_found': result.parts_not_found,
                'parts_manual_review': result.parts_manual_review,
                'mapping_success_rate': result.mapping_success_rate,
                'customer_matched': result.customer_matched,
                'customer_match_confidence': result.customer_match_confidence,
                'error_types': [error.value for error in result.error_types],
                'error_details': result.error_details,
                'manual_corrections_made': result.manual_corrections_made,
                'epicor_ready': result.epicor_ready,
                'epicor_ready_with_one_click': result.epicor_ready_with_one_click,
                'missing_info_count': result.missing_info_count,
                'raw_json_data': result.raw_json_data,
                'processing_summary': processing_summary,
                'created_at': result.created_at.isoformat(),
                'updated_at': result.updated_at.isoformat()
            })
        
        return jsonify({
            'files': files_data,
            'page': page,
            'per_page': per_page,
            'total': len(files_data)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/<int:file_id>/mark-correct', methods=['POST'])
def mark_file_correct(file_id):
    """Mark a file as correct."""
    try:
        success = metrics_db.mark_as_correct(file_id)
        if success:
            return jsonify({'success': True, 'message': 'File marked as correct'})
        else:
            return jsonify({'error': 'File not found or could not be updated'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/<int:file_id>/mark-error', methods=['POST'])
def mark_file_error(file_id):
    """Mark a file as containing errors."""
    try:
        data = request.get_json()
        error_types = [ErrorType(error_type) for error_type in data.get('error_types', [])]
        error_details = data.get('error_details', '')
        
        success = metrics_db.mark_as_contains_error(file_id, error_types, error_details)
        if success:
            return jsonify({'success': True, 'message': 'File marked as containing errors'})
        else:
            return jsonify({'error': 'File not found or could not be updated'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/<int:file_id>/enter-order', methods=['POST'])
def enter_order(file_id):
    """Enter order into Epicor."""
    try:
        data = request.get_json()
        json_data = data.get('json_data', '')
        
        if not json_data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate JSON
        try:
            epicor_json = json.loads(json_data)
        except json.JSONDecodeError as e:
            return jsonify({'error': f'Invalid JSON format: {str(e)}'}), 400
        
        # TODO: Implement actual Epicor API integration here
        # For now, we'll just update the database status
        # In production, you would:
        # 1. Validate the Epicor JSON structure
        # 2. Make API call to Epicor system
        # 3. Handle response and errors
        
        print(f"Entering order for file {file_id} into Epicor...")
        print(f"JSON data: {json_data[:200]}...")  # Print first 200 chars
        
        # Update database to mark as approved and entered
        if file_id > 0:
            metrics_db.update_processing_result(
                file_id,
                validation_status=ValidationStatus.CORRECT,
                notes="Approved and entered from Outlook add-in"
            )
        
        # Simulate success
        return jsonify({
            'success': True,
            'message': 'Order entered successfully',
            'epicor_order_id': f'SIMULATED-{file_id}'  # Would be real order ID from Epicor
        })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/<int:file_id>/delete', methods=['DELETE'])
def delete_file(file_id):
    """Delete a file from the database."""
    try:
        success = metrics_db.delete_processing_result(file_id)
        if success:
            return jsonify({'success': True, 'message': 'File deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'File not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error deleting file: {str(e)}'}), 500

@app.route('/history')
def processing_history():
    """View processing history."""
    try:
        processed_files = []
        if os.path.exists(app.config['PROCESSED_FOLDER']):
            for filename in os.listdir(app.config['PROCESSED_FOLDER']):
                if filename.endswith('.json'):
                    file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
                    stat = os.stat(file_path)
                    processed_files.append({
                        'filename': filename,
                        'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                        'size': stat.st_size
                    })
        
        # Sort by creation time, newest first
        processed_files.sort(key=lambda x: x['created'], reverse=True)
        
        return render_template('history.html', files=processed_files)
    except Exception as e:
        flash(f'Error loading history: {str(e)}', 'error')
        return render_template('history.html', files=[])

# DISABLED: Outlook add-in functionality moved to outlook_addin_disabled folder
# @app.route('/api/process-email', methods=['POST'])
# def process_email():
#     """Process email data from Outlook add-in."""
#     try:
#         data = request.get_json()
#         
#         # Extract email data
#         email_subject = data.get('subject', '')
#         email_body = data.get('body', '')
#         attachments = data.get('attachments', [])
#         
#         # Check if we have attachments to process
#         processed_data = None
#         
#         if attachments:
#             # Process the first PDF attachment
#             for attachment in attachments:
#                 if attachment.get('name', '').lower().endswith('.pdf'):
#                     # In a real implementation, you would:
#                     # 1. Download the attachment from the email
#                     # 2. Save it to a temporary location
#                     # 3. Process it with your existing document processor
#                     
#                     # For now, we'll simulate processing based on the email content
#                     processed_data = simulate_email_processing(email_subject, email_body, attachment)
#                     break
#         
#         if not processed_data:
#             # If no attachments, try to extract PO data from email body
#             processed_data = extract_po_from_email_body(email_subject, email_body)
#         
#         if not processed_data:
#             return jsonify({
#                 'success': False,
#                 'error': 'No PO data found in email or attachments'
#             }), 400
#         
#         # Process with existing mapping logic
#         try:
#             mapped_data = part_mapper.process_purchase_order(processed_data)
#         except Exception as e:
#             return jsonify({
#                 'success': False,
#                 'error': f'Mapping failed: {str(e)}'
#             }), 500
#         
#         # Generate Epicor JSON
#         try:
#             epicor_json = part_mapper.export_to_epicor_json(mapped_data)
#         except Exception as e:
#             # If validation fails, return the mapped data anyway for manual review
#             epicor_json = None
#             validation_error = str(e)
#         
#         # Return results
#         return jsonify({
#             'success': True,
#             'data': part_mapper.export_to_json(mapped_data),
#             'epicor_json': epicor_json,
#             'validation_error': validation_error if 'validation_error' in locals() else None
#         })
#         
#     except Exception as e:
#         return jsonify({
#             'success': False,
#             'error': f'Unexpected error: {str(e)}'
#         }), 500

# DISABLED: Outlook add-in helper functions moved to outlook_addin_disabled folder
# def simulate_email_processing(subject, body, attachment):
#     """Simulate processing an email attachment (placeholder for real implementation)."""
#     # In a real implementation, this would:
#     # 1. Download the attachment from Outlook
#     # 2. Save it to a temporary file
#     # 3. Process it with document_processor.process_document()
#     
#     # For now, return sample data based on email content
#     return {
#         "company_info": {
#             "company_name": extract_company_name_from_email(subject, body),
#             "billing_address": "",
#             "shipping_address": "",
#             "email": "",
#             "phone_number": "",
#             "contact_person": "",
#             "contact_person_email": "",
#             "customer_po_number": extract_po_number_from_email(subject, body),
#             "po_date": "",
#             "notes": "",
#             "subtotal": 0.0,
#             "tax_amount": 0.0,
#             "tax_rate": 0.0,
#             "grand_total": 0.0
#         },
#         "line_items": extract_line_items_from_email(body)
#     }

# def extract_po_from_email_body(subject, body):
#     """Extract PO data from email body when no attachments are available."""
#     # This is a simplified extraction - in reality you'd use AI to parse the email content
#     company_name = extract_company_name_from_email(subject, body)
#     po_number = extract_po_number_from_email(subject, body)
#     
#     if not company_name and not po_number:
#         return None
#     
#     return {
#         "company_info": {
#             "company_name": company_name,
#             "billing_address": "",
#             "shipping_address": "",
#             "email": "",
#             "phone_number": "",
#             "contact_person": "",
#             "contact_person_email": "",
#             "customer_po_number": po_number,
#             "po_date": "",
#             "notes": "",
#             "subtotal": 0.0,
#             "tax_amount": 0.0,
#             "tax_rate": 0.0,
#             "grand_total": 0.0
#         },
#         "line_items": extract_line_items_from_email(body)
#     }

# def extract_company_name_from_email(subject, body):
#     """Extract company name from email content."""
#     import re
#     
#     # Look for company names in subject and body
#     text = f"{subject} {body}"
#     
#     # Common patterns for company names in PO emails
#     patterns = [
#         r'(?:from|company|customer):\s*([A-Z][A-Za-z\s&,.-]+(?:Inc|Corp|LLC|Ltd|Company|Co\.?))',
#         r'^([A-Z][A-Za-z\s&,.-]+(?:Inc|Corp|LLC|Ltd|Company|Co\.?))',
#         r'Purchase Order from ([A-Z][A-Za-z\s&,.-]+)',
#     ]
#     
#     for pattern in patterns:
#         match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
#         if match:
#             return match.group(1).strip()
#     
#     return ""

# def extract_po_number_from_email(subject, body):
#     """Extract PO number from email content."""
#     import re
#     
#     text = f"{subject} {body}"
#     
#     # Common PO number patterns
#     patterns = [
#         r'PO[#\s]*:?\s*([A-Z0-9-]+)',
#         r'Purchase Order[#\s]*:?\s*([A-Z0-9-]+)',
#         r'Order[#\s]*:?\s*([A-Z0-9-]+)',
#         r'P\.O\.\s*#?\s*([A-Z0-9-]+)',
#     ]
#     
#     for pattern in patterns:
#         match = re.search(pattern, text, re.IGNORECASE)
#         if match:
#             return match.group(1).strip()
#     
#     return ""

# def extract_line_items_from_email(body):
#     """Extract line items from email body."""
#     # This is a simplified extraction - in reality you'd use AI to parse structured data
#     # For now, return empty list - the real processing would happen in the attachment
#     return []

@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'components': {
            'file_handler': 'ok',
            'document_processor': 'ok',
            'database_manager': 'ok',
            'part_mapper': 'ok'
        }
    })

@app.route('/api/get_processed_email')
def get_processed_email():
    """Get processed JSON data for an email (for Outlook add-in review UI)."""
    try:
        email_id = request.args.get('email_id')
        subject = request.args.get('subject')
        attachment_name = request.args.get('attachment_name')
        
        if not email_id and not subject and not attachment_name:
            return jsonify({'success': False, 'error': 'Email ID, subject, or attachment name required'}), 400
        
        # Search for processed file
        processed_files = metrics_db.get_all_processing_results()
        
        if not processed_files or len(processed_files) == 0:
            return jsonify({'success': False, 'error': 'No processed files found in database'}), 404
        
        matching_file = None
        
        # Convert ProcessingResult objects to dicts if needed
        files_list = []
        for file in processed_files:
            if hasattr(file, '__dict__'):
                files_list.append(file.__dict__)
            else:
                files_list.append(file)
        
        # Try to match by attachment name first (most reliable)
        matching_file = None
        if attachment_name:
            for file in files_list:
                original_name = file.get('original_filename', '').lower()
                # Remove extension and timestamp from both for comparison
                search_name = attachment_name.lower().replace('.pdf', '').replace('.doc', '').replace('.docx', '')
                if search_name in original_name:
                    matching_file = file
                    break
        
        # If not found by attachment, get most recent
        if not matching_file:
            files_sorted = sorted(files_list, key=lambda x: x.get('id', 0), reverse=True)
            matching_file = files_sorted[0]
        
        # Get the file ID for future updates
        file_id = matching_file.get('id', 0)
        
        # Get the raw JSON data
        raw_json = matching_file.get('raw_json_data')
        if raw_json:
            try:
                data = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
                return jsonify({'success': True, 'data': data, 'file_id': file_id})
            except:
                pass
        
        # Fallback: try to load from processed file
        processed_path = matching_file.get('processed_file_path')
        if processed_path and os.path.exists(processed_path):
            with open(processed_path, 'r') as f:
                data = json.load(f)
                return jsonify({'success': True, 'data': data, 'file_id': file_id})
        
        return jsonify({'success': False, 'error': 'Processed data not available'}), 404
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/save_updated_data', methods=['POST'])
def save_updated_data():
    """Save updated data from Outlook add-in back to the database and file."""
    try:
        data = request.get_json()
        email_id = data.get('email_id')
        subject = data.get('subject')
        attachment_name = data.get('attachment_name')
        updated_data = data.get('updated_data')
        
        if not updated_data:
            return jsonify({'success': False, 'error': 'No updated data provided'}), 400
        
        # Find the matching processed file
        processed_files = metrics_db.get_all_processing_results()
        files_list = []
        for file in processed_files:
            if hasattr(file, '__dict__'):
                files_list.append(file.__dict__)
            else:
                files_list.append(file)
        
        matching_file = None
        if attachment_name:
            for file in files_list:
                original_name = file.get('original_filename', '').lower()
                search_name = attachment_name.lower().replace('.pdf', '').replace('.doc', '').replace('.docx', '')
                if search_name in original_name:
                    matching_file = file
                    break
        
        if not matching_file:
            return jsonify({'success': False, 'error': 'No matching processed file found'}), 404
        
        file_id = matching_file.get('id', 0)
        
        # Update the raw JSON data in the database
        updated_json_str = json.dumps(updated_data)
        success = metrics_db.update_raw_json_data(file_id, updated_json_str)
        
        if not success:
            return jsonify({'success': False, 'error': 'Failed to update database'}), 500
        
        # Update validation status to "correct" since the order was approved
        print(f"Updating validation status for file {file_id} to 'correct'")
        status_success = metrics_db.update_validation_status(file_id, "correct")
        
        if not status_success:
            print(f"Warning: Failed to update validation status for file {file_id}")
        else:
            print(f"Successfully updated validation status for file {file_id}")
        
        # Also update the processed file if it exists
        processed_path = matching_file.get('processed_file_path')
        if processed_path and os.path.exists(processed_path):
            with open(processed_path, 'w') as f:
                json.dump(updated_data, f, indent=2)
        
        return jsonify({'success': True, 'message': 'Data updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_customer_by_account', methods=['GET'])
def get_customer_by_account():
    """Get customer information by account number."""
    try:
        account_number = request.args.get('account_number')
        
        if not account_number:
            return jsonify({'error': 'Account number is required'}), 400
        
        # Look up customer in the database
        customer = db_manager.find_customer_by_account_number(account_number)
        
        if customer:
            return jsonify({
                'success': True,
                'customer': {
                    'company_name': customer.company_name,
                    'account_number': customer.account_number,
                    'address': customer.address,
                    'state': customer.state
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': f'No customer found with account number {account_number}'
            })
            
    except Exception as e:
        print(f"Error looking up customer: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/report_error', methods=['POST'])
def report_error():
    """Report an error with a processed order."""
    try:
        data = request.get_json()
        email_id = data.get('email_id')
        subject = data.get('subject')
        error_type = data.get('error_type')
        notes = data.get('notes', '')
        attachment_name = data.get('attachment_name', '')
        
        if not error_type:
            return jsonify({'success': False, 'error': 'Error type required'}), 400
        
        # Find the file in database
        processed_files = metrics_db.get_all_processing_results()
        files_list = []
        for file in processed_files:
            if hasattr(file, '__dict__'):
                files_list.append(file.__dict__)
            else:
                files_list.append(file)
        
        matching_file = None
        if attachment_name:
            for file in files_list:
                original_name = file.get('original_filename', '').lower()
                search_name = attachment_name.lower().replace('.pdf', '').replace('.doc', '').replace('.docx', '')
                if search_name in original_name:
                    matching_file = file
                    break
        
        if not matching_file and files_list:
            # Get most recent
            files_sorted = sorted(files_list, key=lambda x: x.get('id', 0), reverse=True)
            matching_file = files_sorted[0]
        
        file_id = matching_file.get('id') if matching_file else None
        
        # Map error_type to ErrorType enum
        error_type_map = {
            'wrong_customer': ErrorType.ACCOUNT_NUMBER,
            'wrong_parts': ErrorType.PART_NUMBER,
            'wrong_pricing': ErrorType.PRICING_ERROR,
            'wrong_address': ErrorType.SHIPPING_ADDRESS,
            'wrong_method': ErrorType.OTHER,
            'wrong_PO': ErrorType.OTHER,
            'other': ErrorType.OTHER
        }
        
        error_enum = error_type_map.get(error_type, ErrorType.OTHER)
        
        # Update database
        if file_id:
            metrics_db.update_processing_result(
                file_id,
                validation_status=ValidationStatus.CONTAINS_ERROR,
                notes=f"Error: {error_type}. {notes}" if notes else f"Error: {error_type}"
            )
            
            # Add error type to the file
            metrics_db.add_error_type(file_id, error_enum)
        
        # Save error report to logs
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        error_report = {
            'timestamp': timestamp,
            'file_id': file_id,
            'email_id': email_id,
            'subject': subject,
            'error_type': error_type,
            'notes': notes
        }
        
        error_filename = f"error_report_{timestamp}.json"
        error_path = os.path.join('logs', error_filename)
        os.makedirs('logs', exist_ok=True)
        
        with open(error_path, 'w') as f:
            json.dump(error_report, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Error reported and database updated',
            'report_id': timestamp
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Purchase Order Processing Web App...")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Processed folder: {app.config['PROCESSED_FOLDER']}")
    
    # Print database stats
    stats = db_manager.get_database_stats()
    print(f"Parts database: {stats['parts_count']} parts")
    print(f"Customers database: {stats['customers_count']} customers")
    
    # Get port from environment variable (for AWS deployment)
    port = int(os.environ.get('PORT', 5000))
    
    # Check if SSL certificates exist (local development only)
    if os.path.exists('flask_cert.pem') and os.path.exists('flask_key.pem'):
        print("\n🔐 Starting with HTTPS (SSL certificates found)")
        print("Access the app at: https://127.0.0.1:5000")
        app.run(debug=True, host='127.0.0.1', port=5000, ssl_context=('flask_cert.pem', 'flask_key.pem'))
    else:
        print(f"\n🌐 Starting Flask server on port {port}")
        print(f"Access the app at: http://0.0.0.0:{port}")
        # Use gunicorn for production (AWS App Runner)
        if os.environ.get('FLASK_ENV') == 'production':
            # App Runner will handle this via gunicorn
            app.run(debug=False, host='0.0.0.0', port=port)
        else:
            app.run(debug=False, host='0.0.0.0', port=port)

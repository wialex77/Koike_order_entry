-- Create processing_results table
CREATE TABLE IF NOT EXISTS processing_results (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    processing_status TEXT NOT NULL CHECK (processing_status IN ('pending', 'processing', 'completed', 'error')),
    validation_status TEXT NOT NULL DEFAULT 'pending_review' CHECK (validation_status IN ('correct', 'contains_error', 'pending_review')),
    processing_start_time TIMESTAMP NOT NULL,
    processing_end_time TIMESTAMP,
    processing_duration REAL,
    total_parts INTEGER DEFAULT 0,
    parts_mapped INTEGER DEFAULT 0,
    parts_not_found INTEGER DEFAULT 0,
    parts_manual_review INTEGER DEFAULT 0,
    mapping_success_rate REAL DEFAULT 0.0,
    customer_matched BOOLEAN DEFAULT FALSE,
    customer_match_confidence REAL DEFAULT 0.0,
    error_types TEXT DEFAULT '[]',
    error_details TEXT,
    manual_corrections_made INTEGER DEFAULT 0,
    epicor_ready BOOLEAN DEFAULT FALSE,
    epicor_ready_with_one_click BOOLEAN DEFAULT FALSE,
    missing_info_count INTEGER DEFAULT 0,
    processed_file_path TEXT,
    epicor_json_path TEXT,
    raw_json_data TEXT NOT NULL DEFAULT '{}',
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_processing_status ON processing_results(processing_status);
CREATE INDEX IF NOT EXISTS idx_validation_status ON processing_results(validation_status);
CREATE INDEX IF NOT EXISTS idx_created_at ON processing_results(created_at);
CREATE INDEX IF NOT EXISTS idx_epicor_ready ON processing_results(epicor_ready);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_processing_results_updated_at 
    BEFORE UPDATE ON processing_results 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

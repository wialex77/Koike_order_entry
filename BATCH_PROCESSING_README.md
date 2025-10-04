# Batch PO Processing Script

This script randomly selects 5 Purchase Orders from the `samplePOs` folder and processes them in parallel using the Flask app, then exports their Epicor-formatted JSON to the `batch_results` folder.

## Setup

1. **Install additional dependencies:**
   ```bash
   pip install -r batch_requirements.txt
   ```

2. **Make sure the Flask app is running:**
   ```bash
   python app.py
   ```
   The app should be running on `http://127.0.0.1:5000`

## Usage

1. **Run the batch processing script:**
   ```bash
   python batch_process_sample_pos.py
   ```

2. **Check the results:**
   - Individual Epicor JSON files: `batch_results/[PO_NAME]_epicor_[TIMESTAMP].json`
   - Summary report: `batch_results/batch_processing_summary_[TIMESTAMP].json`

## Output Structure

### Individual Epicor JSON Files
Each processed PO gets its own Epicor-formatted JSON file:
```json
{
  "ds": {
    "OrderHed": [...],
    "OrderDtl": [...]
  },
  "continueProcessingOnError": true,
  "rollbackParentOnChildError": true
}
```

### Summary Report
Contains processing statistics and results for all files:
```json
{
  "timestamp": "20250918_143022",
  "total_files": 5,
  "successful": 4,
  "failed": 1,
  "results": [...]
}
```

## Features

- **Parallel Processing**: Processes up to 3 POs simultaneously to avoid overwhelming the server
- **Random Selection**: Randomly selects 5 POs from available sample files
- **Error Handling**: Continues processing even if some files fail
- **Detailed Logging**: Shows progress and results for each file
- **Timestamped Output**: All files include timestamps to avoid conflicts

## Troubleshooting

- **Connection Errors**: Make sure the Flask app is running on port 5000
- **File Not Found**: Ensure `samplePOs` folder contains PDF files
- **Processing Failures**: Check the summary report for specific error messages
- **Timeout Issues**: The script has a 5-minute timeout per file; increase if needed

## Customization

You can modify the script to:
- Change the number of files to process (modify `count=5` in `main()`)
- Adjust concurrent processing limit (modify `Semaphore(3)`)
- Change timeout settings (modify `ClientTimeout(total=300)`)
- Process specific files instead of random selection

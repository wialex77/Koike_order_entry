# Purchase Order Processing Web App

A comprehensive web application that processes purchase order documents using OCR/AI technology and maps external part numbers to internal ones using database lookups.

## Features

- **File Upload**: Supports PDF, Word, and image files
- **OCR/AI Processing**: Automatically extracts company info and line items
- **Database Mapping**: Maps external part numbers to internal ones using fuzzy matching
- **Customer Lookup**: Finds account numbers based on company names
- **Web Interface**: Modern, responsive web UI
- **Processing History**: View and download previously processed orders
- **Database Management**: Add and manage parts and customers

## Architecture

The application is built with a modular architecture:

1. **Step 1 (`step1_upload.py`)**: File upload and validation
2. **Step 2 (`step2_ocr_ai.py`)**: OCR/AI document processing
3. **Step 3 (`step3_databases.py`)**: Database management for parts and customers
4. **Step 4 (`step4_mapping.py`)**: Part number mapping and account lookup
5. **Main App (`app.py`)**: Flask web interface integrating all steps

## Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Tesseract OCR (for image processing)
- OpenAI API key (for AI processing)

### 2. Install Tesseract OCR

#### Windows:
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install and add to PATH

#### macOS:
```bash
brew install tesseract
```

#### Linux (Ubuntu/Debian):
```bash
sudo apt-get install tesseract-ocr
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configuration

1. Get an OpenAI API key from: https://platform.openai.com/api-keys

2. Create a `.env` file in the project root (or set environment variables):
```
OPENAI_API_KEY=your_openai_api_key_here
MAX_FILE_SIZE=16777216
UPLOAD_FOLDER=uploads
PARTS_DB_PATH=data/parts.csv
CUSTOMERS_DB_PATH=data/customer_list.xlsx
```

### 5. Database Setup

The application uses CSV files as databases. Sample databases are included:

- `data/parts.csv`: Contains internal part numbers and descriptions
- `data/customer_list.xlsx`: Contains company names and Epicor account numbers

You can modify these files or add new entries through the web interface.

### 6. Run the Application

```bash
python app.py
```

The application will be available at: http://127.0.0.1:5000

## Usage

### Upload and Process Purchase Orders

1. Navigate to the main page
2. Upload a PDF, Word document, or image file containing a purchase order
3. The system will:
   - Extract text using OCR (for images) or direct text extraction
   - Use AI to identify company information and line items
   - Map external part numbers to internal ones using the parts database
   - Look up customer account numbers using the customers database
4. Review the results and download the processed JSON file

### Manage Databases

1. Go to the "Databases" page
2. View existing parts and customers
3. Add new parts or customers using the forms
4. The system uses fuzzy matching for lookups, so exact matches aren't required

### View Processing History

1. Go to the "History" page
2. View all previously processed purchase orders
3. Preview or download any processed file

## File Structure

```
Koike/
├── app.py                 # Main Flask application
├── step1_upload.py        # File upload handler
├── step2_ocr_ai.py       # OCR/AI processing
├── step3_databases.py    # Database management
├── step4_mapping.py      # Part mapping and lookup
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── data/                # Database files
│   ├── parts.csv        # Parts database
│   └── customer_list.xlsx    # Customers database
├── templates/           # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── databases.html
│   └── history.html
├── uploads/             # Temporary upload folder
└── processed/           # Processed JSON files
```

## API Endpoints

- `POST /upload` - Upload and process a purchase order
- `GET /download/<filename>` - Download processed JSON file
- `GET /api/databases/stats` - Get database statistics
- `GET /api/databases/parts` - Get all parts
- `GET /api/databases/customers` - Get all customers
- `POST /api/databases/parts` - Add new part
- `POST /api/databases/customers` - Add new customer
- `GET /api/health` - Health check

## Output Format

The processed JSON contains:

```json
{
  "company_info": {
    "company_name": "string",
    "address": "string",
    "email": "string",
    "phone_number": "string",
    "contact_person": "string",
    "contact_person_email": "string",
    "account_number": "string",
    "customer_match_confidence": float,
    "customer_match_status": "matched|not_found|manual_review"
  },
  "line_items": [
    {
      "external_part_number": "string",
      "internal_part_number": "string",
      "description": "string",
      "unit_price": float,
      "quantity": integer,
      "mapping_confidence": float,
      "mapping_status": "mapped|not_found|manual_review"
    }
  ],
  "processing_summary": {
    "total_parts": integer,
    "parts_mapped": integer,
    "parts_not_found": integer,
    "parts_manual_review": integer,
    "mapping_success_rate": float,
    "customer_matched": boolean,
    "requires_manual_review": boolean
  }
}
```

## Troubleshooting

### Common Issues

1. **"No module named 'pytesseract'"**
   - Make sure Tesseract is installed and in PATH
   - Reinstall pytesseract: `pip install pytesseract`

2. **"OpenAI API key not found"**
   - Set the OPENAI_API_KEY environment variable
   - Create a `.env` file with your API key

3. **"File upload failed"**
   - Check file size (max 16MB)
   - Ensure file type is supported
   - Check disk space

4. **"Database not found"**
   - Make sure `data/parts.csv` and `data/customer_list.xlsx` exist
   - Check file permissions

### Performance Tips

- For better OCR results, use high-resolution, clear images
- PDF files with selectable text process faster than scanned images
- Larger databases may slow down fuzzy matching

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve the application.

## License

This project is provided as-is for educational and commercial use.

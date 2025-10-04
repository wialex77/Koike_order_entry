# Outlook Add-in for Purchase Order Processing

This Outlook add-in automatically detects Purchase Order emails, processes them using your existing Flask backend, and provides a user interface to review and edit the JSON payload before entering orders into Epicor.

## Features

- **Automatic PO Detection**: Analyzes email content, subject lines, and attachments to identify Purchase Order emails
- **Smart Processing**: Uses your existing OCR/AI processing pipeline to extract structured data
- **JSON Payload Editor**: Allows editing of the Epicor JSON payload before order entry
- **Validation**: Validates customer and part mappings before allowing order entry
- **One-Click Order Entry**: "Enter Order" button to submit the processed data to Epicor

## Files Created

1. **`manifest.xml`** - Outlook add-in manifest file
2. **`taskpane.html`** - Main user interface for the add-in
3. **`outlook_addin_server.py`** - Simple web server to host the add-in files
4. **Updated `app.py`** - Added `/api/process-email` endpoint for processing email data

## Setup Instructions

### Prerequisites

1. **SSL Certificate**: Outlook add-ins require HTTPS. You'll need SSL certificates.
2. **Flask Backend**: Your existing Flask application must be running on port 5000
3. **Outlook**: Outlook 2016 or later, or Outlook on the web

### Step 1: Generate SSL Certificates (Development)

For development, generate self-signed certificates:

```bash
# Generate self-signed certificate for the add-in server
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Generate self-signed certificate for the Flask backend (if not already done)
openssl req -x509 -newkey rsa:4096 -keyout flask_key.pem -out flask_cert.pem -days 365 -nodes
```

### Step 2: Update Flask Backend for HTTPS

Update your Flask app to use HTTPS:

```python
# In app.py, change the last line from:
app.run(debug=True, host='127.0.0.1', port=5000)

# To:
app.run(debug=True, host='127.0.0.1', port=5000, ssl_context=('flask_cert.pem', 'flask_key.pem'))
```

### Step 3: Install Add-in Server Dependencies

```bash
pip install flask flask-cors
```

### Step 4: Start the Servers

1. **Start your Flask backend** (port 5000):
```bash
python app.py
```

2. **Start the Outlook add-in server** (port 3000):
```bash
python outlook_addin_server.py
```

### Step 5: Install the Outlook Add-in

#### Method 1: Sideloading (Development)

1. **Copy the manifest file**:
   - Copy `manifest.xml` to a web-accessible location (e.g., `https://localhost:3000/manifest.xml`)

2. **Sideload in Outlook Desktop**:
   - Open Outlook
   - Go to File > Get Add-ins
   - Click "Add a custom add-in" > "Add from file"
   - Browse to your `manifest.xml` file

3. **Sideload in Outlook on the web**:
   - Go to Outlook on the web
   - Click the gear icon > Get Add-ins
   - Click "Upload My Add-in"
   - Upload your `manifest.xml` file

#### Method 2: Centralized Deployment (Production)

For production, you'll need to:
1. Upload the manifest to your organization's app catalog
2. Deploy through Office 365 admin center

### Step 6: Test the Add-in

1. **Open an email** that looks like a Purchase Order
2. **Look for the "PO Processor" button** in the message ribbon
3. **Click "Process PO"** to open the task pane
4. **Review the detected signals** and processing results
5. **Edit the JSON payload** if needed
6. **Click "Enter Order"** to submit to Epicor

## How It Works

### 1. Email Analysis
The add-in analyzes incoming emails for PO signals:
- **Subject Keywords**: "Purchase Order", "PO Number", "Order Confirmation"
- **Body Content**: PO-related terms, structured data (prices, quantities, part numbers)
- **Attachments**: PDF files (common for POs)
- **Confidence Scoring**: Combines multiple signals for accurate detection

### 2. Data Processing
When a PO is detected:
- Email content and attachments are sent to your Flask backend
- Your existing `DocumentProcessor` and `PartNumberMapper` classes process the data
- Customer and part mappings are applied using your databases
- Epicor JSON payload is generated

### 3. User Interface
The task pane displays:
- **Detection Status**: Shows confidence level and detected signals
- **Company Information**: Customer details, PO number, account mapping
- **Line Items**: Part numbers, descriptions, quantities, prices
- **Validation Status**: Whether data is ready for order entry
- **JSON Editor**: Editable Epicor payload with validation

### 4. Order Entry
- User can edit the JSON payload before submission
- Validation ensures all required fields are present
- "Enter Order" button submits to your Epicor system

## Configuration

### Backend API Endpoint
The add-in calls your Flask backend at:
```
POST https://localhost:5000/api/process-email
```

Request payload:
```json
{
  "subject": "Purchase Order #12345",
  "body": "Email body content...",
  "attachments": [
    {
      "name": "PO-12345.pdf",
      "contentType": "application/pdf"
    }
  ]
}
```

### Manifest Customization
Update `manifest.xml` for your organization:
- Change the `<Id>` GUID to a unique identifier
- Update `<ProviderName>` to your company name
- Modify `<SupportUrl>` to your support page
- Adjust icon URLs if you have custom icons

## Troubleshooting

### Common Issues

1. **"Add-in not loading"**
   - Check that both servers are running (ports 3000 and 5000)
   - Verify SSL certificates are valid
   - Check browser console for errors

2. **"PO not detected"**
   - Check email content for PO keywords
   - Verify attachment is a PDF
   - Review detection signals in the task pane

3. **"Backend API error"**
   - Ensure Flask backend is running on port 5000
   - Check Flask logs for processing errors
   - Verify database connections

4. **"SSL Certificate errors"**
   - Accept self-signed certificates in browser
   - For production, use proper SSL certificates
   - Update manifest URLs to match your domain

### Debug Mode

Enable debug logging in the task pane:
```javascript
// In taskpane.html, add to console.log statements
console.log('Debug info:', data);
```

### Browser Developer Tools

1. Open Outlook on the web
2. Press F12 to open developer tools
3. Check Console tab for JavaScript errors
4. Check Network tab for API call failures

## Security Considerations

1. **HTTPS Required**: All communication must use HTTPS
2. **CORS Configuration**: Backend must allow requests from Outlook
3. **API Authentication**: Consider adding API keys for production
4. **Data Privacy**: Email content is processed by your backend

## Production Deployment

For production deployment:

1. **Use proper SSL certificates** from a trusted CA
2. **Deploy to a production server** instead of localhost
3. **Update manifest URLs** to your production domain
4. **Add authentication** to the backend API
5. **Deploy through Office 365 admin center**
6. **Monitor usage and performance**

## Support

For issues or questions:
1. Check the Flask backend logs
2. Review browser developer console
3. Verify all servers are running
4. Test with sample PO emails

## Future Enhancements

Potential improvements:
- **Batch Processing**: Process multiple PO emails at once
- **Template Matching**: Learn from previously processed POs
- **Notification System**: Email alerts for processing results
- **Audit Trail**: Track all processed orders
- **Advanced Validation**: More sophisticated data validation rules

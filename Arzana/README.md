# Arzana Order Processor - Outlook Add-in

This Outlook add-in integrates your existing order processing system directly into Outlook, allowing users to process purchase orders from email attachments without leaving their inbox.

## Features

- **Email Attachment Detection**: Automatically detects PDF, Word, and image files that appear to be purchase orders
- **Email Content Analysis**: Analyzes email body text for purchase order information
- **AI-Powered Processing**: Uses your existing Python backend for document OCR and data extraction
- **Part Number Mapping**: Leverages your part number mapping system with fuzzy matching
- **Customer Lookup**: Integrates with your customer database for account number matching
- **Manual Review Interface**: Provides UI for reviewing and correcting mappings
- **Epicor Export**: Generates properly formatted JSON for Epicor import

## Architecture

The add-in consists of:

- **Frontend (TypeScript/HTML)**: Outlook task pane interface
- **Backend Integration**: Calls your existing Python Flask API
- **Data Flow**: Email → Attachment → Python Processing → UI Display → Epicor JSON

## Setup Instructions

### 1. Install Dependencies

```bash
cd Arzana
npm install
```

### 2. Start Development Server

```bash
npm start
```

This will:
- Start the HTTPS development server on port 3000
- Open Outlook with the add-in loaded
- Enable hot reloading for development

### 3. Test the Add-in

1. Open Outlook (web or desktop)
2. Open an email with a purchase order attachment
3. Look for the "Arzana Order Processor" group in the ribbon
4. Click "Process PO" to open the task pane
5. Click "Process Purchase Order" to analyze the attachment

## Integration with Existing System

### Backend Connection

The add-in currently uses simulated data for demonstration. To connect to your existing Python backend:

1. **Update API Endpoints**: Modify the `simulateProcessing()` function in `src/taskpane/taskpane.ts` to call your actual Flask API
2. **Handle File Uploads**: Implement proper file transfer from Outlook attachments to your backend
3. **Authentication**: Add any required authentication for your API

### Example Integration

```typescript
// Replace simulateProcessing() with actual API call
async function processAttachment(attachmentId: string) {
  const formData = new FormData();
  formData.append('file', attachmentData);
  
  const response = await fetch('https://your-backend.com/upload', {
    method: 'POST',
    body: formData
  });
  
  const result = await response.json();
  // Process results...
}
```

## File Structure

```
Arzana/
├── src/
│   ├── taskpane/
│   │   ├── taskpane.html      # Main UI
│   │   └── taskpane.ts        # Outlook API integration
│   └── commands/
│       ├── commands.html      # Command functions
│       └── commands.ts        # Button actions
├── assets/                    # Icons and images
├── manifest.xml              # Outlook add-in configuration
├── package.json              # Dependencies
└── webpack.config.js         # Build configuration
```

## Development

### Building for Production

```bash
npm run build
```

### Validating Manifest

```bash
npm run validate
```

### Linting

```bash
npm run lint
```

## Deployment

### For Testing (Sideload)

1. Run `npm start` in development
2. The add-in will be automatically sideloaded to your Outlook account
3. Test with your email account

### For Production

1. Build the add-in: `npm run build`
2. Deploy the built files to a web server with HTTPS
3. Update `manifest.xml` with your production URLs
4. Submit to Microsoft AppSource for distribution

## Troubleshooting

### Common Issues

1. **Add-in not appearing**: Check that Outlook is signed in with the correct account
2. **HTTPS errors**: Ensure your development server is running with valid SSL certificates
3. **API connection issues**: Verify your backend is running and accessible

### Debug Mode

Enable debug mode by opening browser developer tools when the add-in is running.

## Next Steps

1. **Connect to Backend**: Replace simulation functions with actual API calls
2. **Handle File Uploads**: Implement proper attachment processing
3. **Add Authentication**: Secure your API endpoints
4. **Test with Real Data**: Process actual purchase orders
5. **Deploy to Production**: Make available to your team

## Support

For issues or questions:
- Check the browser console for error messages
- Verify your Python backend is running
- Ensure all dependencies are installed
- Review the Outlook add-in documentation

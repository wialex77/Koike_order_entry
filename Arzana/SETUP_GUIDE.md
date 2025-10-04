# Arzana Outlook Add-in Setup Guide

## ✅ **Integration Complete!**

Your Outlook add-in is now fully connected to your existing Flask server. Here's how to set it up and test it:

## **Prerequisites**

1. **Your Flask server must be running** at `http://127.0.0.1:5000`
2. **Install flask-cors** in your Python environment
3. **Node.js and npm** installed

## **Step 1: Install Flask-CORS**

In your main project directory (where `app.py` is located):

```bash
pip install flask-cors>=4.0.0
```

Or add it to your requirements.txt (already done):
```bash
pip install -r requirements.txt
```

## **Step 2: Start Your Flask Server**

In your main project directory:
```bash
python app.py
```

Your Flask server should start at `http://127.0.0.1:5000`

## **Step 3: Start the Outlook Add-in**

In the Arzana directory:
```bash
cd Arzana
npm start
```

This will:
- Start the HTTPS development server on port 3000
- Automatically open Outlook with the add-in loaded
- Enable hot reloading for development

## **Step 4: Test the Integration**

### **Test with Email Attachment:**

1. **Open Outlook** (web or desktop)
2. **Create a test email** with a PDF attachment that looks like a purchase order
3. **Open the email** in reading mode
4. **Look for "Arzana Order Processor"** in the ribbon
5. **Click "Process PO"** to open the task pane
6. **Click "Process Purchase Order"** to analyze the attachment

### **Test with Email Content:**

1. **Create an email** with PO-related text in the body
2. **Open the email**
3. **Click "Process PO"** 
4. **Click "Process Email Content"** to analyze the text

## **How It Works**

### **Data Flow:**
1. **Outlook Add-in** detects PO attachments or content
2. **Downloads attachment** from Outlook
3. **Sends to Flask server** at `/upload` endpoint
4. **Flask processes** using your existing pipeline:
   - OCR/AI analysis
   - Part number mapping
   - Customer lookup
   - Epicor JSON generation
5. **Results return** to Outlook add-in
6. **User can download** Epicor JSON format

### **API Endpoints Used:**
- `POST /upload` - Process attachment
- `GET /download/<filename>` - Download Epicor JSON
- `POST /api/update-customer/<filename>` - Update customer mapping
- `POST /api/update-part/<filename>` - Update part mapping

## **Features Working:**

✅ **Email Attachment Detection** - Automatically finds PO files  
✅ **Email Content Analysis** - Detects PO-related text  
✅ **Real-time Processing** - Uses your existing Python backend  
✅ **Part Number Mapping** - Leverages your fuzzy matching system  
✅ **Customer Lookup** - Integrates with your customer database  
✅ **Manual Review Interface** - Allows corrections in Outlook  
✅ **Epicor Export** - Downloads properly formatted JSON  
✅ **Progress Tracking** - Shows real-time processing status  

## **Troubleshooting**

### **Add-in Not Appearing:**
- Make sure you're signed into the correct Outlook account
- Check that `npm start` completed successfully
- Try refreshing the Outlook page

### **Processing Errors:**
- Verify your Flask server is running at `http://127.0.0.1:5000`
- Check browser console for CORS errors
- Ensure flask-cors is installed and configured

### **File Upload Issues:**
- Check that attachment is a supported format (PDF, DOC, DOCX, images)
- Verify file size is under 16MB
- Ensure attachment has PO-related filename or content

## **Development Mode**

While developing:
- **Flask server**: `python app.py` (runs on port 5000)
- **Add-in server**: `npm start` (runs on port 3000)
- **Hot reloading**: Enabled for both servers

## **Production Deployment**

When ready for production:

1. **Build the add-in**: `npm run build`
2. **Deploy to web server** with HTTPS
3. **Update manifest.xml** with production URLs
4. **Configure CORS** for production domain
5. **Submit to Microsoft AppSource**

## **Next Steps**

1. **Test with real PO attachments** from your customers
2. **Verify all mapping accuracy** with your existing data
3. **Train your team** on the new Outlook workflow
4. **Monitor processing success rates** and accuracy
5. **Deploy to production** when ready

## **Support**

If you encounter issues:
- Check the browser console for error messages
- Verify both servers are running
- Test your Flask API directly with Postman/curl
- Review the README.md for additional details

**Your Outlook add-in is now fully integrated with your existing order processing system!** 🎉

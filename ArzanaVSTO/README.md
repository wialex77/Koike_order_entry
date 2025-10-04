# Arzana VSTO Add-in

This is a VSTO (Visual Studio Tools for Office) add-in for Outlook that automatically processes purchase order emails using the NewMailEx event.

## Features

- **Automatic Email Processing**: Uses NewMailEx event to process emails as they arrive
- **PO Detection**: Advanced AI-powered detection of purchase order emails
- **Email Tagging**: Automatically tags emails based on processing results
- **Flask Integration**: Connects to your existing Flask processing server
- **Real-time Processing**: Processes emails immediately when they arrive

## Email Tags

The add-in will automatically tag emails with the following categories:

- **Arzana-Ready**: Customer matched and parts mapped successfully
- **Arzana-CustomerMatched**: Customer found but parts need review
- **Arzana-NeedsReview**: Customer needs manual review
- **Arzana-MissingInfo**: Missing required information
- **Arzana-Error**: Processing error occurred
- **Arzana-Processing**: Currently being processed

## Prerequisites

- Visual Studio 2019 or later with Office development tools
- .NET Framework 4.8
- Microsoft Outlook 2016 or later
- Your Flask server running on http://127.0.0.1:5000

## Building the Add-in

1. Open `ArzanaVSTO.csproj` in Visual Studio
2. Build the solution (Ctrl+Shift+B)
3. The add-in will be compiled to `bin\Debug\ArzanaVSTO.dll`

## Installation

### Method 1: Visual Studio (Recommended)
1. Right-click the project in Visual Studio
2. Select "Publish"
3. Follow the publish wizard
4. Run the generated installer

### Method 2: Manual Installation
1. Copy the compiled files to a permanent location
2. Run the VSTO installer as administrator
3. The add-in will be registered with Outlook

## Configuration

The add-in connects to your Flask server at `http://127.0.0.1:5000`. To change this:

1. Edit `POProcessor.cs`
2. Modify the `flaskServerUrl` variable
3. Rebuild the project

## Troubleshooting

### Add-in Not Loading
- Ensure Outlook is running as administrator
- Check that .NET Framework 4.8 is installed
- Verify the add-in is registered in Outlook's COM Add-ins

### Processing Not Working
- Ensure your Flask server is running on port 5000
- Check the debug output in Visual Studio's Output window
- Verify the email contains PO-related content

### Debug Output
To see debug messages:
1. Open Visual Studio
2. Go to View → Output
3. Select "Debug" from the dropdown
4. Look for "Arzana VSTO" messages

## How It Works

1. **Email Arrives**: NewMailEx event fires for every new email
2. **PO Detection**: EmailDetector analyzes subject, body, and attachments
3. **Processing**: If PO detected, sends to Flask server for AI processing
4. **Tagging**: Updates email categories based on processing results
5. **Logging**: All actions are logged to debug output

## Limitations

- **Desktop Only**: Works only in Outlook desktop application
- **Windows Only**: Requires Windows and .NET Framework
- **Per-Machine**: Must be installed on each computer
- **VSTO Deprecation**: Microsoft is deprecating VSTO (but still supported)

## Support

For issues or questions:
1. Check the debug output in Visual Studio
2. Ensure your Flask server is running and accessible
3. Verify the email content matches PO detection criteria

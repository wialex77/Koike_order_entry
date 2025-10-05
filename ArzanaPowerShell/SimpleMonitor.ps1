# Simple Outlook Monitor - Alternative Approach
# This version uses a different method to access Outlook

param(
    [string]$FlaskServerUrl = "https://bx3w2xz6f6.us-east-1.awsapprunner.com",
    [int]$CheckIntervalSeconds = 60
)

# Logging function
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Host $logMessage
}

Write-Log "Starting Simple Outlook Monitor..."
Write-Log "Flask Server: $FlaskServerUrl"
Write-Log "Check Interval: $CheckIntervalSeconds seconds"

# Check if Outlook is running
$outlookProcess = Get-Process -Name "OUTLOOK" -ErrorAction SilentlyContinue
if ($outlookProcess) {
    Write-Log "Outlook is running (PID: $($outlookProcess.Id))"
} else {
    Write-Log "Outlook is not running. Please start Outlook first." "ERROR"
    Write-Log "Opening Outlook..."
    Start-Process "outlook.exe"
    Start-Sleep -Seconds 15
}

# Try to connect to Outlook using a different method
try {
    Write-Log "Attempting to connect to Outlook..."
    
    # Add Outlook COM type
    Add-Type -AssemblyName "Microsoft.Office.Interop.Outlook"
    
    # Try to get existing Outlook instance
    $outlook = [System.Runtime.InteropServices.Marshal]::GetActiveObject("Outlook.Application")
    Write-Log "Successfully connected to Outlook!"
    
    # Get inbox
    $namespace = $outlook.GetNamespace("MAPI")
    $inbox = $namespace.GetDefaultFolder(6) # 6 = olFolderInbox
    Write-Log "Connected to Inbox. Starting monitoring..."
    
    $processedEmails = @{}
    $lastCheckTime = Get-Date
    
    while ($true) {
        try {
            Write-Log "Checking for new emails..."
            
            # Get recent emails (last 5 minutes)
            $emails = $inbox.Items | Where-Object { 
                $_.ReceivedTime -gt $lastCheckTime -and 
                ($_.Subject -like "*PO*" -or $_.Subject -like "*Purchase Order*" -or $_.Subject -like "*Order*") -and
                $_.Attachments.Count -gt 0
            }
            
            foreach ($email in $emails) {
                $emailId = $email.EntryID
                if ($processedEmails.ContainsKey($emailId)) {
                    continue
                }
                
                Write-Log "Found new PO email: $($email.Subject)"
                Write-Log "Processing email with $($email.Attachments.Count) attachments"
                
                # Process each attachment
                foreach ($attachment in $email.Attachments) {
                    Write-Log "Processing attachment: $($attachment.FileName)"
                    
                    # Save attachment temporarily
                    $tempPath = "C:\temp\$($attachment.FileName)"
                    $attachment.SaveAsFile($tempPath)
                    
                    # Send to Flask server for processing
                    try {
                        $response = Invoke-RestMethod -Uri "$FlaskServerUrl/api/process-email" -Method POST -Body @{
                            email_id = $emailId
                            subject = $email.Subject
                            attachment_name = $attachment.FileName
                            attachment_path = $tempPath
                        } -ContentType "application/json"
                        
                        Write-Log "Successfully processed attachment: $($attachment.FileName)"
                        
                        # Tag the email
                        $email.Categories = "Processed"
                        $email.Save()
                        
                    } catch {
                        Write-Log "Error processing attachment: $($_.Exception.Message)" "ERROR"
                    } finally {
                        # Clean up temp file
                        if (Test-Path $tempPath) {
                            Remove-Item $tempPath -Force
                        }
                    }
                }
                
                $processedEmails[$emailId] = Get-Date
            }
            
            $lastCheckTime = Get-Date
            Write-Log "Waiting $CheckIntervalSeconds seconds before next check..."
            Start-Sleep -Seconds $CheckIntervalSeconds
            
        } catch {
            Write-Log "Error during monitoring: $($_.Exception.Message)" "ERROR"
            Start-Sleep -Seconds 30
        }
    }
    
} catch {
    Write-Log "Failed to connect to Outlook: $($_.Exception.Message)" "ERROR"
    Write-Log "Please make sure Outlook is running and try again."
    Write-Log "You may need to restart Outlook or check COM object permissions."
}

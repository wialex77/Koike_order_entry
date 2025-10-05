# Arzana Outlook Monitor - PowerShell Solution
# Automatically monitors Outlook for PO emails and processes them

param(
    [string]$FlaskServerUrl = "https://bx3w2xz6f6.us-east-1.awsapprunner.com",
    [int]$CheckIntervalSeconds = 30,
    [string]$LogPath = "C:\Users\willt\Downloads\Koike\ArzanaPowerShell\logs\",
    [switch]$RunAsService = $false
)

# Create log directory if it doesn't exist
if (!(Test-Path $LogPath)) {
    New-Item -ItemType Directory -Path $LogPath -Force | Out-Null
}

# Logging function
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Host $logMessage
    Add-Content -Path "$LogPath\ArzanaMonitor.log" -Value $logMessage
}

# Global variables
$global:ProcessedEmails = @{}
$global:OutlookApp = $null
$global:FlaskServerUrl = $FlaskServerUrl

# Initialize Outlook COM object
function Initialize-Outlook {
    try {
        Write-Log "Initializing Outlook COM object..."
        
        # First, try to get an existing Outlook instance
        try {
            Write-Log "Trying to connect to existing Outlook instance..."
            $global:OutlookApp = [System.Runtime.InteropServices.Marshal]::GetActiveObject("Outlook.Application")
            Write-Log "Connected to existing Outlook instance"
            return $true
        }
        catch {
            Write-Log "No existing Outlook instance found. Please make sure Outlook is running!" "ERROR"
            Write-Log "Opening Outlook and waiting 10 seconds..." "INFO"
            Start-Process "outlook.exe"
            Start-Sleep -Seconds 10
            try {
                $global:OutlookApp = [System.Runtime.InteropServices.Marshal]::GetActiveObject("Outlook.Application")
                Write-Log "Connected to Outlook after opening it"
                return $true
            }
            catch {
                Write-Log "Still cannot connect to Outlook. Please make sure Outlook is running and try again." "ERROR"
                return $false
            }
        }
        
        # Try different Outlook versions
        $outlookVersions = @(
            "Outlook.Application.16",  # Office 2016/2019/2021
            "Outlook.Application.15",  # Office 2013
            "Outlook.Application.14",  # Office 2010
            "Outlook.Application"      # Generic
        )
        
        foreach ($version in $outlookVersions) {
            try {
                Write-Log "Trying to create Outlook version: $version"
                $global:OutlookApp = New-Object -ComObject $version
                Write-Log "Outlook COM object initialized successfully with version: $version"
                return $true
            }
            catch {
                Write-Log "Failed with version $version : $($_.Exception.Message)" "WARN"
                continue
            }
        }
        
        # All methods failed
        Write-Log "Failed to initialize Outlook COM object: All methods failed" "ERROR"
        Write-Log "Make sure Outlook is running and accessible" "ERROR"
        return $false
    }
    catch {
        Write-Log "Failed to initialize Outlook COM object: $($_.Exception.Message)" "ERROR"
        Write-Log "Make sure Outlook is running and accessible" "ERROR"
        return $false
    }
}

# Check if email is a PO email
function Test-POEmail {
    param([object]$MailItem)
    
    try {
        $subject = $MailItem.Subject
        if ($subject) { $subject = $subject.ToLower() } else { $subject = "" }
        
        $body = $MailItem.Body
        if ($body) { $body = $body.ToLower() } else { $body = "" }
        
        # PO keywords - simplified and more inclusive
        $subjectKeywords = @(
            "po", "purchase order", "po number", "po#", "order confirmation", "order request",
            "p.o.", "p.o number", "purchase req", "purchase request", "order form",
            "quote", "quotation", "invoice", "billing", "order details",
            "new order", "order placed", "order received", "order summary"
        )
        
        $bodyKeywords = @(
            "po", "purchase order", "po number", "po#", "order number", "order date",
            "bill to", "ship to", "quantity", "unit price", "total amount",
            "part number", "item number", "manufacturer", "supplier", "vendor",
            "order total", "subtotal", "tax", "shipping", "delivery"
        )
        
        # Check subject - use -like for partial matching
        $subjectMatch = $false
        foreach ($keyword in $subjectKeywords) {
            if ($subject -like "*$keyword*") {
                $subjectMatch = $true
                break
            }
        }
        
        # Check body - use -like for partial matching
        $bodyMatches = 0
        foreach ($keyword in $bodyKeywords) {
            if ($body -like "*$keyword*") {
                $bodyMatches++
            }
        }
        $bodyMatch = $bodyMatches -ge 2
        
        # Check for PDF attachments
        $hasPDFAttachments = $false
        if ($MailItem.Attachments) {
            for ($i = 1; $i -le $MailItem.Attachments.Count; $i++) {
                $attachment = $MailItem.Attachments.Item($i)
                if ($attachment.FileName.ToLower() -like "*.pdf") {
                    $hasPDFAttachments = $true
                    break
                }
            }
        }
        
        # Check for structured data patterns
        $hasStructuredData = $body -match '\b\d{4,}\b' -or $body -match '\$\d+\.\d{2}' -or $body -match '\b\d+\s+(ea|each|pcs|pieces)\b'
        
        # Calculate confidence
        $confidence = 0
        if ($subjectMatch) { $confidence += 40 }
        if ($bodyMatch) { $confidence += 25 }
        if ($hasPDFAttachments) { $confidence += 20 }
        if ($hasStructuredData) { $confidence += 15 }
        
        $isPO = $confidence -ge 40
        
        Write-Log "PO Detection - Subject: $subjectMatch, Body: $bodyMatch, PDF: $hasPDFAttachments, Structured: $hasStructuredData, Confidence: $confidence%, IsPO: $isPO"
        
        return $isPO
    }
    catch {
        Write-Log "Error in PO detection: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# Process PO email with Flask server
function Invoke-ProcessPOEmail {
    param([object]$MailItem)
    
    try {
        Write-Log "Processing PO email: $($MailItem.Subject)"
        
        # Check for PDF attachments first
        $pdfAttachment = $null
        if ($MailItem.Attachments) {
            for ($i = 1; $i -le $MailItem.Attachments.Count; $i++) {
                $attachment = $MailItem.Attachments.Item($i)
                if ($attachment.FileName.ToLower() -like "*.pdf") {
                    $pdfAttachment = $attachment
                    break
                }
            }
        }
        
        if ($pdfAttachment) {
            # Process PDF attachment
            $tempPath = [System.IO.Path]::GetTempFileName()
            $pdfPath = [System.IO.Path]::ChangeExtension($tempPath, ".pdf")
            $pdfAttachment.SaveAsFile($pdfPath)
            
            try {
                $result = Invoke-FlaskProcessing -FilePath $pdfPath -FileName $pdfAttachment.FileName
            }
            finally {
                if (Test-Path $pdfPath) { Remove-Item $pdfPath -Force }
            }
        }
        else {
            # Process email body as text
            $bodyText = $MailItem.Body
            $tempPath = [System.IO.Path]::GetTempFileName()
            $txtPath = [System.IO.Path]::ChangeExtension($tempPath, ".txt")
            [System.IO.File]::WriteAllText($txtPath, $bodyText)
            
            try {
                $result = Invoke-FlaskProcessing -FilePath $txtPath -FileName "email_content.txt"
            }
            finally {
                if (Test-Path $txtPath) { Remove-Item $txtPath -Force }
            }
        }
        
        # Update email category based on result
        Update-EmailCategory -MailItem $MailItem -Result $result
        
        return $result
    }
    catch {
        Write-Log "Error processing PO email: $($_.Exception.Message)" "ERROR"
        Update-EmailCategory -MailItem $MailItem -Result @{ Status = "error"; ErrorMessage = $_.Exception.Message }
        return $null
    }
}

# Send file to Flask server for processing
function Invoke-FlaskProcessing {
    param([string]$FilePath, [string]$FileName)
    
    try {
        Write-Log "Sending $FileName to Flask server..."
        
        # Create proper multipart form data
        $boundary = [System.Guid]::NewGuid().ToString()
        $LF = "`r`n"
        
        $fileBytes = [System.IO.File]::ReadAllBytes($FilePath)
        $fileContent = [System.Text.Encoding]::GetEncoding("iso-8859-1").GetString($fileBytes)
        
        $body = (
            "--$boundary$LF" +
            "Content-Disposition: form-data; name=`"file`"; filename=`"$FileName`"$LF" +
            "Content-Type: application/octet-stream$LF$LF" +
            "$fileContent$LF" +
            "--$boundary--$LF"
        )
        
        $bodyBytes = [System.Text.Encoding]::GetEncoding("iso-8859-1").GetBytes($body)
        
        $headers = @{
            "Content-Type" = "multipart/form-data; boundary=$boundary"
        }
        
        $response = Invoke-RestMethod -Uri "$FlaskServerUrl/upload-test" -Method Post -Body $bodyBytes -Headers $headers -TimeoutSec 300
        
        Write-Log "Flask server response received"
        return $response
    }
    catch {
        Write-Log "Error calling Flask server: $($_.Exception.Message)" "ERROR"
        return @{ success = $false; error = $_.Exception.Message }
    }
}

# Ensure Outlook categories exist with correct colors
function Initialize-OutlookCategories {
    try {
        $namespace = $global:OutlookApp.GetNamespace("MAPI")
        $categories = $namespace.Categories
        
        # Define categories with colors
        # OlCategoryColor: 0=None, 1=Red, 2=Orange, 3=Peach, 4=Yellow, 5=Green, 6=Teal, 7=Olive, 8=Blue, 9=Purple, 10=Maroon, etc.
        $categoryDefinitions = @{
            "Approved" = 5           # Green
            "Pending Approval" = 4   # Yellow
            "Missing Info" = 1       # Red
        }
        
        foreach ($catName in $categoryDefinitions.Keys) {
            $exists = $false
            foreach ($cat in $categories) {
                if ($cat.Name -eq $catName) {
                    $exists = $true
                    # Update color if needed
                    $cat.Color = $categoryDefinitions[$catName]
                    break
                }
            }
            
            if (-not $exists) {
                $newCat = $categories.Add($catName)
                $newCat.Color = $categoryDefinitions[$catName]
                Write-Log "Created category: $catName"
            }
        }
    }
    catch {
        Write-Log "Error initializing categories: $($_.Exception.Message)" "WARN"
    }
}

# Update email category based on processing result
function Update-EmailCategory {
    param([object]$MailItem, [object]$Result)
    
    try {
        $newCategory = "Missing Info"  # Default to red
        
        if ($Result.success -eq $true) {
            # Check confidence score
            $confidence = 0
            if ($Result.data.confidence_score) {
                $confidence = $Result.data.confidence_score
            }
            
            # Check if everything is matched and ready
            $customerMatched = $Result.data.company_info.customer_match_status -eq "matched"
            $partsMapped = $Result.data.processing_summary.parts_mapped -gt 0
            $missingInfo = $Result.data.missing_fields -and $Result.data.missing_fields.Count -gt 0
            
            if ($confidence -ge 95 -and $customerMatched -and $partsMapped -and -not $missingInfo) {
                $newCategory = "Pending Approval"  # Yellow - high confidence, ready for approval
            }
            elseif ($customerMatched -and $partsMapped) {
                $newCategory = "Pending Approval"  # Yellow - has data but lower confidence
            }
            elseif ($missingInfo) {
                $newCategory = "Missing Info"  # Red - missing required information
            }
            else {
                $newCategory = "Missing Info"  # Red - needs review
            }
        }
        else {
            # Processing failed
            $newCategory = "Missing Info"  # Red - error or missing info
        }
        
        # Update email categories - use comma separator (Outlook standard)
        $currentCategories = $MailItem.Categories
        if ($currentCategories) {
            $categories = $currentCategories -split ","
            $categories = $categories | ForEach-Object { $_.Trim() }
            $filteredCategories = $categories | Where-Object { 
                $_ -ne "Approved" -and $_ -ne "Pending Approval" -and $_ -ne "Missing Info" 
            }
            if ($filteredCategories) {
                $MailItem.Categories = (($filteredCategories + $newCategory) -join ", ")
            } else {
                $MailItem.Categories = $newCategory
            }
        }
        else {
            $MailItem.Categories = $newCategory
        }
        
        $MailItem.Save()
        Write-Log "Email tagged as: $newCategory"
    }
    catch {
        Write-Log "Error updating email category: $($_.Exception.Message)" "ERROR"
    }
}

# Check for new emails in inbox
function Get-NewEmails {
    try {
        $namespace = $global:OutlookApp.GetNamespace("MAPI")
        $inbox = $namespace.GetDefaultFolder(6) # olFolderInbox
        
        Write-Log "Checking inbox: $($inbox.Name)"
        Write-Log "Total items in inbox: $($inbox.Items.Count)"
        
        # Get all emails (not just unread) - Class 43 is the numeric value for IPM.Note
        $allEmails = $inbox.Items | Where-Object { 
            $_.Class -eq "IPM.Note" -or $_.Class -eq 43
        }
        Write-Log "Total emails in inbox: $($allEmails.Count)"
        
        # Debug: Show all items and their classes
        Write-Log "Debug - All items in inbox:"
        for ($i = 1; $i -le $inbox.Items.Count; $i++) {
            $item = $inbox.Items.Item($i)
            Write-Log "  Item $i : Class=$($item.Class), Subject=$($item.Subject)"
        }
        
        # Filter out already processed emails and emails that already have status tags
        $candidateEmails = $allEmails | Where-Object { 
            $entryId = $_.EntryID
            $categories = $_.Categories
            
            # Skip if already processed
            if ($global:ProcessedEmails.ContainsKey($entryId)) {
                return $false
            }
            
            # Skip if has any status category
            if ($categories) {
                $lowerCat = $categories.ToLower()
                if ($lowerCat -like "*approved*" -or $lowerCat -like "*pending*" -or $lowerCat -like "*missing*") {
                    return $false
                }
            }
            
            return $true
        }
        Write-Log "Candidate emails (not processed, no status tags): $($candidateEmails.Count)"
        
        # Log details of candidate emails for debugging
        if ($candidateEmails.Count -gt 0) {
            Write-Log "Candidate email details:"
            foreach ($email in $candidateEmails) {
                Write-Log "  - Subject: $($email.Subject), From: $($email.SenderName), EntryID: $($email.EntryID), Categories: $($email.Categories)"
            }
        }
        
        return $candidateEmails
    }
    catch {
        Write-Log "Error getting new emails: $($_.Exception.Message)" "ERROR"
        return @()
    }
}

# Main monitoring loop
function Start-Monitoring {
    Write-Log "Starting Arzana Outlook Monitor..."
    Write-Log "Flask Server: $FlaskServerUrl"
    Write-Log "Check Interval: $CheckIntervalSeconds seconds"
    
    if (!(Initialize-Outlook)) {
        Write-Log "Failed to initialize Outlook. Exiting." "ERROR"
        return
    }
    
    # Initialize Outlook categories with colors
    Write-Log "Initializing Outlook categories..."
    Initialize-OutlookCategories
    
    # Test Flask server connection
    try {
        $testResponse = Invoke-RestMethod -Uri "$FlaskServerUrl" -Method Get -TimeoutSec 10
        Write-Log "Flask server connection successful"
    }
    catch {
        Write-Log "Warning: Cannot connect to Flask server at $FlaskServerUrl" "WARN"
    }
    
    Write-Log "Monitoring started. Press Ctrl+C to stop."
    
    while ($true) {
        try {
            $newEmails = Get-NewEmails
            
            foreach ($email in $newEmails) {
                try {
                    Write-Log "Checking email: $($email.Subject)"
                    
                    # Mark as being processed
                    $global:ProcessedEmails[$email.EntryID] = Get-Date
                    
                    # Use COM object directly without explicit casting
                    if (Test-POEmail -MailItem $email) {
                        Write-Log "PO email detected, processing..."
                        $result = Invoke-ProcessPOEmail -MailItem $email
                        Write-Log "PO email processed successfully"
                    }
                    else {
                        Write-Log "Not a PO email, skipping"
                    }
                }
                catch {
                    Write-Log "Error processing email $($email.Subject): $($_.Exception.Message)" "ERROR"
                }
            }
            
            Start-Sleep -Seconds $CheckIntervalSeconds
        }
        catch {
            Write-Log "Error in monitoring loop: $($_.Exception.Message)" "ERROR"
            Start-Sleep -Seconds $CheckIntervalSeconds
        }
    }
}

# Cleanup function
function Stop-Monitoring {
    Write-Log "Stopping Arzana Outlook Monitor..."
    if ($global:OutlookApp) {
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($global:OutlookApp) | Out-Null
    }
    Write-Log "Monitor stopped"
}

# Handle Ctrl+C
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    Stop-Monitoring
}

# Start monitoring
try {
    Start-Monitoring
}
finally {
    Stop-Monitoring
}

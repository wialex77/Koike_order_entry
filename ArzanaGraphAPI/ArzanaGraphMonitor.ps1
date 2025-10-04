# Arzana Outlook Monitor - Microsoft Graph API Version
# This version uses Microsoft Graph API instead of COM for more reliable email monitoring

param(
    [string]$ConfigPath = "$PSScriptRoot\config.json"
)

# Load configuration
if (Test-Path $ConfigPath) {
    $config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
    $TenantId = $config.tenant_id
    $ClientId = $config.client_id
    $ClientSecret = $config.client_secret
    $FlaskServerUrl = $config.flask_server_url
    $CheckIntervalSeconds = $config.check_interval_seconds
    $UserEmail = $config.user_email  # The email address of the mailbox to monitor
} else {
    Write-Host "Config file not found at: $ConfigPath" -ForegroundColor Red
    Write-Host "Please create config.json with your Azure app credentials" -ForegroundColor Yellow
    exit 1
}

# Global variables
$global:ProcessedEmails = @{}
$global:AccessToken = $null
$global:TokenExpiry = $null
$LogFile = "$PSScriptRoot\monitor.log"

# Logging function
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Host $logMessage
    Add-Content -Path $LogFile -Value $logMessage
}

# Get access token from Azure AD
function Get-GraphAccessToken {
    try {
        Write-Log "Getting access token from Azure AD..."
        
        $body = @{
            client_id     = $ClientId
            scope         = "https://graph.microsoft.com/.default"
            client_secret = $ClientSecret
            grant_type    = "client_credentials"
        }
        
        $tokenResponse = Invoke-RestMethod -Method Post -Uri "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token" -Body $body
        
        $global:AccessToken = $tokenResponse.access_token
        $global:TokenExpiry = (Get-Date).AddSeconds($tokenResponse.expires_in - 300) # Refresh 5 min early
        
        Write-Log "Access token obtained successfully (expires in $($tokenResponse.expires_in) seconds)"
        return $true
    }
    catch {
        Write-Log "Failed to get access token: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# Check if token needs refresh
function Test-TokenExpiry {
    if ($null -eq $global:AccessToken -or $null -eq $global:TokenExpiry) {
        return $true
    }
    return (Get-Date) -ge $global:TokenExpiry
}

# Get emails from inbox using Microsoft Graph
function Get-InboxEmails {
    try {
        # Refresh token if needed
        if (Test-TokenExpiry) {
            if (-not (Get-GraphAccessToken)) {
                return @()
            }
        }
        
        $headers = @{
            "Authorization" = "Bearer $global:AccessToken"
            "Content-Type"  = "application/json"
        }
        
        # Get emails from inbox (top 50, sorted by received date)
        $uri = "https://graph.microsoft.com/v1.0/users/$UserEmail/mailFolders/inbox/messages?`$top=50&`$orderby=receivedDateTime desc&`$select=id,subject,from,receivedDateTime,hasAttachments,bodyPreview,categories,body"
        
        $response = Invoke-RestMethod -Method Get -Uri $uri -Headers $headers
        
        Write-Log "Retrieved $($response.value.Count) emails from inbox"
        return $response.value
    }
    catch {
        Write-Log "Error getting inbox emails: $($_.Exception.Message)" "ERROR"
        return @()
    }
}

# Get email attachments
function Get-EmailAttachments {
    param([string]$MessageId)
    
    try {
        if (Test-TokenExpiry) {
            if (-not (Get-GraphAccessToken)) {
                return @()
            }
        }
        
        $headers = @{
            "Authorization" = "Bearer $global:AccessToken"
            "Content-Type"  = "application/json"
        }
        
        $uri = "https://graph.microsoft.com/v1.0/users/$UserEmail/messages/$MessageId/attachments"
        $response = Invoke-RestMethod -Method Get -Uri $uri -Headers $headers
        
        return $response.value
    }
    catch {
        Write-Log "Error getting attachments: $($_.Exception.Message)" "ERROR"
        return @()
    }
}

# Update email categories (tags)
function Update-EmailCategories {
    param(
        [string]$MessageId,
        [string]$Category
    )
    
    try {
        if (Test-TokenExpiry) {
            if (-not (Get-GraphAccessToken)) {
                return $false
            }
        }
        
        $headers = @{
            "Authorization" = "Bearer $global:AccessToken"
            "Content-Type"  = "application/json"
        }
        
        # Get current categories
        $uri = "https://graph.microsoft.com/v1.0/users/$UserEmail/messages/$MessageId"
        $email = Invoke-RestMethod -Method Get -Uri $uri -Headers $headers
        
        # Add new category, remove old status categories
        $currentCategories = @($email.categories)
        $filteredCategories = $currentCategories | Where-Object { 
            $_ -ne "Approved" -and $_ -ne "Pending Approval" -and $_ -ne "Missing Info" 
        }
        $newCategories = @($filteredCategories) + @($Category)
        
        # Update email with new categories
        $body = @{
            categories = $newCategories
        } | ConvertTo-Json
        
        Invoke-RestMethod -Method Patch -Uri $uri -Headers $headers -Body $body | Out-Null
        
        Write-Log "Tagged email as: $Category"
        return $true
    }
    catch {
        Write-Log "Error updating email categories: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# Check if email is a PO email
function Test-POEmail {
    param([object]$Email)
    
    try {
        $subject = $Email.subject.ToLower()
        $body = $Email.bodyPreview.ToLower()
        if ($Email.body -and $Email.body.content) {
            $body = $Email.body.content.ToLower()
        }
        
        # PO keywords
        $subjectKeywords = @("po", "purchase order", "po number", "po#", "order confirmation", 
                            "order request", "p.o.", "quote", "quotation", "invoice", 
                            "new order", "order placed")
        
        $bodyKeywords = @("po", "purchase order", "po number", "order number", "bill to", 
                         "ship to", "quantity", "unit price", "part number", "supplier")
        
        # Check subject
        $subjectMatch = $false
        foreach ($keyword in $subjectKeywords) {
            if ($subject -like "*$keyword*") {
                $subjectMatch = $true
                break
            }
        }
        
        # Check body
        $bodyMatches = 0
        foreach ($keyword in $bodyKeywords) {
            if ($body -like "*$keyword*") {
                $bodyMatches++
            }
        }
        $bodyMatch = $bodyMatches -ge 2
        
        # Check for attachments
        $hasPDFAttachment = $Email.hasAttachments
        
        # Calculate confidence
        $confidence = 0
        if ($subjectMatch) { $confidence += 40 }
        if ($bodyMatch) { $confidence += 25 }
        if ($hasPDFAttachment) { $confidence += 20 }
        if ($body -match '\b\d{4,}\b' -or $body -match '\$\d+\.\d{2}') { $confidence += 15 }
        
        $isPO = $confidence -ge 40
        
        Write-Log "PO Detection - Subject: $subjectMatch, Body: $bodyMatch, Attachments: $hasPDFAttachment, Confidence: $confidence%, IsPO: $isPO"
        
        return $isPO
    }
    catch {
        Write-Log "Error in PO detection: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# Process PO email with Flask server
function Invoke-ProcessPOEmail {
    param([object]$Email)
    
    try {
        Write-Log "Processing PO email: $($Email.subject)"
        
        # Get attachments
        $attachments = Get-EmailAttachments -MessageId $Email.id
        $pdfAttachment = $attachments | Where-Object { $_.name -like "*.pdf" } | Select-Object -First 1
        
        if ($pdfAttachment) {
            Write-Log "Found PDF attachment: $($pdfAttachment.name)"
            
            # Decode base64 content
            $fileBytes = [System.Convert]::FromBase64String($pdfAttachment.contentBytes)
            
            # Save to temp file
            $tempFile = [System.IO.Path]::GetTempFileName()
            $tempPdfFile = $tempFile -replace '\.tmp$', '.pdf'
            [System.IO.File]::WriteAllBytes($tempPdfFile, $fileBytes)
            
            # Upload to Flask server
            $boundary = [System.Guid]::NewGuid().ToString()
            $bodyLines = @()
            $bodyLines += "--$boundary"
            $bodyLines += "Content-Disposition: form-data; name=`"file`"; filename=`"$($pdfAttachment.name)`""
            $bodyLines += "Content-Type: application/pdf"
            $bodyLines += ""
            $bodyLines += [System.Text.Encoding]::GetEncoding("iso-8859-1").GetString($fileBytes)
            $bodyLines += "--$boundary--"
            
            $body = $bodyLines -join "`r`n"
            $bodyBytes = [System.Text.Encoding]::GetEncoding("iso-8859-1").GetBytes($body)
            
            $headers = @{
                "Content-Type" = "multipart/form-data; boundary=$boundary"
            }
            
            $response = Invoke-RestMethod -Uri "$FlaskServerUrl/upload" -Method Post -Body $bodyBytes -Headers $headers -TimeoutSec 300
            
            # Clean up temp file
            Remove-Item $tempPdfFile -ErrorAction SilentlyContinue
            
            Write-Log "Flask server response received"
            
            # Determine category based on response
            $category = "Missing Info"
            if ($response.success -eq $true) {
                $confidence = if ($response.data.confidence_score) { $response.data.confidence_score } else { 0 }
                $customerMatched = $response.data.company_info.customer_match_status -eq "matched"
                $partsMapped = $response.data.processing_summary.parts_mapped -gt 0
                $missingInfo = $response.data.missing_fields -and $response.data.missing_fields.Count -gt 0
                
                if ($confidence -ge 95 -and $customerMatched -and $partsMapped -and -not $missingInfo) {
                    $category = "Pending Approval"
                }
                elseif ($customerMatched -and $partsMapped) {
                    $category = "Pending Approval"
                }
            }
            
            # Tag the email
            Update-EmailCategories -MessageId $Email.id -Category $category
            
            return $response
        }
        else {
            Write-Log "No PDF attachment found, processing email body..."
            
            # Process email body as text
            $emailData = @{
                subject = $Email.subject
                from = $Email.from.emailAddress.address
                body = if ($Email.body.content) { $Email.body.content } else { $Email.bodyPreview }
            } | ConvertTo-Json
            
            $response = Invoke-RestMethod -Uri "$FlaskServerUrl/process_text" -Method Post -Body $emailData -ContentType "application/json" -TimeoutSec 300
            
            # Tag as Missing Info since no PDF
            Update-EmailCategories -MessageId $Email.id -Category "Missing Info"
            
            return $response
        }
    }
    catch {
        Write-Log "Error processing PO email: $($_.Exception.Message)" "ERROR"
        Update-EmailCategories -MessageId $Email.id -Category "Missing Info"
        return @{ success = $false; error = $_.Exception.Message }
    }
}

# Main monitoring loop
function Start-Monitoring {
    Write-Log "Starting Arzana Outlook Monitor (Graph API version)..."
    Write-Log "Flask Server: $FlaskServerUrl"
    Write-Log "Check Interval: $CheckIntervalSeconds seconds"
    Write-Log "Monitoring mailbox: $UserEmail"
    
    # Get initial access token
    if (-not (Get-GraphAccessToken)) {
        Write-Log "Failed to get access token. Exiting." "ERROR"
        return
    }
    
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
            $emails = Get-InboxEmails
            
            # Filter emails that haven't been processed and don't have status categories
            $candidateEmails = $emails | Where-Object {
                $emailId = $_.id
                $categories = $_.categories
                
                # Skip if already processed
                if ($global:ProcessedEmails.ContainsKey($emailId)) {
                    return $false
                }
                
                # Skip if has status category
                if ($categories) {
                    foreach ($cat in $categories) {
                        if ($cat -eq "Approved" -or $cat -eq "Pending Approval" -or $cat -eq "Missing Info") {
                            return $false
                        }
                    }
                }
                
                return $true
            }
            
            Write-Log "Found $($candidateEmails.Count) unprocessed emails"
            
            foreach ($email in $candidateEmails) {
                try {
                    Write-Log "Checking email: $($email.subject)"
                    
                    # Mark as being processed
                    $global:ProcessedEmails[$email.id] = Get-Date
                    
                    if (Test-POEmail -Email $email) {
                        Write-Log "PO email detected, processing..."
                        $result = Invoke-ProcessPOEmail -Email $email
                        Write-Log "PO email processed successfully"
                    }
                    else {
                        Write-Log "Not a PO email, skipping"
                    }
                }
                catch {
                    Write-Log "Error processing email $($email.subject): $($_.Exception.Message)" "ERROR"
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

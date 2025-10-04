# Test script to add tags to emails in inbox

Write-Host "Connecting to Outlook..." -ForegroundColor Cyan

try {
    # Try to get existing Outlook instance first
    $outlookApp = $null
    
    try {
        Write-Host "Trying to connect to running Outlook instance..." -ForegroundColor Yellow
        $outlookApp = [System.Runtime.InteropServices.Marshal]::GetActiveObject("Outlook.Application")
        Write-Host "Connected to existing Outlook instance" -ForegroundColor Green
    }
    catch {
        Write-Host "No existing instance found, creating new one..." -ForegroundColor Yellow
        $outlookApp = New-Object -ComObject Outlook.Application
        Write-Host "Created new Outlook instance" -ForegroundColor Green
    }
    
    if (!$outlookApp) {
        throw "Could not connect to Outlook"
    }
    
    # Get inbox
    $namespace = $outlookApp.GetNamespace("MAPI")
    $inbox = $namespace.GetDefaultFolder(6) # olFolderInbox
    
    Write-Host "`nInbox: $($inbox.Name)" -ForegroundColor Cyan
    Write-Host "Total items: $($inbox.Items.Count)" -ForegroundColor Cyan
    
    # Get all emails
    $emails = @()
    for ($i = 1; $i -le $inbox.Items.Count; $i++) {
        $item = $inbox.Items.Item($i)
        if ($item.Class -eq 43) {  # MailItem
            $emails += $item
        }
    }
    
    Write-Host "`nFound $($emails.Count) emails" -ForegroundColor Cyan
    Write-Host "`nAdding 'Test' category to each email..." -ForegroundColor Cyan
    
    foreach ($email in $emails) {
        Write-Host "  Processing: $($email.Subject)" -ForegroundColor Yellow
        
        try {
            # Get current categories
            $currentCategories = $email.Categories
            Write-Host "    Current categories: '$currentCategories'" -ForegroundColor Gray
            
            # Add Test category
            if ($currentCategories) {
                $email.Categories = "$currentCategories, Test"
            } else {
                $email.Categories = "Test"
            }
            
            # Save the email
            $email.Save()
            
            Write-Host "    Added 'Test' category" -ForegroundColor Green
            Write-Host "    New categories: '$($email.Categories)'" -ForegroundColor Gray
        }
        catch {
            Write-Host "    ERROR: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    Write-Host "`nDone! Check your inbox in Outlook." -ForegroundColor Green
}
catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    if ($outlookApp) {
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($outlookApp) | Out-Null
    }
}

Write-Host "`nPress any key to exit..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

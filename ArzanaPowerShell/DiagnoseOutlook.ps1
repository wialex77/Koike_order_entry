# Diagnostic script to check Outlook COM status

Write-Host "`n=== Outlook COM Diagnostic ===" -ForegroundColor Cyan
Write-Host ""

# Check if Outlook process is running
Write-Host "1. Checking if Outlook.exe is running..." -ForegroundColor Yellow
$outlookProcesses = Get-Process -Name "OUTLOOK" -ErrorAction SilentlyContinue
if ($outlookProcesses) {
    Write-Host "   ✓ Outlook.exe is running" -ForegroundColor Green
    Write-Host "   Process ID(s): $($outlookProcesses.Id -join ', ')" -ForegroundColor Gray
} else {
    Write-Host "   ✗ Outlook.exe is NOT running" -ForegroundColor Red
    Write-Host "   Please start Outlook first!" -ForegroundColor Red
    Read-Host "`nPress Enter to exit"
    exit
}

Write-Host ""

# Check if we're running as admin
Write-Host "2. Checking if script is running as Administrator..." -ForegroundColor Yellow
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    Write-Host "   ✓ Running as Administrator" -ForegroundColor Green
} else {
    Write-Host "   ✗ NOT running as Administrator" -ForegroundColor Red
    Write-Host "   This might be the problem!" -ForegroundColor Red
}

Write-Host ""

# Try GetActiveObject
Write-Host "3. Testing GetActiveObject..." -ForegroundColor Yellow
try {
    $outlookApp = [System.Runtime.InteropServices.Marshal]::GetActiveObject("Outlook.Application")
    Write-Host "   ✓ GetActiveObject succeeded!" -ForegroundColor Green
    Write-Host "   Outlook Version: $($outlookApp.Version)" -ForegroundColor Gray
    
    # Try to get inbox
    $namespace = $outlookApp.GetNamespace("MAPI")
    $inbox = $namespace.GetDefaultFolder(6)
    Write-Host "   ✓ Can access inbox: $($inbox.Name)" -ForegroundColor Green
    Write-Host "   Total items: $($inbox.Items.Count)" -ForegroundColor Gray
    
    Write-Host ""
    Write-Host "=== RESULT: Everything looks good! ===" -ForegroundColor Green
    Write-Host "The monitor should work now. Try running it again." -ForegroundColor Green
}
catch {
    Write-Host "   ✗ GetActiveObject FAILED" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    
    Write-Host ""
    Write-Host "4. Testing New-Object..." -ForegroundColor Yellow
    try {
        $outlookApp = New-Object -ComObject Outlook.Application
        Write-Host "   ✓ New-Object succeeded!" -ForegroundColor Green
        Write-Host "   Outlook Version: $($outlookApp.Version)" -ForegroundColor Gray
    }
    catch {
        Write-Host "   ✗ New-Object FAILED" -ForegroundColor Red
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
        
        Write-Host ""
        Write-Host "=== POSSIBLE SOLUTIONS ===" -ForegroundColor Yellow
        Write-Host "1. Close Outlook completely and restart it" -ForegroundColor White
        Write-Host "2. Run this command in Command Prompt:" -ForegroundColor White
        Write-Host "   outlook.exe /resetnavpane" -ForegroundColor Cyan
        Write-Host "3. Restart your computer" -ForegroundColor White
        Write-Host "4. Check if Windows Updates are installing" -ForegroundColor White
        Write-Host "5. Try running Outlook as Administrator" -ForegroundColor White
    }
}

Write-Host ""
Read-Host "Press Enter to exit"

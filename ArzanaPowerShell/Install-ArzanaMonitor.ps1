# Arzana Outlook Monitor - Installation Script
# This script installs and configures the Arzana Outlook Monitor

param(
    [string]$InstallPath = "C:\ArzanaMonitor",
    [string]$FlaskServerUrl = "http://127.0.0.1:5000",
    [switch]$InstallAsService = $false,
    [switch]$Force = $false
)

Write-Host "Arzana Outlook Monitor - Installation Script" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "This script requires administrator privileges. Please run as administrator." -ForegroundColor Red
    exit 1
}

# Create installation directory
if (!(Test-Path $InstallPath)) {
    Write-Host "Creating installation directory: $InstallPath" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
}

# Copy files
Write-Host "Copying files..." -ForegroundColor Yellow
Copy-Item "ArzanaOutlookMonitor.ps1" -Destination "$InstallPath\ArzanaOutlookMonitor.ps1" -Force
Copy-Item "config.json" -Destination "$InstallPath\config.json" -Force

# Create logs directory
$LogPath = "$InstallPath\logs"
if (!(Test-Path $LogPath)) {
    New-Item -ItemType Directory -Path $LogPath -Force | Out-Null
}

# Update config with user settings
Write-Host "Updating configuration..." -ForegroundColor Yellow
$config = Get-Content "$InstallPath\config.json" | ConvertFrom-Json
$config.FlaskServerUrl = $FlaskServerUrl
$config.LogPath = "$LogPath\"
$config | ConvertTo-Json -Depth 10 | Set-Content "$InstallPath\config.json"

# Create batch file for easy execution
$batchContent = @"
@echo off
echo Starting Arzana Outlook Monitor...
cd /d "$InstallPath"
powershell.exe -ExecutionPolicy Bypass -File "ArzanaOutlookMonitor.ps1" -FlaskServerUrl "$FlaskServerUrl"
pause
"@
$batchContent | Set-Content "$InstallPath\Start-ArzanaMonitor.bat"

# Create service installation script (if requested)
if ($InstallAsService) {
    Write-Host "Creating Windows Service..." -ForegroundColor Yellow
    
    $serviceScript = @"
# Install as Windows Service using NSSM (Non-Sucking Service Manager)
# Download NSSM from: https://nssm.cc/download

# Install the service
nssm install ArzanaMonitor "$InstallPath\ArzanaOutlookMonitor.ps1"
nssm set ArzanaMonitor AppParameters "-FlaskServerUrl `"$FlaskServerUrl`""
nssm set ArzanaMonitor AppDirectory "$InstallPath"
nssm set ArzanaMonitor DisplayName "Arzana Outlook Monitor"
nssm set ArzanaMonitor Description "Automatically monitors Outlook for PO emails and processes them"

# Start the service
nssm start ArzanaMonitor

Write-Host "Service installed and started. Use 'nssm stop ArzanaMonitor' to stop it."
"@
    
    $serviceScript | Set-Content "$InstallPath\Install-Service.ps1"
    Write-Host "Service installation script created: $InstallPath\Install-Service.ps1" -ForegroundColor Green
    Write-Host "Note: You need to download NSSM from https://nssm.cc/download first" -ForegroundColor Yellow
}

# Set execution policy
Write-Host "Setting PowerShell execution policy..." -ForegroundColor Yellow
try {
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine -Force
    Write-Host "Execution policy set successfully" -ForegroundColor Green
}
catch {
    Write-Host "Warning: Could not set execution policy: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Create desktop shortcut
Write-Host "Creating desktop shortcut..." -ForegroundColor Yellow
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Arzana Monitor.lnk")
$Shortcut.TargetPath = "$InstallPath\Start-ArzanaMonitor.bat"
$Shortcut.WorkingDirectory = $InstallPath
$Shortcut.Description = "Arzana Outlook Monitor"
$Shortcut.Save()

Write-Host ""
Write-Host "Installation completed successfully!" -ForegroundColor Green
Write-Host "Installation path: $InstallPath" -ForegroundColor Cyan
Write-Host "Logs path: $LogPath" -ForegroundColor Cyan
Write-Host "Flask server: $FlaskServerUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start monitoring:" -ForegroundColor Yellow
Write-Host "1. Double-click 'Arzana Monitor' on your desktop" -ForegroundColor White
Write-Host "2. Or run: $InstallPath\Start-ArzanaMonitor.bat" -ForegroundColor White
Write-Host ""
Write-Host "Make sure your Flask server is running on $FlaskServerUrl" -ForegroundColor Yellow
Write-Host "Make sure Outlook is running and accessible" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Check what permissions the token has

$config = Get-Content "$PSScriptRoot\config.json" -Raw | ConvertFrom-Json

Write-Host "`nGetting access token..." -ForegroundColor Cyan

$body = @{
    client_id     = $config.client_id
    scope         = "https://graph.microsoft.com/.default"
    client_secret = $config.client_secret
    grant_type    = "client_credentials"
}

$response = Invoke-RestMethod -Method Post -Uri "https://login.microsoftonline.com/$($config.tenant_id)/oauth2/v2.0/token" -Body $body

Write-Host "Token obtained!" -ForegroundColor Green
Write-Host ""

# Decode the JWT token to see what permissions it has
$tokenParts = $response.access_token.Split('.')
$tokenPayload = $tokenParts[1]

# Add padding if needed
while ($tokenPayload.Length % 4 -ne 0) {
    $tokenPayload += "="
}

$bytes = [System.Convert]::FromBase64String($tokenPayload)
$json = [System.Text.Encoding]::UTF8.GetString($bytes)
$decoded = $json | ConvertFrom-Json

Write-Host "=== TOKEN PERMISSIONS ===" -ForegroundColor Yellow
Write-Host ""

if ($decoded.roles) {
    Write-Host "Roles/Permissions in token:" -ForegroundColor Cyan
    foreach ($role in $decoded.roles) {
        Write-Host "  - $role" -ForegroundColor Green
    }
    Write-Host ""
    
    $hasMail = $decoded.roles | Where-Object { $_ -like "*Mail*" }
    if ($hasMail) {
        Write-Host "SUCCESS: Mail permissions found!" -ForegroundColor Green
        Write-Host "The monitor should work now." -ForegroundColor Green
    }
    else {
        Write-Host "PROBLEM: No Mail permissions found!" -ForegroundColor Red
        Write-Host ""
        Write-Host "You need to add these Application permissions:" -ForegroundColor Yellow
        Write-Host "  - Mail.Read" -ForegroundColor White
        Write-Host "  - Mail.ReadWrite" -ForegroundColor White
        Write-Host ""
        Write-Host "Make sure you:" -ForegroundColor Yellow
        Write-Host "1. Select 'Application permissions' (NOT Delegated)" -ForegroundColor White
        Write-Host "2. Click 'Grant admin consent' after adding" -ForegroundColor White
    }
}
else {
    Write-Host "PROBLEM: No roles/permissions in token!" -ForegroundColor Red
    Write-Host "This means you haven't added Application permissions yet." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "App ID: $($decoded.appid)" -ForegroundColor Gray
Write-Host "Tenant: $($decoded.tid)" -ForegroundColor Gray
Write-Host ""

pause

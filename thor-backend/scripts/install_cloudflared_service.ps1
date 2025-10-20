# Install Cloudflared Service (Run as Administrator)
# This script must be run with administrator privileges

Write-Host "Installing cloudflared Windows service..." -ForegroundColor Yellow

# Check if running as admin
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    pause
    exit 1
}

# Navigate to Thor directory to ensure we're in the right context
Set-Location "A:\Thor"

# Install the service
Write-Host "Installing cloudflared service..." -ForegroundColor Green
try {
    & "C:\Program Files (x86)\cloudflared\cloudflared.exe" service install
    Write-Host "✅ Cloudflared service installed successfully!" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to install cloudflared service: $($_.Exception.Message)" -ForegroundColor Red
    pause
    exit 1
}

# Verify the service was created
Write-Host "`nVerifying service installation..." -ForegroundColor Yellow
try {
    $service = Get-Service cloudflared -ErrorAction Stop
    Write-Host "✅ Service found: $($service.Name) - Status: $($service.Status)" -ForegroundColor Green
} catch {
    Write-Host "❌ Service verification failed: $($_.Exception.Message)" -ForegroundColor Red
    pause
    exit 1
}

# Set service to Manual startup (as per your configuration)
Write-Host "`nSetting service startup type to Manual..." -ForegroundColor Yellow
try {
    Set-Service cloudflared -StartupType Manual
    Write-Host "✅ Service startup type set to Manual" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to set service startup type: $($_.Exception.Message)" -ForegroundColor Red
}

# Show current service status
Write-Host "`nCurrent service status:" -ForegroundColor Yellow
Get-Service cloudflared | Format-Table Name, DisplayName, Status, StartType

Write-Host "`nCloudflared service installation complete!" -ForegroundColor Green
Write-Host "You can now use the following commands:" -ForegroundColor Yellow
Write-Host "  Start-Service cloudflared" -ForegroundColor Cyan
Write-Host "  Stop-Service cloudflared" -ForegroundColor Cyan
Write-Host "  Get-Service cloudflared" -ForegroundColor Cyan

pause
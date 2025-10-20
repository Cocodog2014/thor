# Update Cloudflare Tunnel Configuration to serve both frontend and backend
# Run as Administrator

$ErrorActionPreference = "Stop"

Write-Host "Updating Cloudflare Tunnel Configuration..." -ForegroundColor Cyan

# Backup existing config
$configPath = "C:\ProgramData\cloudflared\config.yml"
$backupPath = "C:\ProgramData\cloudflared\config.yml.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"

if (Test-Path $configPath) {
    Write-Host "Backing up existing config to: $backupPath" -ForegroundColor Yellow
    Copy-Item $configPath $backupPath
} else {
    Write-Host "No existing config found at $configPath" -ForegroundColor Yellow
}

# Copy new config
$sourceConfig = "A:\Thor\cloudflared-config-updated.yml"
if (Test-Path $sourceConfig) {
    Write-Host "Copying new config from: $sourceConfig" -ForegroundColor Green
    Copy-Item $sourceConfig $configPath -Force
    Write-Host "Config updated successfully!" -ForegroundColor Green
} else {
    Write-Host "Error: Source config not found at $sourceConfig" -ForegroundColor Red
    exit 1
}

# Restart the tunnel service if it's running
$service = Get-Service cloudflared -ErrorAction SilentlyContinue
if ($service -and $service.Status -eq "Running") {
    Write-Host "Restarting cloudflared service..." -ForegroundColor Cyan
    Restart-Service cloudflared
    Start-Sleep -Seconds 3
    $newStatus = (Get-Service cloudflared).Status
    Write-Host "Service status: $newStatus" -ForegroundColor $(if ($newStatus -eq "Running") {"Green"} else {"Red"})
} else {
    Write-Host "Cloudflared service is not running. Start it when ready." -ForegroundColor Yellow
}

Write-Host "`nConfiguration complete!" -ForegroundColor Green
Write-Host "`nURLs after restart:" -ForegroundColor Cyan
Write-Host "  Frontend: https://thor.360edu.org/" -ForegroundColor White
Write-Host "  Admin:    https://thor.360edu.org/admin/" -ForegroundColor White
Write-Host "  API:      https://thor.360edu.org/api/" -ForegroundColor White

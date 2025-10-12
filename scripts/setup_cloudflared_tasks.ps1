# Setup Cloudflared Scheduled Tasks with proper privileges
# Run this script as Administrator

Write-Host "Setting up Cloudflared control tasks..."

# Delete existing tasks if they exist
try {
    schtasks /Delete /TN "CloudflaredStart" /F 2>$null
    schtasks /Delete /TN "CloudflaredStop" /F 2>$null
    Write-Host "Cleaned up existing tasks"
} catch {
    Write-Host "No existing tasks to clean up"
}

# Create CloudflaredStart task (runs as SYSTEM with highest privileges)
$startResult = schtasks /Create /TN "CloudflaredStart" /SC ONCE /ST 00:00 /SD 01/01/1990 /TR "powershell -NoProfile -ExecutionPolicy Bypass -Command Start-Service cloudflared" /RU SYSTEM /RL HIGHEST /F

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ CloudflaredStart task created successfully"
} else {
    Write-Host "❌ Failed to create CloudflaredStart task"
    Write-Host $startResult
}

# Create CloudflaredStop task (runs as SYSTEM with highest privileges)
$stopResult = schtasks /Create /TN "CloudflaredStop" /SC ONCE /ST 00:00 /SD 01/01/1990 /TR "powershell -NoProfile -ExecutionPolicy Bypass -Command 'Stop-Service cloudflared -Force; Stop-Process -Name cloudflared -Force -ErrorAction SilentlyContinue'" /RU SYSTEM /RL HIGHEST /F

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ CloudflaredStop task created successfully"
} else {
    Write-Host "❌ Failed to create CloudflaredStop task"
    Write-Host $stopResult
}

Write-Host ""
Write-Host "Verifying tasks..."
schtasks /Query /TN "CloudflaredStart" | Select-String "TaskName|Status"
schtasks /Query /TN "CloudflaredStop" | Select-String "TaskName|Status"

Write-Host ""
Write-Host "Setup complete! The Django admin dashboard buttons should now work."
Write-Host "Tasks run as SYSTEM with highest privileges to control the cloudflared service."
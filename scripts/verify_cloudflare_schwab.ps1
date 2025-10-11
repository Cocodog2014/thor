# Verify Cloudflare + Schwab URLs for Thor
# Usage: Run in PowerShell after starting Django on port 8000

$domain = "https://thor.360edu.org"

Write-Host "Testing provider health via Cloudflare..." -ForegroundColor Cyan
try {
  $health = Invoke-WebRequest -Uri "$domain/api/schwab/provider/health/?provider=schwab" -UseBasicParsing -TimeoutSec 15
  Write-Host "Health status: $($health.StatusCode)" -ForegroundColor Green
} catch {
  Write-Host "Health request failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "Testing provider status via Cloudflare..." -ForegroundColor Cyan
try {
  $status = Invoke-WebRequest -Uri "$domain/api/schwab/provider/status/?provider=schwab" -UseBasicParsing -TimeoutSec 15
  Write-Host "Status code: $($status.StatusCode)" -ForegroundColor Green
} catch {
  Write-Host "Status request failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "Checking OAuth start (no follow) via Cloudflare..." -ForegroundColor Cyan
try {
  # We expect a 302 redirect to Schwab authorize
  $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
  $resp = Invoke-WebRequest -Uri "$domain/api/schwab/auth/login/" -MaximumRedirection 0 -WebSession $session -ErrorAction Stop
  Write-Host "Unexpected response: $($resp.StatusCode)" -ForegroundColor Yellow
} catch {
  if ($_.Exception.Response -and $_.Exception.Response.StatusCode -eq 302) {
    $loc = $_.Exception.Response.Headers["Location"]
    Write-Host "Got redirect to: $loc" -ForegroundColor Green
  } else {
    Write-Host "Auth start failed: $($_.Exception.Message)" -ForegroundColor Red
  }
}

Write-Host "Done." -ForegroundColor Cyan

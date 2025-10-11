#Requires -Version 5.1
<#
.
SYNOPSIS
    Configure Windows Service auto-recovery for the Cloudflared agent.

DESCRIPTION
    Sets service failure actions so Cloudflared restarts automatically if it crashes or is terminated by Windows.
    - First failure: restart after 5 seconds
    - Second failure: restart after 10 seconds
    - Subsequent (third) action: no action after 15 seconds
    - Reset failure count after 24 hours (86400 seconds)

    Also enables failure actions on non-crash failures (failureflag = 1).

NOTES
    Must be executed with Administrator privileges. The script will self-elevate if needed.

USAGE
    .\scripts\configure_cloudflared_recovery.ps1
#>

param(
    [string]$ServiceName = 'cloudflared'
)

function Test-IsAdministrator {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Confirm-Elevation {
    if (-not (Test-IsAdministrator)) {
        Write-Host 'Re-launching with elevated privileges...' -ForegroundColor Yellow
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = 'powershell.exe'
        $psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -ServiceName `"$ServiceName`""
        $psi.Verb = 'runas'
        try {
            $p = [System.Diagnostics.Process]::Start($psi)
            $p.WaitForExit()
            exit $p.ExitCode
        } catch {
            Write-Error 'Elevation was canceled or failed.'
            exit 1
        }
    }
}

Confirm-Elevation

Write-Host "Configuring service recovery for '$ServiceName'..." -ForegroundColor Cyan

# Validate the service exists
$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Error "Service '$ServiceName' not found. Ensure Cloudflared is installed."
    exit 2
}

# Configure failure actions: restart after 5s and 10s, then no action after 15s; reset counter after 24h
$failureArgs = @('failure', $ServiceName, 'reset=', '86400', 'actions=', 'restart/5000/restart/10000/""/15000')
Write-Host ("sc.exe {0}" -f ($failureArgs -join ' ')) -ForegroundColor DarkGray
& sc.exe @failureArgs | Out-String | Write-Output
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to set failure actions. Code: $LASTEXITCODE"
    exit $LASTEXITCODE
}

# Enable actions for non-crash failures as well
$failureFlagArgs = @('failureflag', $ServiceName, '1')
Write-Host ("sc.exe {0}" -f ($failureFlagArgs -join ' ')) -ForegroundColor DarkGray
& sc.exe @failureFlagArgs | Out-String | Write-Output
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to set failureflag. Code: $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host 'Service recovery rules applied.' -ForegroundColor Green

# Show summary
Write-Host 'Current failure actions:' -ForegroundColor Cyan
sc.exe qfailure $ServiceName | Out-String | Write-Output

# Optional: advise a restart if service is in a bad state
if ($svc.Status -eq 'StopPending' -or $svc.Status -eq 'StartPending') {
    Write-Host "Service is in state: $($svc.Status). You may want to run: Restart-Service $ServiceName" -ForegroundColor Yellow
}

exit 0

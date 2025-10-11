import subprocess
import sys
from typing import Literal, Tuple

Status = Literal["running", "stopped", "pending", "unknown"]


def _run(cmd: list[str]) -> Tuple[int, str, str]:
    """Run a command and return (code, stdout, stderr)."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def get_status() -> Status:
    """Return cloudflared Windows service status.

    Uses `sc.exe query cloudflared` and parses STATE to one of:
    - running
    - stopped
    - pending (start/stop pending)
    - unknown (error parsing)
    """
    if sys.platform != "win32":
        return "unknown"

    code, out, err = _run(["sc.exe", "query", "cloudflared"])  # nosec - trusted system binary
    if code != 0:
        return "unknown"

    text = (out or "") + "\n" + (err or "")
    t = text.lower()
    if "running" in t:
        return "running"
    if "stopped" in t:
        return "stopped"
    if "start pending" in t or "stop pending" in t or "pending" in t:
        return "pending"
    return "unknown"


def start() -> Tuple[bool, str]:
    """Trigger the CloudflaredStart scheduled task."""
    if sys.platform != "win32":
        return False, "Unsupported platform"
    code, out, err = _run(["schtasks", "/Run", "/TN", "CloudflaredStart"])  # nosec - system tool
    ok = code == 0
    msg = out or err
    return ok, msg


def stop() -> Tuple[bool, str]:
    """Trigger the CloudflaredStop scheduled task."""
    if sys.platform != "win32":
        return False, "Unsupported platform"
    code, out, err = _run(["schtasks", "/Run", "/TN", "CloudflaredStop"])  # nosec
    ok = code == 0
    msg = out or err
    return ok, msg


def toggle() -> Tuple[Status, str]:
    """Toggle the service based on current status; return (new_status, message)."""
    status = get_status()
    if status == "running":
        ok, msg = stop()
    elif status == "stopped":
        ok, msg = start()
    else:
        return status, "Service is pending or unknown; try again shortly."

    if not ok:
        return status, msg or "Failed to trigger scheduled task"

    # Brief polling loop to see if state flips
    import time

    for _ in range(10):  # ~10 seconds
        time.sleep(1)
        ns = get_status()
        if status == "running" and ns in {"stopped", "pending"}:
            return ns, msg
        if status == "stopped" and ns in {"running", "pending"}:
            return ns, msg
    return get_status(), msg

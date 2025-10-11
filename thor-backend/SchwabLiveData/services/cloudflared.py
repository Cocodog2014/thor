import re
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


def get_status(treat_stop_pending_as_stopped: bool = True) -> Status:
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

    # Parse the numeric STATE code to avoid locale/text variations.
    # Expected line example: "STATE              : 1  STOPPED"
    text = (out or "") + "\n" + (err or "")
    m = re.search(r"STATE\s*:\s*(\d+)\s+([A-Z_]+)", text, flags=re.IGNORECASE)
    if not m:
        # Fallback to simple keyword checks if pattern isn't found
        t = text.lower()
        if "running" in t:
            return "running"
        if "stopped" in t:
            return "stopped"
        if "pending" in t:
            return "pending"
        return "unknown"

    try:
        code_num = int(m.group(1))
    except Exception:
        code_num = -1

    # Map Windows service state codes
    # 1: STOPPED, 2: START_PENDING, 3: STOP_PENDING, 4: RUNNING,
    # 5: CONTINUE_PENDING, 6: PAUSE_PENDING, 7: PAUSED
    if code_num == 4:
        return "running"
    if code_num == 1:
        return "stopped"
    if code_num in {2, 5, 6}:
        return "pending"
    if code_num == 3:
        # STOP_PENDING can be treated as stopped (idle view) or pending (action view)
        return "stopped" if treat_stop_pending_as_stopped else "pending"
    if code_num == 7:
        # Treat paused similar to stopped for our simple control surface
        return "stopped"
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
        ns = get_status(treat_stop_pending_as_stopped=False)
        if status == "running" and ns in {"stopped", "pending"}:
            return ns, msg
        if status == "stopped" and ns in {"running", "pending"}:
            return ns, msg
    return get_status(), msg

from django.contrib.admin.sites import site
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.contrib import messages

from .services import cloudflared
import time


def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_active and u.is_superuser)(view_func)


@superuser_required
@never_cache
def cloudflared_control(request):
    action = request.GET.get("action")
    status = cloudflared.get_status()
    msg_text = None

    if action == "toggle":
        new_status, msg = cloudflared.toggle()
        status = new_status
        msg_text = msg
    elif action == "start":
        ok, msg = cloudflared.start()
        msg_text = msg
        if ok:
            messages.success(request, "Triggered Cloudflared start")
            # Briefly poll for RUNNING
            for _ in range(10):  # ~10 seconds
                time.sleep(1)
                status = cloudflared.get_status(treat_stop_pending_as_stopped=False, prefer_process_signal=True)
                if status in {"running", "pending"}:  # show progress quickly
                    break
        else:
            messages.error(request, f"Start failed: {msg}")
    elif action == "stop":
        ok, msg = cloudflared.stop()
        msg_text = msg
        if ok:
            messages.success(request, "Triggered Cloudflared stop")
            # Briefly poll for STOPPED
            for _ in range(10):
                time.sleep(1)
                status = cloudflared.get_status(treat_stop_pending_as_stopped=False, prefer_process_signal=True)
                if status in {"stopped", "pending"}:  # show progress quickly
                    break
        else:
            messages.error(request, f"Stop failed: {msg}")

    context = {
        "site_header": site.site_header,
        "site_title": site.site_title,
        "title": "Cloudflared Tunnel Control",
        "status": status,
        "message": msg_text,
        "has_permission": True,
    }
    return render(request, "admin/schwab_cloudflared_control.html", context)

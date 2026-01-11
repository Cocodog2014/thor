from __future__ import annotations

from django import template
from django.urls import reverse

from users.models import CustomUser

register = template.Library()


@register.inclusion_tag("admin/_pending_approvals_panel.html", takes_context=True)
def pending_approvals_panel(context, limit: int = 10):
    qs = (
        CustomUser.objects
        .filter(is_active=True, is_approved=False)
        .order_by("-created_at")
    )

    pending_users = list(qs[: int(limit)])
    pending_count = qs.count()

    return {
        "pending_count": pending_count,
        "pending_users": pending_users,
        "pending_list_url": reverse("admin:users_customuser_changelist") + "?approval=pending",
        "title": "New users pending approval",
    }

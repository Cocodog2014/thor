"""Utilities for resolving which data feeds power downstream consumer apps."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

from django.db.models import Prefetch, QuerySet

from ..models import ConsumerApp, FeedAssignment


@dataclass(frozen=True)
class FeedInfo:
    """Resolved feed details returned to API clients."""

    code: str
    display_name: str
    connection_type: str
    priority: int
    is_primary: bool


@dataclass(frozen=True)
class RoutingPlan:
    """Summary describing how a consumer app should source its market data."""

    consumer_code: str
    consumer_name: str
    feeds: List[FeedInfo]
    primary_feed: Optional[FeedInfo]

    @property
    def primary_code(self) -> Optional[str]:
        return self.primary_feed.code if self.primary_feed else None


def _active_assignments(assignments: QuerySet[FeedAssignment]) -> Iterable[FeedAssignment]:
    """Return assignments that are enabled on both sides."""

    for assignment in assignments:
        if assignment.is_active:
            yield assignment


def build_routing_plan(consumer_code: str) -> RoutingPlan:
    """Construct a routing plan for the given consumer app code."""

    consumer = (
        ConsumerApp.objects.filter(code__iexact=consumer_code)
        .prefetch_related(
            Prefetch(
                "assignments",
                queryset=FeedAssignment.objects.select_related("feed").order_by("priority", "-is_primary", "feed__display_name"),
            )
        )
        .first()
    )

    if consumer is None:
        raise ConsumerApp.DoesNotExist(f"Consumer app '{consumer_code}' is not registered")

    assignments = list(_active_assignments(consumer.assignments.all()))

    feeds = [
        FeedInfo(
            code=a.feed.code,
            display_name=a.feed.display_name,
            connection_type=a.feed.connection_type,
            priority=a.priority,
            is_primary=a.is_primary,
        )
        for a in assignments
    ]

    # Determine primary feed preference order: explicit primary flag, then lowest priority, then default fallback.
    primary_feed = None
    for info in feeds:
        if info.is_primary:
            primary_feed = info
            break

    if primary_feed is None and feeds:
        primary_feed = min(feeds, key=lambda info: info.priority)

    if primary_feed is None and consumer.default_feed and consumer.default_feed.is_active:
        primary_feed = FeedInfo(
            code=consumer.default_feed.code,
            display_name=consumer.default_feed.display_name,
            connection_type=consumer.default_feed.connection_type,
            priority=0,
            is_primary=False,
        )

    return RoutingPlan(
        consumer_code=consumer.code,
        consumer_name=consumer.display_name,
        feeds=feeds,
        primary_feed=primary_feed,
    )

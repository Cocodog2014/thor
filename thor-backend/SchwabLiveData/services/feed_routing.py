"""Utilities for resolving which data feeds power downstream consumer apps."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..models import ConsumerApp, DataFeed

from ..models import ConsumerApp, DataFeed


@dataclass(frozen=True)
class FeedInfo:
    """Resolved feed details returned to API clients."""

    code: str
    display_name: str
    connection_type: str
    provider_key: str
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


def build_routing_plan(consumer_code: str) -> RoutingPlan:
    """Construct a routing plan for the given consumer app code."""

    try:
        consumer = ConsumerApp.objects.select_related('primary_feed', 'fallback_feed').get(code__iexact=consumer_code)
    except ConsumerApp.DoesNotExist:
        raise ConsumerApp.DoesNotExist(f"Consumer app '{consumer_code}' is not registered")

    feeds = []
    primary_feed = None

    # Add primary feed if exists and active
    if consumer.primary_feed and consumer.primary_feed.is_active:
        primary_info = FeedInfo(
            code=consumer.primary_feed.code,
            display_name=consumer.primary_feed.display_name,
            connection_type=consumer.primary_feed.connection_type,
            provider_key=consumer.primary_feed.provider_key,
            priority=1,
            is_primary=True,
        )
        feeds.append(primary_info)
        primary_feed = primary_info

    # Add fallback feed if exists, active, and different from primary
    if (consumer.fallback_feed and 
        consumer.fallback_feed.is_active and 
        consumer.fallback_feed != consumer.primary_feed):
        
        fallback_info = FeedInfo(
            code=consumer.fallback_feed.code,
            display_name=consumer.fallback_feed.display_name,
            connection_type=consumer.fallback_feed.connection_type,
            provider_key=consumer.fallback_feed.provider_key,
            priority=2,
            is_primary=False,
        )
        feeds.append(fallback_info)
        
        # If no primary feed is set, use fallback as primary
        if primary_feed is None:
            primary_feed = fallback_info

    return RoutingPlan(
        consumer_code=consumer.code,
        consumer_name=consumer.display_name,
        feeds=feeds,
        primary_feed=primary_feed,
    )

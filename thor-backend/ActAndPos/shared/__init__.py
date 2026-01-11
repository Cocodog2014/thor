"""Shared (broker-agnostic) contracts and utilities for ActAndPos.

This package is intentionally dependency-light so both PAPER and LIVE
implementations can import it without pulling in broker-specific code.
"""

from .formatting import format_money, format_pct

__all__ = [
	"format_money",
	"format_pct",
]

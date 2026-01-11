"""Account statement composition (broker-agnostic).

This will become the shared, canonical way to build account statements so both
PAPER and LIVE can feed the same response shape.

For now it's scaffolding only.
"""

from __future__ import annotations


class StatementService:
    def build_statement(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

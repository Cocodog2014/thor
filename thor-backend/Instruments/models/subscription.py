"""Legacy Schwab subscription table.

This project previously stored per-user Schwab streaming intent in a dedicated
`instrument_schwab_subscription` table.

Canonical streaming intent is now expressed via:
  UserInstrumentWatchlistItem(enabled=True, stream=True)

The DB table is intentionally left in place for rollback/forensics, but the Django
model has been removed to prevent new code from depending on it.
"""


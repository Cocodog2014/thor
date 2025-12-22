from ThorTrading.models.MarketSession import MarketSession


def update_session_volume_for_country(country: str, enriched_rows):
    """
    Deprecated: per-tick session volume accumulation is removed to avoid
    double-counting (quote volumes are typically cumulative). Session volume
    should be derived from flushed intraday bars instead.
    """
    return {'session_volume_updates': 0}


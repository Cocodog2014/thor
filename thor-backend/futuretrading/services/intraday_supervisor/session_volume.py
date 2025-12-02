from FutureTrading.models.MarketSession import MarketSession

def update_session_volume_for_country(country: str, enriched_rows):
    """Accumulate session_volume on latest MarketSession per future.

    Returns counts dict: {'session_volume_updates': int}
    """
    if not enriched_rows:
        return {'session_volume_updates': 0}

    counts = {'session_volume_updates': 0}

    for row in enriched_rows:
        sym = row.get('instrument', {}).get('symbol')
        if not sym:
            continue
        future = sym.lstrip('/').upper()
        vol = int(row.get('volume') or 0)

        session = (
            MarketSession.objects
            .filter(country=country, future=future)
            .order_by('-session_number')
            .first()
        )
        if not session:
            continue
        try:
            sv = session.session_volume or 0
            session.session_volume = sv + vol
            session.save(update_fields=['session_volume'])
            counts['session_volume_updates'] += 1
        except Exception:
            pass

    return counts

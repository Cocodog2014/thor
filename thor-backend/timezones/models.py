from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime, time, timedelta, date as date_cls
import pytz


class Market(models.Model):
    """
    Represents stock markets around the world for monitoring while trading US markets
    """
    # Basic market information
    country = models.CharField(max_length=50)
    
    # Timezone information (Django will handle DST automatically)
    timezone_name = models.CharField(max_length=50)  # e.g., "Asia/Tokyo", "Europe/London"
    
    # Trading hours (in local market time)
    market_open_time = models.TimeField()   # e.g., 09:00
    market_close_time = models.TimeField()  # e.g., 15:00
    
    # Market status - controls data collection
    status = models.CharField(
        max_length=10,
        choices=[
            ('OPEN', 'Open'),
            ('CLOSED', 'Closed'),
        ],
        default='CLOSED'
    )
    
    # Market configuration
    is_active = models.BooleanField(default=True)
    
    # Additional market info
    currency = models.CharField(max_length=3, blank=True)  # USD, JPY, EUR, etc.
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['country']
        verbose_name = 'Market'
        verbose_name_plural = 'Markets'
    
    def __str__(self):
        return f"{self.country} ({self.timezone_name})"
    
    def get_display_name(self):
        """Get the display name for the frontend based on user requirements"""
        display_names = {
            'Japan': 'Tokyo',
            'Shenzhen': 'Shenzhen', 
            'Hong Kong': 'Hong Kong',
            'China': 'Shanghai',
            'India': 'Bombay',
            'Netherlands': 'Amsterdam',
            'France': 'France',
            'Germany': 'Frankfurt',
            'Spain': 'Spain',
            'United Kingdom': 'London',
            'Pre_USA': 'Pre_USA',
            'USA': 'USA',
            'Canada': 'Toronto',
            'Mexico': 'Mexican'
        }
        return display_names.get(self.country, self.country)
    
    def get_sort_order(self):
        """Get sort order based on user's requested market sequence"""
        order_map = {
            'Japan': 1,      # Tokyo
            'Shenzhen': 2,   # Shenzhen
            'Hong Kong': 3,  # Hong Kong
            'China': 4,      # Shanghai
            'India': 5,      # Bombay
            'Netherlands': 6, # Amsterdam
            'France': 7,     # France
            'Germany': 8,    # Frankfurt
            'Spain': 9,      # Spain
            'United Kingdom': 10, # London
            'Pre_USA': 11,   # Pre_USA
            'USA': 12,       # USA
            'Canada': 13,    # Toronto
            'Mexico': 14     # Mexican
        }
        return order_map.get(self.country, 999)
    
    def get_current_market_time(self):
        """Get current time in market's timezone with full date/time info"""
        try:
            tz = pytz.timezone(self.timezone_name)
            now = datetime.now(tz)
            return {
                'datetime': now,
                'year': now.year,
                'month': now.month,
                'date': now.day,
                'day': now.strftime('%a'),  # Mon, Tue, Wed, etc.
                'day_number': now.weekday(),  # 0=Monday, 6=Sunday
                'time': now.strftime('%H:%M:%S'),
                'formatted_12h': now.strftime('%I:%M:%S %p'),
                'formatted_24h': now.strftime('%H:%M:%S'),
                'timestamp': now.timestamp(),
                'utc_offset': now.strftime('%z'),  # Auto-calculated with DST
                'dst_active': bool(now.dst()),  # Auto-detected DST status
            }
        except Exception as e:
            return None
    
    def should_collect_data(self):
        """Only collect if market status is OPEN (controlled manually based on US market status)"""
        market_time_data = self.get_current_market_time()
        if not market_time_data:
            return False
        # Never collect on weekends (Saturday=5, Sunday=6)
        if market_time_data.get('day_number', 0) >= 5:
            return False
        return self.is_active and self.status == 'OPEN'
    
    def is_market_open_now(self):
        """Check if this specific market is currently in trading hours"""
        market_time_data = self.get_current_market_time()
        if not market_time_data:
            return False
        # Markets are closed on weekends
        if market_time_data.get('day_number', 0) >= 5:
            return False
        
        current_time = market_time_data['datetime'].time()
        
        # Check if current time is between open and close
        if self.market_open_time <= self.market_close_time:
            # Normal trading day (e.g., 9:00 - 17:00)
            return self.market_open_time <= current_time <= self.market_close_time
        else:
            # Overnight trading (e.g., 22:00 - 06:00)
            return current_time >= self.market_open_time or current_time <= self.market_close_time
    
    def get_market_status(self):
        """Compute enriched market status and next event information (tz-aware).

        Returns a dict with:
        - current_state: OPEN | PREOPEN | PRECLOSE | CLOSED | HOLIDAY_CLOSED
        - next_open_at: ISO tz-aware string
        - next_close_at: ISO tz-aware string
        - next_event: 'open' | 'close'
        - seconds_to_next_event: int seconds until next_event from now (>=0)
        Plus existing fields for backward compatibility.
        """
        market_time = self.get_current_market_time()
        if not market_time or not self.is_active:
            return None

        tz = pytz.timezone(self.timezone_name)
        now_local = market_time['datetime']  # tz-aware

        # Helpers for trading day / holidays
        def is_holiday(d: datetime) -> bool:
            local_date = d.date()
            try:
                return self.holidays.filter(date=local_date, full_day=True).exists()
            except Exception:
                # Table might not exist yet if migrations haven't been applied
                return False

        def is_trading_day(d: datetime) -> bool:
            # Weekday: Monday=0..Sunday=6; closed on weekends or holidays
            return d.weekday() < 5 and not is_holiday(d)

        def combine_local(d: datetime, t: time) -> datetime:
            naive = datetime(d.year, d.month, d.day, t.hour, t.minute, t.second)
            return tz.localize(naive)

        # Compute today's canonical open/close datetimes
        open_today = combine_local(now_local, self.market_open_time)
        close_today = combine_local(now_local, self.market_close_time)

        # Handle overnight sessions (open > close) by rolling close to next day
        if self.market_open_time > self.market_close_time:
            close_today = close_today + timedelta(days=1)

        # Next trading day helper
        def next_trading_day(start: datetime) -> datetime:
            d = start + timedelta(days=1)
            # iterate until weekday and not holiday
            while not is_trading_day(d):
                d += timedelta(days=1)
            return d

        # Compute next open datetime
        def compute_next_open(now_dt: datetime) -> datetime:
            # If today is trading day and before close
            if is_trading_day(now_dt):
                if now_dt < open_today:
                    return open_today
                elif now_dt <= close_today:
                    # next open is next trading day's open
                    nd = next_trading_day(now_dt)
                    return combine_local(nd, self.market_open_time)
            # Otherwise find the next trading day from tomorrow
            nd = next_trading_day(now_dt)
            return combine_local(nd, self.market_open_time)

        # Compute next close datetime
        def compute_next_close(now_dt: datetime) -> datetime:
            if is_trading_day(now_dt) and open_today <= now_dt <= close_today:
                return close_today
            # If before open today and today is trading day, today's close
            if is_trading_day(now_dt) and now_dt < open_today:
                return close_today
            # Else next trading day's close
            nd = next_trading_day(now_dt)
            close_nd = combine_local(nd, self.market_close_time)
            if self.market_open_time > self.market_close_time:
                close_nd = close_nd + timedelta(days=1)
            return close_nd

        # Determine base flags
        weekend = market_time.get('day_number', 0) >= 5
        holiday_today = is_holiday(now_local)
        in_hours = False if (weekend or holiday_today) else self.is_market_open_now()

        # Windows (minutes) for PREOPEN and PRECLOSE
        PREOPEN_MIN = 60
        PRECLOSE_MIN = 15

        next_open_at_dt = compute_next_open(now_local)
        next_close_at_dt = compute_next_close(now_local)

        # Determine current_state and next_event
        if holiday_today:
            current_state = 'HOLIDAY_CLOSED'
            next_event = 'open'
            target_dt = next_open_at_dt
        elif in_hours:
            # within trading hours
            # preclose window if close - now <= PRECLOSE_MIN
            if (next_close_at_dt - now_local) <= timedelta(minutes=PRECLOSE_MIN):
                current_state = 'PRECLOSE'
            else:
                current_state = 'OPEN'
            next_event = 'close'
            target_dt = next_close_at_dt
        else:
            # Closed: check preopen window if open - now <= PREOPEN_MIN and today is trading day
            if is_trading_day(now_local) and now_local < open_today and (open_today - now_local) <= timedelta(minutes=PREOPEN_MIN):
                current_state = 'PREOPEN'
            else:
                current_state = 'CLOSED'
            next_event = 'open'
            target_dt = next_open_at_dt

        seconds_to_next_event = max(0, int((target_dt - now_local).total_seconds()))

        # Preserve prior fields and add enriched fields
        effective_status = 'CLOSED' if weekend else self.status
        return {
            'country': self.country,
            'timezone': self.timezone_name,
            'current_time': market_time,
            'market_open': self.market_open_time.strftime('%H:%M'),
            'market_close': self.market_close_time.strftime('%H:%M'),
            'is_in_trading_hours': in_hours,
            'status': effective_status,
            'should_collect_data': False if weekend else self.should_collect_data(),
            # New enriched fields
            'current_state': current_state,
            'next_open_at': next_open_at_dt.isoformat(),
            'next_close_at': next_close_at_dt.isoformat(),
            'next_event': next_event,
            'seconds_to_next_event': seconds_to_next_event,
            'is_holiday_today': holiday_today,
        }


class USMarketStatus(models.Model):
    """
    Tracks US market status - controls whether we collect ANY data
    """
    date = models.DateField(unique=True)
    is_trading_day = models.BooleanField(default=True)  # False for weekends/holidays
    holiday_name = models.CharField(max_length=100, blank=True)  # e.g., "Memorial Day"
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'US Market Status'
        verbose_name_plural = 'US Market Status'
    
    def __str__(self):
        if self.is_trading_day:
            return f"{self.date} - Trading Day"
        else:
            return f"{self.date} - Closed ({self.holiday_name or 'Weekend'})"
    
    # ------------------------
    # US Holiday Computations
    # ------------------------
    @staticmethod
    def _nth_weekday(year: int, month: int, weekday: int, n: int):
        """Return date of the nth weekday in a month. weekday: Monday=0..Sunday=6"""
        from datetime import date, timedelta
        d = date(year, month, 1)
        # Advance to first desired weekday
        days_ahead = (weekday - d.weekday()) % 7
        d += timedelta(days=days_ahead)
        # Add (n-1) weeks
        d += timedelta(weeks=n-1)
        return d

    @staticmethod
    def _last_weekday(year: int, month: int, weekday: int):
        """Return date of the last weekday in a month. weekday: Monday=0..Sunday=6"""
        from datetime import date, timedelta
        # Start from first day of next month, step back
        if month == 12:
            d = date(year + 1, 1, 1)
        else:
            d = date(year, month + 1, 1)
        d -= timedelta(days=1)  # last day of target month
        days_back = (d.weekday() - weekday) % 7
        return d - timedelta(days=days_back)

    @staticmethod
    def _easter_sunday(year: int):
        """Compute Gregorian Easter Sunday (Anonymous Gregorian algorithm)."""
        from datetime import date
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = ((h + l - 7 * m + 114) % 31) + 1
        return date(year, month, day)

    @staticmethod
    def _observed(d):
        """Apply NYSE observed rules: if holiday on Sat -> observe Friday; if Sunday -> observe Monday."""
        from datetime import timedelta
        if d.weekday() == 5:  # Saturday
            return d - timedelta(days=1)
        if d.weekday() == 6:  # Sunday
            return d + timedelta(days=1)
        return d

    @classmethod
    def us_market_holidays(cls, year: int):
        """Return a set of dates when US equity markets are fully closed for the given year (observed)."""
        from datetime import date, timedelta
        MON, TUE, WED, THU, FRI = 0, 1, 2, 3, 4

        holidays = set()

        # New Year's Day (January 1, observed)
        holidays.add(cls._observed(date(year, 1, 1)))

        # Martin Luther King Jr. Day (Third Monday in January)
        holidays.add(cls._nth_weekday(year, 1, MON, 3))

        # Presidents' Day (Third Monday in February)
        holidays.add(cls._nth_weekday(year, 2, MON, 3))

        # Good Friday (Friday before Easter Sunday)
        easter = cls._easter_sunday(year)
        good_friday = easter - timedelta(days=2)
        holidays.add(good_friday)

        # Memorial Day (Last Monday in May)
        holidays.add(cls._last_weekday(year, 5, MON))

        # Juneteenth (June 19, observed)
        holidays.add(cls._observed(date(year, 6, 19)))

        # Independence Day (July 4, observed)
        holidays.add(cls._observed(date(year, 7, 4)))

        # Labor Day (First Monday in September)
        holidays.add(cls._nth_weekday(year, 9, MON, 1))

        # Thanksgiving Day (Fourth Thursday in November)
        holidays.add(cls._nth_weekday(year, 11, THU, 4))

        # Christmas Day (December 25, observed)
        holidays.add(cls._observed(date(year, 12, 25)))

        return holidays

    @classmethod
    def is_us_market_open_today(cls):
        """Check if US markets are open today - controls all data collection"""
        from datetime import date
        today = date.today()

        # First: if there's an explicit DB record, use it (manual override)
        try:
            status = cls.objects.get(date=today)
            return status.is_trading_day
        except cls.DoesNotExist:
            pass

        # Weekend check
        if today.weekday() >= 5:  # Saturday/Sunday
            return False

        # US Holiday check (observed rules applied)
        holidays = cls.us_market_holidays(today.year)
        if today in holidays:
            return False

        return True


class MarketDataSnapshot(models.Model):
    """
    Real-time market data snapshots - only collected when US markets are open
    """
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='snapshots')
    
    # Timestamp when data was collected
    collected_at = models.DateTimeField(auto_now_add=True)
    
    # Market time data at collection
    market_year = models.IntegerField()
    market_month = models.IntegerField()
    market_date = models.IntegerField()
    market_day = models.CharField(max_length=3)  # Mon, Tue, Wed
    market_time = models.TimeField()
    
    # Market status at collection
    market_status = models.CharField(max_length=10)  # OPEN, CLOSED
    utc_offset = models.CharField(max_length=10)  # +09:00, -05:00, etc.
    dst_active = models.BooleanField()
    is_in_trading_hours = models.BooleanField()
    
    class Meta:
        ordering = ['-collected_at']
        verbose_name = 'Market Data Snapshot'
        verbose_name_plural = 'Market Data Snapshots'
        indexes = [
            models.Index(fields=['market', '-collected_at']),
            models.Index(fields=['market_status']),
        ]
    
    def __str__(self):
        return f"{self.market.country} - {self.market_status} at {self.collected_at}"


class MarketHoliday(models.Model):
    """Per-market holiday days (full-day closures). Partial days ignored for now."""
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='holidays')
    date = models.DateField()
    name = models.CharField(max_length=100, blank=True)
    full_day = models.BooleanField(default=True)

    class Meta:
        unique_together = ('market', 'date')
        ordering = ['date']
        verbose_name = 'Market Holiday'
        verbose_name_plural = 'Market Holidays'

    def __str__(self):
        return f"{self.market.country} holiday on {self.date} ({'Full' if self.full_day else 'Partial'})"


class UserMarketWatchlist(models.Model):
    """
    User's personalized market watchlist for frontend display
    """
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='market_watchlist')
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=100, blank=True)  # Custom name for the market
    is_primary = models.BooleanField(default=False)  # User's primary/home market
    order = models.PositiveIntegerField(default=0)  # Display order
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        unique_together = ['user', 'market']
        verbose_name = 'User Market Watchlist'
        verbose_name_plural = 'User Market Watchlists'
    
    def __str__(self):
        display = self.display_name if self.display_name else str(self.market)
        return f"{self.user.username} - {display}"
    
    def save(self, *args, **kwargs):
        if self.is_primary:
            # Ensure only one primary market per user
            UserMarketWatchlist.objects.filter(
                user=self.user, 
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
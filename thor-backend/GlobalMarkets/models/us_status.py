from django.db import models


class USMarketStatus(models.Model):
    """
    Tracks US market status - controls whether we collect ANY data
    """
    date = models.DateField(unique=True)
    is_trading_day = models.BooleanField(default=True)
    holiday_name = models.CharField(max_length=100, blank=True)

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

    @staticmethod
    def _nth_weekday(year: int, month: int, weekday: int, n: int):
        from datetime import date, timedelta
        d = date(year, month, 1)
        days_ahead = (weekday - d.weekday()) % 7
        d += timedelta(days=days_ahead)
        d += timedelta(weeks=n-1)
        return d

    @staticmethod
    def _last_weekday(year: int, month: int, weekday: int):
        from datetime import date, timedelta
        if month == 12:
            d = date(year + 1, 1, 1)
        else:
            d = date(year, month + 1, 1)
        d -= timedelta(days=1)
        days_back = (d.weekday() - weekday) % 7
        return d - timedelta(days=days_back)

    @staticmethod
    def _easter_sunday(year: int):
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
        from datetime import timedelta
        if d.weekday() == 5:
            return d - timedelta(days=1)
        if d.weekday() == 6:
            return d + timedelta(days=1)
        return d

    @classmethod
    def us_market_holidays(cls, year: int):
        from datetime import date
        MON, TUE, WED, THU, FRI = 0, 1, 2, 3, 4

        holidays = set()
        holidays.add(cls._observed(date(year, 1, 1)))
        holidays.add(cls._nth_weekday(year, 1, MON, 3))
        holidays.add(cls._nth_weekday(year, 2, MON, 3))
        easter = cls._easter_sunday(year)
        good_friday = easter - __import__('datetime').timedelta(days=2)
        holidays.add(good_friday)
        holidays.add(cls._last_weekday(year, 5, MON))
        holidays.add(cls._observed(date(year, 6, 19)))
        holidays.add(cls._observed(date(year, 7, 4)))
        holidays.add(cls._nth_weekday(year, 9, MON, 1))
        holidays.add(cls._nth_weekday(year, 11, THU, 4))
        holidays.add(cls._observed(date(year, 12, 25)))
        return holidays

    @classmethod
    def is_us_market_open_today(cls):
        from datetime import date
        today = date.today()
        try:
            status = cls.objects.get(date=today)
            return status.is_trading_day
        except cls.DoesNotExist:
            pass
        if today.weekday() >= 5:
            return False
        holidays = cls.us_market_holidays(today.year)
        if today in holidays:
            return False
        return True

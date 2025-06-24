from datetime import datetime, timedelta
import pandas_market_calendars as mcal


def get_last_workday(date):
    if date.weekday() == 5:  # Saturday
        return date - timedelta(days=1)
    elif date.weekday() == 6:  # Sunday
        return date - timedelta(days=2)
    else:
        return date

def get_last_trading_day():
    nyse = mcal.get_calendar("NYSE")
    now = datetime.now()
    schedule = nyse.schedule(start_date=now - timedelta(days=10), end_date=now)
    return schedule.index[-1].date()

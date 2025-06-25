from datetime import datetime, timedelta
import pandas_market_calendars as mcal
import pytz


def get_last_workday(date):
    if date.weekday() == 5:  # Saturday
        return date - timedelta(days=1)
    elif date.weekday() == 6:  # Sunday
        return date - timedelta(days=2)
    else:
        return date


def get_last_trading_day():
    nyse = mcal.get_calendar("NYSE")
    eastern = pytz.timezone("US/Eastern")
    now = datetime.now(tz=eastern)

    schedule = nyse.schedule(start_date=now - timedelta(days=10), end_date=now)
    trading_days = schedule.index

    if now.time() < datetime.strptime("16:00", "%H:%M").time():
        return trading_days[-2].date()
    else:
        if trading_days[-1].date() == now.date():
            return trading_days[-1].date()
        else:
            return trading_days[-2].date()

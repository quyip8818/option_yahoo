from time import sleep

import yfinance as yf

from src.utils.utils import round_num


def get_stock_info(symbol):
    try:
        print(f"yf stock info: {symbol}")
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        sleep(0.3)
        current_price = round_num(info.get("lastPrice"), 2)
        market_cap = round_num(info.get("marketCap"), 0)
        return current_price, market_cap
    except Exception as e:
        if "Rate limited" in e.args[0]:
            sleep(1)
            raise e
        return None, None


def localize_date(date):
    if date.tz is None:
        date = date.tz_localize("UTC")
    return date.tz_convert("US/Eastern").date.astype(str)


def get_earning_data(symbol):
    ticker = yf.Ticker(symbol)
    df = ticker.get_earnings_dates(limit=100)
    df = df[df["Reported EPS"].notna()]
    date = localize_date(df.index)
    return "|".join(date)

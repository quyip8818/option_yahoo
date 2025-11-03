import os
from datetime import datetime
from typing import List, Optional
import pandas as pd
from src.utils.finnhub_utils import get_stock_price, get_all_earnings_dates

BATCH_SIZE = 50
SAVE_INTERVAL = 10


def _process_earnings_dates(dates: List[str]) -> Optional[pd.DatetimeIndex]:
    if not dates:
        return None
    dt_index = pd.to_datetime(sorted(dates), errors="coerce")
    result = dt_index[pd.notna(dt_index)]
    return result if len(result) > 0 else None


def fillin_market_data(path, date):
    if not os.path.exists(path):
        return
    df = pd.read_csv(path)
    date = pd.Timestamp(date)
    current_date = date.to_pydatetime()

    for col in ["next_report_days", "next_report_date", "current_price"]:
        if col not in df.columns:
            df[col] = None

    symbols_earnings = [
        df.loc[idx, "symbol"]
        for idx in range(len(df))
        if pd.isna(df.loc[idx, "next_report_days"])
        or pd.isna(df.loc[idx, "next_report_date"])
    ]

    symbols_price = [
        (df.loc[idx, "symbol"], idx)
        for idx in range(len(df))
        if pd.isna(df.loc[idx, "current_price"])
    ]

    indices_map = {df.loc[idx, "symbol"]: idx for idx in range(len(df))}

    if symbols_earnings:
        print("Fetching earnings dates for all stocks...")
        earnings_dict_raw = get_all_earnings_dates(current_date)
        earnings_dict = {
            symbol: _process_earnings_dates(dates)
            for symbol, dates in earnings_dict_raw.items()
        }

        updated_count = 0
        for symbol in symbols_earnings:
            idx = indices_map[symbol]
            rep_dates = earnings_dict.get(symbol)
            if rep_dates is None or len(rep_dates) == 0:
                continue
            next_report_days, next_report_date = get_next_report_days(date, rep_dates)
            if next_report_days is not None:
                df.loc[idx, "next_report_days"] = next_report_days
                updated_count += 1
            if next_report_date is not None:
                df.loc[idx, "next_report_date"] = next_report_date
        df.to_csv(path, index=False)
        print(f"Updated earnings dates for {updated_count}/{len(symbols_earnings)} symbols")

    if symbols_price:
        for count, (symbol, idx) in enumerate(symbols_price, 1):
            try:
                current_price = get_stock_price(symbol)
                if current_price is not None:
                    df.loc[idx, "current_price"] = current_price
                if count % SAVE_INTERVAL == 0:
                    df.to_csv(path, index=False)
                    print(f"Processed {count}/{len(symbols_price)} prices")
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
                df.to_csv(path, index=False)
                continue
        df.to_csv(path, index=False)

    df.to_csv(path, index=False)
    print("Processed all symbols")


def get_next_report_days(date, rep_dates):
    if rep_dates is None or len(rep_dates) == 0:
        return None, None
    for rep_date in rep_dates:
        delta = rep_date - date
        next_report_days = delta.days
        if next_report_days >= 0:
            return int(next_report_days), rep_date
    return None, None


def get_pass_report_days(date, rep_dates):
    if rep_dates is None:
        return None
    for rep_date in reversed(rep_dates):
        pass_report_days = (date - rep_date).days
        if pass_report_days >= 0:
            return pass_report_days
    return None


def fillin_finance_report_date(df, current_date):
    date = pd.Timestamp(current_date)

    if "symbol" in df.columns:
        df = df.copy()
    else:
        df = df.reset_index()

    unique_symbols = df["symbol"].dropna().unique().tolist()
    if not unique_symbols:
        print("No symbols found in dataframe")
        return df

    print("Fetching earnings dates for all stocks...")
    earnings_dict_raw = get_all_earnings_dates(current_date)
    reports = {
        symbol: _process_earnings_dates(dates)
        for symbol, dates in earnings_dict_raw.items()
    }

    df[["next_report_days", "next_report_date"]] = df.apply(
        lambda r: pd.Series(get_next_report_days(date, reports.get(r["symbol"]))),
        axis=1,
    )
    df["pass_report_days"] = df.apply(
        lambda r: get_pass_report_days(date, reports.get(r["symbol"])), axis=1
    )

    current_headers = [col for col in df.columns if col not in ["pass_report_days", "next_report_days", "next_report_date"]]
    return df[["pass_report_days", "next_report_days", "next_report_date"] + current_headers]

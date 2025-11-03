import os
from typing import List, Optional
import pandas as pd
from src.utils.finnhub_utils import get_stock_price, get_batch_earnings_dates

BATCH_SIZE = 50
SAVE_INTERVAL = 10


def _process_earnings_dates(dates: List[str]) -> Optional[pd.DatetimeIndex]:
    if not dates:
        return None
    dt_index = pd.to_datetime(sorted(dates), format="%Y-%m-%d", errors="coerce")
    return dt_index[pd.notna(dt_index)]


def fillin_market_data(path, date):
    if not os.path.exists(path):
        return
    df = pd.read_csv(path)
    date = pd.Timestamp(date)

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
        unique_symbols = list(set(symbols_earnings))
        earnings_dict = {}

        for i in range(0, len(unique_symbols), BATCH_SIZE):
            batch_symbols = unique_symbols[i : i + BATCH_SIZE]
            try:
                batch_earnings = get_batch_earnings_dates(batch_symbols)
                for symbol in batch_symbols:
                    dates = batch_earnings.get(symbol, [])
                    earnings_dict[symbol] = _process_earnings_dates(dates)

                total_batches = (len(unique_symbols) + BATCH_SIZE - 1) // BATCH_SIZE
                print(f"Processed earnings batch {i // BATCH_SIZE + 1}/{total_batches}")
            except Exception as e:
                print(f"Error processing earnings batch: {e}")
                continue

        for symbol in symbols_earnings:
            idx = indices_map[symbol]
            rep_dates = earnings_dict.get(symbol)
            next_report_days, next_report_date = get_next_report_days(date, rep_dates)
            if next_report_days is not None:
                df.loc[idx, "next_report_days"] = next_report_days
            if next_report_date is not None:
                df.loc[idx, "next_report_date"] = next_report_date
        df.to_csv(path, index=False)

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
    if rep_dates is None:
        return None, None
    for rep_date in rep_dates:
        next_report_days = (rep_date - date).days
        if next_report_days >= 0:
            return next_report_days, rep_date
    return None, None


def get_pass_report_days(date, rep_dates):
    if rep_dates is None:
        return None
    for rep_date in reversed(rep_dates):
        pass_report_days = (date - rep_date).days
        if pass_report_days >= 0:
            return pass_report_days
    return None


def fillin_finance_report_date(df, date):
    current_headers = df.columns.tolist()
    date = pd.Timestamp(date)

    if "symbol" in df.columns:
        unique_symbols = df["symbol"].dropna().unique().tolist()
        use_column = True
    elif hasattr(df.index, "tolist") and len(df.index) > 0:
        unique_symbols = [
            s for s in df.index.tolist() if isinstance(s, str) and len(s) > 0
        ]
        unique_symbols = list(set(unique_symbols))
        use_column = False
    else:
        unique_symbols = []
        use_column = None

    if not unique_symbols:
        print("No symbols found in dataframe")
        return df

    reports = {}

    for i in range(0, len(unique_symbols), BATCH_SIZE):
        batch_symbols = unique_symbols[i : i + BATCH_SIZE]
        try:
            batch_earnings = get_batch_earnings_dates(batch_symbols)
            for symbol in batch_symbols:
                dates = batch_earnings.get(symbol, [])
                reports[symbol] = _process_earnings_dates(dates)
            print(
                f"Processed earnings batch {i // BATCH_SIZE + 1}, symbols: {batch_symbols[0]} to {batch_symbols[-1]}"
            )
        except Exception as e:
            print(f"Error processing earnings batch starting at {i}: {e}")
            continue

    if use_column is not None:
        if use_column:
            df[["next_report_days", "next_report_date"]] = df.apply(
                lambda r: pd.Series(
                    get_next_report_days(date, reports.get(r["symbol"]))
                ),
                axis=1,
            )
            df["pass_report_days"] = df.apply(
                lambda r: get_pass_report_days(date, reports.get(r["symbol"])), axis=1
            )
        else:
            df[["next_report_days", "next_report_date"]] = df.apply(
                lambda r: pd.Series(get_next_report_days(date, reports.get(r.name))),
                axis=1,
            )
            df["pass_report_days"] = df.apply(
                lambda r: get_pass_report_days(date, reports.get(r.name)), axis=1
            )

    return df[
        [
            "pass_report_days",
            "next_report_days",
            "next_report_date",
        ]
        + current_headers
    ]

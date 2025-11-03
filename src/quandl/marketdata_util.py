import os
import numpy as np
import pandas as pd
from src.utils.path_utils import (
    get_data_path,
)
from src.utils.yf_utils import get_stock_info


def fillin_market_data(path, date):
    if os.path.exists(path):
        df = pd.read_csv(path)

    for idx in range(len(df)):
        if pd.notna(df.loc[idx, "current_price"]):
            continue
        symbol = df.loc[idx, "symbol"]
        try:
            current_price, market_cap = get_stock_info(symbol)
            df.loc[idx, "current_price"] = current_price
            df.loc[idx, "market_cap"] = market_cap

            if (idx + 1) % 10 == 0:
                df.to_csv(path, index=False)
                print(f"save to {symbol}")

        except Exception as e:
            print(f"processing {symbol} with error：{e}")
            df.to_csv(path, index=False)
            break
    df.to_csv(path, index=False)
    print(f"processed all symbols")


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
    report_df = pd.read_csv(get_data_path(f"financeReportDate.csv"))
    report_df.dropna(subset=["date"], inplace=True)
    reports = report_df.set_index("symbol")["date"].to_dict()
    for symbol in reports:
        reports[symbol] = pd.to_datetime(
            sorted(reports[symbol].split("|")), format="%Y-%m-%d"
        )
    df[["next_report_days", "next_report_date"]] = df.apply(
        lambda r: pd.Series(get_next_report_days(date, reports.get(r.name))), axis=1
    )
    df["pass_report_days"] = df.apply(
        lambda r: get_pass_report_days(date, reports.get(r.name)), axis=1
    )
    df["current_price"] = np.nan
    df["market_cap"] = np.nan

    return df[
        [
            "pass_report_days",
            "next_report_days",
            "next_report_date",
            "current_price",
            "market_cap",
        ]
        + current_headers
    ]

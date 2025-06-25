import os
from time import sleep

import numpy as np
import pandas as pd

from src.quandl.headers import PercentiledIVHeader
from src.utils.path_utils import (
    get_quandl_path,
    get_data_path,
    get_latest_date,
    get_root_path,
)
from src.utils.idx_utils import get_percentile_rank
from src.utils.download_utils import download_file, get_quandl_last_day_iv_url
from src.utils.yf_utils import get_stock_info

TargetHeader = ["date"] + [
    h for header in PercentiledIVHeader for h in (header, f"{header}_rank")
]


def find_percentiles(df, header):
    values_s = df.get(header)
    if values_s is None:
        return None
    values_s = values_s.dropna()
    percentiles_df = pd.read_csv(get_data_path(f"iv_percentiles_headers/{header}.csv"))
    percentiles_df.set_index("percentiles", inplace=True)
    symbol_ranks = {}
    for symbol, value in values_s.items():
        percentiles = percentiles_df.get(symbol)
        if percentiles is None:
            continue
        rank = get_percentile_rank(percentiles, value)
        symbol_ranks[symbol] = rank
    rank_s = pd.Series(symbol_ranks).astype(int)
    return pd.DataFrame({header: values_s, f"{header}_rank": rank_s})


def get_last_iv_rank():
    last_csv_name = get_latest_date(get_quandl_path("option_iv_rank"))
    df = pd.read_csv(get_quandl_path(f"option_iv_rank/{last_csv_name}.csv"))
    df.set_index("symbol", inplace=True)
    return df


def percentile_last_day_iv_rank(raw_file_name, date_str):
    df = pd.read_csv(raw_file_name)
    if len(df) < 10:
        return None

    df = df[df["date"] == date_str]
    df.rename(columns={"ticker": "symbol"}, inplace=True)
    df.set_index("symbol", inplace=True)
    df.sort_index(inplace=True)

    dfs = []
    for header in PercentiledIVHeader:
        dfs.append(find_percentiles(df, header))
    all_df = pd.concat(dfs, axis=1)
    all_df.sort_index(inplace=True)
    return all_df


def fillin_market_data(path, date):
    if os.path.exists(path):
        df = pd.read_csv(path)

    for idx in range(len(df)):
        if pd.notna(df.loc[idx, "current_price"]):
            continue
        df["market_cap"] = np.nan
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


def fetch_option_percentiles(date):
    date_str = date.strftime("%Y-%m-%d")
    date_path = date.strftime("%Y_%m_%d")
    print(f"start processing {date_str}")
    iv_rank_final_path = get_quandl_path(f"option_iv_rank/{date_path}.csv")
    if os.path.exists(iv_rank_final_path):
        fillin_market_data(iv_rank_final_path, date)
        return

    url = get_quandl_last_day_iv_url(date_str)
    raw_folder = get_quandl_path(f"option_iv_raw")
    os.makedirs(raw_folder, exist_ok=True)
    raw_file_name = f"{raw_folder}/{date_path}.csv"
    if not os.path.exists(raw_file_name) or pd.read_csv(raw_file_name).empty:
        download_file(url, raw_file_name)
        sleep(1)
    df = percentile_last_day_iv_rank(raw_file_name, date_str)
    if df is None:
        return False
    expiry_date_df = pd.read_csv(get_root_path(f"finance/expiry_dates.csv"))
    expiry_date_df.set_index("symbol", inplace=True)
    df = pd.merge(df, expiry_date_df, left_index=True, right_index=True, how="left")
    # df = fillin_finance_report_date(df, date)

    df["iv_ratio"] = df.apply(
        lambda row: divide(row["ivmean1080"], row["ivmean10"]), axis=1
    )
    df.to_csv(iv_rank_final_path, index=True, index_label="symbol")
    for symbol, row in df.iterrows():
        if symbol == "nan":
            continue
        symbol_file_path = get_quandl_path(f"option_iv_rank_by_symbols/{symbol}.csv")
        df = pd.read_csv(symbol_file_path) if os.path.exists(symbol_file_path) else None
        has_symbol = df is not None and len(df) > 0
        if has_symbol and not df.loc[df["date"] == date_str].empty:
            continue

        row["date"] = date_str
        row_df = pd.DataFrame([row])
        row_df = row_df[TargetHeader]

        if has_symbol:
            df = pd.concat([row_df, df], ignore_index=True)
            df.sort_values(by=["date"], ascending=[False], inplace=True)
        else:
            df = row_df
        df.to_csv(symbol_file_path, index=False)
    fillin_market_data(iv_rank_final_path, date)


def quantiles_all_iv():
    q_dfs = {}
    for header in PercentiledIVHeader:
        q_dfs[header] = pd.read_csv(
            get_data_path(f"iv_percentiles_headers/{header}.csv")
        )
        q_dfs[header].set_index("percentiles", inplace=True)

    df = pd.read_csv(
        get_data_path(f"iv_all.csv"), usecols=["ticker", "date"] + PercentiledIVHeader
    )
    df.rename(columns={"ticker": "symbol"}, inplace=True)
    df.dropna(inplace=True)

    for symbol, symbol_df in df.groupby("symbol"):
        print(symbol)
        symbol_df.sort_values(by=["date"], ascending=[False], inplace=True)
        for header in PercentiledIVHeader:
            percentiles = q_dfs[header].get(symbol)
            if percentiles is not None:
                symbol_df[header + "_rank"] = symbol_df.apply(
                    lambda row: get_percentile_rank(percentiles, row[header]), axis=1
                )
            else:
                symbol_df[header + "_rank"] = np.nan
        symbol_df = symbol_df[TargetHeader]
        symbol_df = symbol_df.sort_values(by=["date"], ascending=[False])
        symbol_df.to_csv(
            get_quandl_path(f"option_iv_rank_by_symbols/{symbol}.csv"), index=False
        )


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


def divide(dividend, divisor):
    if dividend is None or divisor is None or divisor == 0:
        return None
    return dividend / divisor


if __name__ == "__main__":
    # fetch_option_percentiles(datetime.date(2025, 3, 21))
    quantiles_all_iv()

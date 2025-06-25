import os

import numpy as np
import pandas as pd

from src.utils.path_utils import get_quandl_path


def filter_qualified_options(date):
    date_path = date.strftime("%Y_%m_%d")
    file_path = get_quandl_path(f"option_iv_rank/{date_path}.csv")
    if not os.path.exists(file_path):
        return
    df = pd.read_csv(get_quandl_path(f"option_iv_rank/{date_path}.csv"))
    df = df[df.apply(is_qualified, axis=1)]
    # df = df[df['ivcall1080_rank'] <= 50 & df['ivput1080_rank'] <= 60]

    df.to_csv(get_quandl_path(f"option_qualified/{date_path}.csv"), index=False)


def is_qualified(row):
    if row['max_days'] < 500 or np.isnan(row['max_days']):
        return False
    if row['current_price'] < 30:
        return False
    if row['ivmean1080'] > 0.4:
        return False
    if row['ivcall1080_rank'] > 40:
        return False
    if row['ivput1080_rank'] > 50:
        return False
    return  True

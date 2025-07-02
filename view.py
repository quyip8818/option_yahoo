import re
from time import sleep

from src.utils.file_utis import open_file_in_application
from src.utils.path_utils import get_quandl_path, get_latest_date


def get_symbols(line: str) -> list[str]:
    return sorted([w.strip() for w in re.split(r"[\s,]+", line)])


if __name__ == "__main__":
    latest_date = get_latest_date(get_quandl_path("option_iv_rank"))
    open_file_in_application(get_quandl_path(f"option_iv_rank/{latest_date}.csv"))
    sleep(1)
    for symbol in get_symbols("""ADSK CPNG DBX ICLN INCY INSM PDD WB ZM"""):
        open_file_in_application(
            get_quandl_path(f"option_iv_rank_by_symbols/{symbol}.csv")
        )
        sleep(0.2)

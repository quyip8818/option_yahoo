import itertools
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv
from src.utils.utils import round_num

load_dotenv()

_api_keys_str = os.getenv("FINNHUB_API_KEYS", "").strip()
FINNHUB_API_KEYS = [key.strip() for key in _api_keys_str.split(",") if key.strip()]

BASE_URL = "https://finnhub.io/api/v1"
API_CALL_DELAY = 0.3

_api_key_cycle = itertools.cycle(FINNHUB_API_KEYS)
_api_call_count = 0
_current_api_key = None


def _get_next_api_key() -> str:
    global _api_call_count, _current_api_key
    if _api_call_count % 50 == 0:
        time.sleep(5)
        _current_api_key = next(_api_key_cycle)

    _api_call_count += 1
    return _current_api_key


def _make_api_request(url: str, params: dict, symbol: str = "") -> Optional[dict]:
    max_retries = 5
    for attempt in range(max_retries):
        try:
            api_key = _get_next_api_key()
            params_with_token = {**params, "token": api_key}
            response = requests.get(url, params=params_with_token, timeout=10)

            if response.status_code == 429:
                wait_time = (attempt + 1) * 3.0
                print(f"Rate limited for {symbol}, waiting {wait_time}s before retry")
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            data = response.json()
            time.sleep(API_CALL_DELAY)
            return data
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 429:
                wait_time = (attempt + 1) * 1.0
                print(f"Rate limited for {symbol}, waiting {wait_time}s before retry")
                time.sleep(wait_time)
                if attempt == max_retries - 1:
                    print(f"Error for {symbol} after {max_retries} retries: {e}")
            else:
                print(f"Error for {symbol}: {e}")
                return None
        except Exception as e:
            print(f"Error for {symbol}: {e}")
            return None
    return None


def get_stock_price(symbol: str) -> Optional[float]:
    url = f"{BASE_URL}/quote"
    params = {"symbol": symbol}
    data = _make_api_request(url, params, symbol)

    if data and "c" in data and data["c"] is not None:
        price = round_num(data["c"], 2)
        print(f"Got price for {symbol}: {price}")
        return price
    print(f"Failed to get price for {symbol}")
    return None


def get_stock_market_cap(symbol: str) -> Optional[float]:
    url = f"{BASE_URL}/stock/profile2"
    params = {"symbol": symbol}
    data = _make_api_request(url, params, symbol)

    if (
        data
        and "marketCapitalization" in data
        and data["marketCapitalization"] is not None
    ):
        return round_num(data["marketCapitalization"], 0)
    return None


def get_stock_earnings_dates(symbol: str) -> List[str]:
    url = f"{BASE_URL}/stock/earnings"
    params = {"symbol": symbol}
    data = _make_api_request(url, params, symbol)

    if isinstance(data, list):
        dates = [item.get("date") for item in data if item.get("date")]
        return sorted(dates)
    return []


def get_all_earnings_dates(current_date: datetime) -> Dict[str, List[str]]:
    from_date = (current_date - timedelta(days=3)).strftime("%Y-%m-%d")
    to_date = (current_date + timedelta(days=120)).strftime("%Y-%m-%d")

    url = f"{BASE_URL}/calendar/earnings"
    params = {"from": from_date, "to": to_date}

    data = _make_api_request(url, params, "earnings_calendar")

    if data is None:
        print("Warning: earnings calendar API returned None")
        return {}

    if isinstance(data, dict):
        if "error" in data:
            print(f"Warning: earnings calendar API returned error: {data.get('error')}")
            return {}
        if "earningsCalendar" in data:
            data = data["earningsCalendar"]
        elif isinstance(data.get("earnings"), list):
            data = data["earnings"]
        else:
            print(
                f"Warning: earnings calendar API returned dict with unexpected structure: {data.keys()}"
            )
            return {}

    if not isinstance(data, list):
        print(f"Warning: earnings calendar API returned non-list data: {type(data)}")
        return {}

    results = {}
    for item in data:
        symbol = item.get("symbol")
        date = item.get("date")
        if symbol and date:
            if symbol not in results:
                results[symbol] = []
            results[symbol].append(date)

    for symbol in results:
        results[symbol] = sorted(list(set(results[symbol])))

    return results

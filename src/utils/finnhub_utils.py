import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv
from src.utils.utils import round_num

load_dotenv()

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
BASE_URL = "https://finnhub.io/api/v1"
API_DELAY = 0.1


def _make_api_request(url: str, params: dict, symbol: str = "") -> Optional[dict]:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 429:
                wait_time = (attempt + 1) * 1.0
                print(f"Rate limited for {symbol}, waiting {wait_time}s before retry")
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            data = response.json()
            time.sleep(API_DELAY)
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
    params = {"symbol": symbol, "token": FINNHUB_API_KEY}
    data = _make_api_request(url, params, symbol)

    if data and "c" in data and data["c"] is not None:
        return round_num(data["c"], 2)
    return None


def get_stock_market_cap(symbol: str) -> Optional[float]:
    url = f"{BASE_URL}/stock/profile2"
    params = {"symbol": symbol, "token": FINNHUB_API_KEY}
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
    params = {"symbol": symbol, "token": FINNHUB_API_KEY}
    data = _make_api_request(url, params, symbol)

    if isinstance(data, list):
        dates = [item.get("date") for item in data if item.get("date")]
        return sorted(dates)
    return []


def get_all_earnings_dates(current_date: datetime) -> Dict[str, List[str]]:
    from_date = (current_date - timedelta(days=90)).strftime("%Y-%m-%d")
    to_date = (current_date + timedelta(days=90)).strftime("%Y-%m-%d")
    
    url = f"{BASE_URL}/calendar/earnings"
    params = {
        "from": from_date,
        "to": to_date,
        "token": FINNHUB_API_KEY
    }
    
    data = _make_api_request(url, params, "earnings_calendar")
    
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
    
    print(f"Fetched earnings dates for {len(results)} symbols")
    return results

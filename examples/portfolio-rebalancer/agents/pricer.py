import requests
from shared.config import REQUEST_TIMEOUT

# simple symbol -> coingecko id map
SYMBOL_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDC": "usd-coin",
    "SOL": "solana",
    "BNB": "binancecoin",
    "DOGE": "dogecoin"
}


# fallback prices (used if API fails)
FALLBACK_PRICES = {
    "BTC": 60000,
    "ETH": 3000,
    "USDC": 1,
}


def fetch_from_api(symbols: list[str]) -> dict[str, float]:
    ids = [SYMBOL_MAP.get(s, "").lower() for s in symbols if s in SYMBOL_MAP]

    if not ids:
        return {}

    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(ids),
        "vs_currencies": "usd",
    }

    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    data = response.json()

    prices = {}
    for symbol in symbols:
        coin_id = SYMBOL_MAP.get(symbol)
        if coin_id and coin_id in data:
            prices[symbol] = data[coin_id]["usd"]

    return prices


def run(symbols: list[str]) -> dict[str, float]:
    try:
        prices = fetch_from_api(symbols)

        # fill missing with fallback
        for s in symbols:
            if s not in prices:
                prices[s] = FALLBACK_PRICES.get(s, 1)

        return prices

    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"[pricer] warrenty: {e}, using fallback prices")
        return {s: FALLBACK_PRICES.get(s, 1) for s in symbols}
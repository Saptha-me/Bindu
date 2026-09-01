# shared/config.py
import os

USE_FAKE_DATA = os.getenv("USE_FAKE_DATA", "true").lower() == "true"

def _parse_float(raw, default):
    try:
        value = float(raw) if raw is not None else default
        return value if 0 < value <= 1 else default
    except (TypeError, ValueError):
        return default

REBALANCE_FRACTION = _parse_float(os.getenv("REBALANCE_FRACTION"), 0.25)

try:
    REQUEST_TIMEOUT = max(1, int(os.getenv("REQUEST_TIMEOUT", "5")))
except ValueError:
    REQUEST_TIMEOUT = 5
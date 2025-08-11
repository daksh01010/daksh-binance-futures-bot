"""
Daksh Binance Futures Trading Bot
Core utilities, validation, logging, and retry mechanisms

Author: Daksh
Description: Professional trading bot for Binance USDT-M Futures
"""

import os
import re
import json
import uuid
import time
from datetime import datetime
from typing import Any, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

BOT_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot.log")

def init_logger():
    # Ensure log file exists
    os.makedirs(os.path.dirname(BOT_LOG_PATH), exist_ok=True)
    if not os.path.exists(BOT_LOG_PATH):
        with open(BOT_LOG_PATH, "w", encoding="utf-8") as f:
            f.write("")
    return BOT_LOG_PATH

def _write_log(level: str, payload: Dict[str, Any]):
    rec = {
        "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "level": level.upper(),
        **payload
    }
    with open(BOT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")

def log_info(payload: Dict[str, Any]):
    _write_log("INFO", payload)

def log_error(payload: Dict[str, Any]):
    _write_log("ERROR", payload)

def load_env():
    cfg = {
        "API_KEY": os.getenv("BINANCE_API_KEY", ""),
        "API_SECRET": os.getenv("BINANCE_API_SECRET", ""),
        "MODE": os.getenv("MODE", "dryrun").lower(),
        "DEFAULT_SYMBOL": os.getenv("DEFAULT_SYMBOL", "BTCUSDT"),
    }
    return cfg

SYMBOL_RE = re.compile(r"^[A-Z]{3,}USDT$")

def validate_symbol(symbol: str) -> str:
    if not isinstance(symbol, str):
        raise ValueError("symbol must be a string")
    s = symbol.strip().upper()
    if not SYMBOL_RE.match(s):
        raise ValueError("symbol must be uppercase letters and end with USDT (e.g., BTCUSDT)")
    return s

def validate_side(side: str) -> str:
    if not isinstance(side, str):
        raise ValueError("side must be a string")
    s = side.strip().upper()
    if s not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")
    return s

def _to_float(name: str, val: Any) -> float:
    try:
        f = float(val)
    except Exception:
        raise ValueError(f"{name} must be a number")
    if f <= 0:
        raise ValueError(f"{name} must be > 0")
    return f

def validate_qty(qty: Any) -> float:
    return _to_float("quantity", qty)

def validate_price(price: Any) -> float:
    return _to_float("price", price)

class FakeClient:
    def __init__(self):
        self.mode = "dryrun"

    def futures_create_order(self, **kwargs) -> Dict[str, Any]:
        oid = f"FAKE-{uuid.uuid4().hex[:8]}"
        log_info({
            "action": "place_order",
            "mode": self.mode,
            "request": kwargs,
            "orderId": oid
        })
        return {"orderId": oid, "status": "ACK", "dryrun": True, "request": kwargs}

def get_client(api_key: str, api_secret: str, mode: str):
    if mode.lower() == "dryrun":
        return FakeClient()
    from binance.client import Client
    client = Client(api_key, api_secret)
    return client

import time
from typing import Callable, Dict, Any, Tuple

RETRY_ERRORS = {
    "-1001",   # DISCONNECTED
    "-1021",   # TIMESTAMP for this request was 1000ms ahead of the server's time.
    "-1105",   # Parameter was empty or a whitespace
    "ReadTimeout",
    "ConnectionError",
    "TimeoutError",
}

def _is_transient_error(err: Exception) -> bool:
    s = str(err)
    for key in RETRY_ERRORS:
        if key in s:
            return True
    # Fallback: consider generic network/timeouts transient
    return "timed out" in s.lower() or "temporarily unavailable" in s.lower()

def place_order_with_retry(client: Any, req: Dict[str, Any], max_retries: int = 3, base_delay: float = 0.5) -> Dict[str, Any]:
    """
    Attempts to place a futures order with retries on transient errors.
    Logs each attempt and final outcome.
    """
    attempt = 0
    last_err = None
    while attempt <= max_retries:
        try:
            if attempt > 0:
                log_info({
                    "action": "retry_attempt",
                    "attempt": attempt,
                    "req": {k: v for k, v in req.items() if k != "newClientOrderId"},
                })
            resp = client.futures_create_order(**req)
            return resp
        except Exception as e:
            last_err = e
            is_transient = _is_transient_error(e)
            log_error({
                "action": "order_attempt_failed",
                "attempt": attempt,
                "transient": is_transient,
                "error": str(e),
                "req": {k: v for k, v in req.items() if k != "newClientOrderId"},
            })
            if attempt == max_retries or not is_transient:
                break
            # Exponential backoff: 0.5s, 1s, 2s...
            sleep_s = base_delay * (2 ** attempt)
            time.sleep(sleep_s)
            attempt += 1
            continue
    # If here, all attempts failed
    raise last_err if last_err else RuntimeError("Unknown error placing order")

# Initialize logger on import
init_logger()

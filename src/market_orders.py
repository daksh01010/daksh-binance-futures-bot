import sys
import os
import argparse

# Add project root to path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.common import (
    load_env,
    get_client,
    validate_symbol,
    validate_side,
    validate_qty,
    log_info,
    log_error,
    place_order_with_retry,  # NEW
)

def parse_args():
    p = argparse.ArgumentParser(description="Place a MARKET futures order")
    p.add_argument("symbol", help="e.g., BTCUSDT")
    p.add_argument("side", help="BUY or SELL")
    p.add_argument("quantity", help="Order quantity (float)")
    return p.parse_args()

def main():
    args = parse_args()
    cfg = load_env()
    try:
        symbol = validate_symbol(args.symbol)
        side = validate_side(args.side)
        qty = validate_qty(args.quantity)
    except Exception as e:
        log_error({"action": "validate", "error": str(e)})
        print(f"Input error: {e}")
        sys.exit(1)

    client = get_client(cfg["API_KEY"], cfg["API_SECRET"], cfg["MODE"])

    try:
        req = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": qty,
        }
        resp = place_order_with_retry(client, req)  # UPDATED
        log_info({
            "action": "place_order",
            "type": "MARKET",
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "result": "ok",
            "orderId": resp.get("orderId")
        })
        print(f"OK: MARKET {side} {qty} {symbol}, orderId={resp.get('orderId')}")
    except Exception as e:
        log_error({
            "action": "place_order",
            "type": "MARKET",
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "result": "error",
            "error": str(e),
        })
        print(f"Order failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

import sys
import os
import argparse

# Add project root to path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.common import (
    load_env,
    get_client,
    validate_symbol,
    validate_side,
    validate_qty,
    validate_price,
    log_info,
    log_error,
    place_order_with_retry,  # NEW
)

def parse_args():
    p = argparse.ArgumentParser(description="Place a STOP-LIMIT futures order (GTC)")
    p.add_argument("symbol", help="e.g., BTCUSDT")
    p.add_argument("side", help="BUY or SELL")
    p.add_argument("quantity", help="Order quantity (float)")
    p.add_argument("--stopPrice", required=True, help="Trigger price (float)")
    p.add_argument("--limitPrice", required=True, help="Limit price (float)")
    p.add_argument("--timeInForce", default="GTC", choices=["GTC", "IOC", "FOK"], help="Time in force (default GTC)")
    return p.parse_args()

def main():
    args = parse_args()
    cfg = load_env()
    try:
        symbol = validate_symbol(args.symbol)
        side = validate_side(args.side)
        qty = validate_qty(args.quantity)
        stop_price = validate_price(args.stopPrice)
        limit_price = validate_price(args.limitPrice)
        tif = args.timeInForce

        # Relationship validation (simple, common convention)
        if side == "SELL":
            if stop_price < limit_price:
                raise ValueError("For SELL stop-limit: stopPrice should be >= limitPrice")
        else:  # BUY
            if stop_price > limit_price:
                raise ValueError("For BUY stop-limit: stopPrice should be <= limitPrice")
    except Exception as e:
        log_error({"action": "validate", "type": "STOP_LIMIT", "error": str(e)})
        print(f"Input error: {e}")
        sys.exit(1)

    client = get_client(cfg["API_KEY"], cfg["API_SECRET"], cfg["MODE"])

    try:
        # Futures STOP-LIMIT uses type="STOP" with price as limit and stopPrice as trigger
        req = {
            "symbol": symbol,
            "side": side,
            "type": "STOP",
            "timeInForce": tif,
            "quantity": qty,
            "price": limit_price,
            "stopPrice": stop_price,
            "workingType": "CONTRACT_PRICE",  # simple default
        }
        resp = place_order_with_retry(client, req)  # UPDATED
        log_info({
            "action": "place_order",
            "type": "STOP_LIMIT",
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "stopPrice": stop_price,
            "limitPrice": limit_price,
            "tif": tif,
            "result": "ok",
            "orderId": resp.get("orderId"),
        })
        print(f"OK: STOP-LIMIT {side} {qty} {symbol}, stop={stop_price}, limit={limit_price}, tif={tif}, orderId={resp.get('orderId')}")
    except Exception as e:
        log_error({
            "action": "place_order",
            "type": "STOP_LIMIT",
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "stopPrice": stop_price,
            "limitPrice": limit_price,
            "tif": tif,
            "result": "error",
            "error": str(e),
        })
        print(f"Order failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


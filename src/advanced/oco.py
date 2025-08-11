import sys
import os
import argparse
import uuid

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
    p = argparse.ArgumentParser(description="Emulated OCO for Futures (TP + SL paired)")
    p.add_argument("symbol", help="e.g., BTCUSDT")
    p.add_argument("side", help="SELL or BUY for the exit side")
    p.add_argument("quantity", help="Order quantity (float)")
    p.add_argument("--takeProfit", required=True, help="TP price (float)")
    p.add_argument("--stopPrice", required=True, help="SL trigger price (float)")
    p.add_argument("--stopLimitPrice", help="Optional SL limit price (float). If omitted, use STOP_MARKET")
    return p.parse_args()

def main():
    args = parse_args()
    cfg = load_env()

    try:
        symbol = validate_symbol(args.symbol)
        side = validate_side(args.side)
        qty = validate_qty(args.quantity)
        tp = validate_price(args.takeProfit)
        sp = validate_price(args.stopPrice)
        sl_limit = None
        if args.stopLimitPrice is not None:
            sl_limit = validate_price(args.stopLimitPrice)
    except Exception as e:
        log_error({"action": "validate", "type": "OCO", "error": str(e)})
        print(f"Input error: {e}")
        sys.exit(1)

    client = get_client(cfg["API_KEY"], cfg["API_SECRET"], cfg["MODE"])
    link_id = f"OCO-{uuid.uuid4().hex[:8]}"

    try:
        # Take Profit order
        tp_type = "TAKE_PROFIT" if sl_limit else "TAKE_PROFIT"
        tp_req = {
            "symbol": symbol,
            "side": side,
            "type": tp_type,
            "reduceOnly": True,
            "quantity": qty,
            "price": tp,
            "timeInForce": "GTC",
            "workingType": "CONTRACT_PRICE",
            "newClientOrderId": f"{link_id}-TP",
        }
        tp_resp = place_order_with_retry(client, tp_req)  # UPDATED

        # Stop Loss order
        if sl_limit:
            sl_type = "STOP"
            sl_req = {
                "symbol": symbol,
                "side": side,
                "type": sl_type,
                "reduceOnly": True,
                "quantity": qty,
                "price": sl_limit,
                "stopPrice": sp,
                "timeInForce": "GTC",
                "workingType": "CONTRACT_PRICE",
                "newClientOrderId": f"{link_id}-SL",
            }
        else:
            sl_type = "STOP_MARKET"
            sl_req = {
                "symbol": symbol,
                "side": side,
                "type": sl_type,
                "reduceOnly": True,
                "quantity": qty,
                "stopPrice": sp,
                "workingType": "CONTRACT_PRICE",
                "newClientOrderId": f"{link_id}-SL",
            }

        sl_resp = place_order_with_retry(client, sl_req)  # UPDATED

        log_info({
            "action": "place_oco",
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "takeProfit": tp,
            "stopPrice": sp,
            "stopLimitPrice": sl_limit,
            "result": "ok",
            "linkId": link_id,
            "tpOrderId": tp_resp.get("orderId"),
            "slOrderId": sl_resp.get("orderId"),
        })

        print(f"OK: OCO linkId={link_id} TP orderId={tp_resp.get('orderId')} SL orderId={sl_resp.get('orderId')}")
        print("Note: In this simple emulation, auto-cancel on fill is not implemented. Document this in README.")
    except Exception as e:
        log_error({
            "action": "place_oco",
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "takeProfit": tp,
            "stopPrice": sp,
            "stopLimitPrice": sl_limit,
            "result": "error",
            "error": str(e),
        })
        print(f"OCO failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

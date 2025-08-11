import sys
import os
import argparse
import uuid

# Ensure project root is on path to import src
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
    p = argparse.ArgumentParser(description="Bracket Order: Entry + TP + SL (Futures)")
    p.add_argument("symbol", help="e.g., BTCUSDT")
    p.add_argument("side", help="BUY or SELL for the ENTRY side")
    p.add_argument("quantity", help="Total entry quantity (float)")
    p.add_argument("--entryType", default="MARKET", choices=["MARKET", "LIMIT"], help="Entry order type (default MARKET)")
    p.add_argument("--price", help="Entry limit price if entryType=LIMIT")
    p.add_argument("--takeProfit", required=True, help="Take Profit price (float)")
    p.add_argument("--stopPrice", required=True, help="Stop trigger price (float)")
    p.add_argument("--stopLimitPrice", help="Optional Stop-Limit price (float). If omitted, uses STOP_MARKET")
    return p.parse_args()

def main():
    args = parse_args()
    cfg = load_env()

    try:
        symbol = validate_symbol(args.symbol)
        entry_side = validate_side(args.side)             # BUY opens long, SELL opens short
        qty = validate_qty(args.quantity)
        entry_type = args.entryType.upper()
        if entry_type == "LIMIT":
            if args.price is None:
                raise ValueError("price is required when entryType=LIMIT")
            entry_price = validate_price(args.price)
        else:
            entry_price = None

        tp_price = validate_price(args.takeProfit)
        sl_trigger = validate_price(args.stopPrice)
        sl_limit = validate_price(args.stopLimitPrice) if args.stopLimitPrice else None
    except Exception as e:
        log_error({"action": "validate", "type": "BRACKET", "error": str(e)})
        print(f"Input error: {e}")
        sys.exit(1)

    # Exit side is the opposite of entry
    exit_side = "SELL" if entry_side == "BUY" else "BUY"

    client = get_client(cfg["API_KEY"], cfg["API_SECRET"], cfg["MODE"])
    link_id = f"BRK-{uuid.uuid4().hex[:8]}"

    # 1) Place entry
    try:
        entry_req = {
            "symbol": symbol,
            "side": entry_side,
            "type": entry_type,
            "quantity": qty,
        }
        if entry_type == "LIMIT":
            entry_req["price"] = entry_price
            entry_req["timeInForce"] = "GTC"

        entry_req["newClientOrderId"] = f"{link_id}-ENTRY"
        entry_resp = place_order_with_retry(client, entry_req)  # UPDATED

        entry_id = entry_resp.get("orderId")
        log_info({
            "action": "place_entry",
            "type": entry_type,
            "symbol": symbol,
            "side": entry_side,
            "qty": qty,
            "price": entry_price,
            "linkId": link_id,
            "orderId": entry_id,
            "result": "ok",
        })
        print(f"OK: Entry placed ({entry_type}) orderId={entry_id}, linkId={link_id}")
    except Exception as e:
        log_error({
            "action": "place_entry",
            "type": entry_type,
            "symbol": symbol,
            "side": entry_side,
            "qty": qty,
            "price": entry_price,
            "linkId": link_id,
            "result": "error",
            "error": str(e),
        })
        print(f"Entry failed: {e}")
        sys.exit(1)

    # 2) Place Take-Profit
    try:
        tp_req = {
            "symbol": symbol,
            "side": exit_side,
            "type": "TAKE_PROFIT",
            "reduceOnly": True,
            "quantity": qty,
            "price": tp_price,
            "timeInForce": "GTC",
            "workingType": "CONTRACT_PRICE",
            "newClientOrderId": f"{link_id}-TP",
        }
        tp_resp = place_order_with_retry(client, tp_req)  # UPDATED
        tp_id = tp_resp.get("orderId")
        log_info({
            "action": "place_exit_tp",
            "symbol": symbol,
            "side": exit_side,
            "qty": qty,
            "price": tp_price,
            "linkId": link_id,
            "orderId": tp_id,
            "result": "ok",
        })
        print(f"OK: TP placed orderId={tp_id}")
    except Exception as e:
        log_error({
            "action": "place_exit_tp",
            "symbol": symbol,
            "side": exit_side,
            "qty": qty,
            "price": tp_price,
            "linkId": link_id,
            "result": "error",
            "error": str(e),
        })
        print(f"TP failed: {e}")
        # Continue to attempt SL placement for completeness

    # 3) Place Stop Loss (STOP_MARKET or STOP with limit price)
    try:
        if sl_limit:
            sl_req = {
                "symbol": symbol,
                "side": exit_side,
                "type": "STOP",
                "reduceOnly": True,
                "quantity": qty,
                "price": sl_limit,
                "stopPrice": sl_trigger,
                "timeInForce": "GTC",
                "workingType": "CONTRACT_PRICE",
                "newClientOrderId": f"{link_id}-SL",
            }
        else:
            sl_req = {
                "symbol": symbol,
                "side": exit_side,
                "type": "STOP_MARKET",
                "reduceOnly": True,
                "quantity": qty,
                "stopPrice": sl_trigger,
                "workingType": "CONTRACT_PRICE",
                "newClientOrderId": f"{link_id}-SL",
            }

        sl_resp = place_order_with_retry(client, sl_req)  # UPDATED
        sl_id = sl_resp.get("orderId")
        log_info({
            "action": "place_exit_sl",
            "symbol": symbol,
            "side": exit_side,
            "qty": qty,
            "stopPrice": sl_trigger,
            "stopLimitPrice": sl_limit,
            "linkId": link_id,
            "orderId": sl_id,
            "result": "ok",
        })
        print(f"OK: SL placed orderId={sl_id}")
    except Exception as e:
        log_error({
            "action": "place_exit_sl",
            "symbol": symbol,
            "side": exit_side,
            "qty": qty,
            "stopPrice": sl_trigger,
            "stopLimitPrice": sl_limit,
            "linkId": link_id,
            "result": "error",
            "error": str(e),
        })
        print(f"SL failed: {e}")

    print("Note: Auto-cancel on fill is not implemented; document this in README as intentional for this version.")

if __name__ == "__main__":
    main()

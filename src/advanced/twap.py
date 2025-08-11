import sys
import os
import argparse
import time
import uuid

# Add project root to path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.common import (
    load_env,
    get_client,
    validate_symbol,
    validate_side,
    validate_qty,
    log_info,
    log_error,
    place_order_with_retry,
)

def parse_args():
    p = argparse.ArgumentParser(description="TWAP (Time-Weighted Average Price) execution")
    p.add_argument("symbol", help="e.g., BTCUSDT")
    p.add_argument("side", help="BUY or SELL")
    p.add_argument("quantity", help="Total quantity to execute (float)")
    p.add_argument("--slices", type=int, default=5, help="Number of slices (default: 5)")
    p.add_argument("--intervalSec", type=int, default=10, help="Seconds between slices (default: 10)")
    return p.parse_args()

def main():
    args = parse_args()
    cfg = load_env()

    try:
        symbol = validate_symbol(args.symbol)
        side = validate_side(args.side)
        total_qty = validate_qty(args.quantity)
        slices = args.slices
        interval_sec = args.intervalSec
        
        if slices < 1:
            raise ValueError("slices must be >= 1")
        if interval_sec < 1:
            raise ValueError("intervalSec must be >= 1")
            
    except Exception as e:
        log_error({"action": "validate", "type": "TWAP", "error": str(e)})
        print(f"Input error: {e}")
        sys.exit(1)

    client = get_client(cfg["API_KEY"], cfg["API_SECRET"], cfg["MODE"])
    link_id = f"TWAP-{uuid.uuid4().hex[:8]}"
    
    # Calculate slice size
    slice_qty = total_qty / slices
    executed_qty = 0.0
    
    log_info({
        "action": "twap_start",
        "symbol": symbol,
        "side": side,
        "totalQty": total_qty,
        "slices": slices,
        "sliceQty": slice_qty,
        "intervalSec": interval_sec,
        "linkId": link_id,
    })
    
    print(f"Starting TWAP: {total_qty} {symbol} {side} over {slices} slices, {interval_sec}s apart")
    print(f"Each slice: ~{slice_qty:.6f} | LinkId: {link_id}")
    
    for slice_idx in range(1, slices + 1):
        try:
            # Use exact slice quantity except for last slice (handle rounding)
            if slice_idx == slices:
                current_qty = total_qty - executed_qty  # Remainder
            else:
                current_qty = slice_qty
            
            if current_qty <= 0:
                print(f"Slice {slice_idx}/{slices}: Skipped (quantity {current_qty:.6f} <= 0)")
                continue
                
            req = {
                "symbol": symbol,
                "side": side,
                "type": "MARKET",
                "quantity": current_qty,
                "newClientOrderId": f"{link_id}-S{slice_idx}",
            }
            
            resp = place_order_with_retry(client, req)
            order_id = resp.get("orderId")
            executed_qty += current_qty
            
            log_info({
                "action": "twap_slice",
                "symbol": symbol,
                "side": side,
                "sliceIndex": slice_idx,
                "totalSlices": slices,
                "qty": current_qty,
                "executedQty": executed_qty,
                "linkId": link_id,
                "orderId": order_id,
                "result": "ok",
            })
            
            print(f"Slice {slice_idx}/{slices}: {current_qty:.6f} {symbol} {side} → orderId={order_id}")
            
            # Wait before next slice (except for last one)
            if slice_idx < slices:
                print(f"Waiting {interval_sec}s before next slice...")
                time.sleep(interval_sec)
                
        except Exception as e:
            log_error({
                "action": "twap_slice",
                "symbol": symbol,
                "side": side,
                "sliceIndex": slice_idx,
                "totalSlices": slices,
                "qty": current_qty,
                "linkId": link_id,
                "result": "error",
                "error": str(e),
            })
            print(f"Slice {slice_idx}/{slices} failed: {e}")
            # Continue with remaining slices
    
    log_info({
        "action": "twap_complete",
        "symbol": symbol,
        "side": side,
        "totalQty": total_qty,
        "executedQty": executed_qty,
        "slices": slices,
        "linkId": link_id,
        "result": "ok",
    })
    
    print(f"TWAP complete: {executed_qty:.6f}/{total_qty:.6f} executed, linkId={link_id}")

if __name__ == "__main__":
    main()

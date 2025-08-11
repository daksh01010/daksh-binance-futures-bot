import os
import csv
import json
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)  # go up from scripts/ to project root
LOG_PATH = os.path.join(PROJECT_ROOT, "bot.log")
OUT_CSV = os.path.join(PROJECT_ROOT, "trades.csv")

FIELDS = [
    "ts",
    "action",
    "type",
    "symbol",
    "side",
    "qty",
    "price",
    "stopPrice",
    "limitPrice",
    "tif",
    "orderId",
    "linkId",
    "result",
    "sliceIndex",
    "totalSlices",
]

def main():
    if not os.path.exists(LOG_PATH):
        print(f"Log not found: {LOG_PATH}")
        return

    rows = []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            row = {k: rec.get(k, "") for k in FIELDS}
            rows.append(row)

    if not rows:
        print("No log entries to export.")
        return

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Exported {len(rows)} records to {OUT_CSV}")

if __name__ == "__main__":
    main()

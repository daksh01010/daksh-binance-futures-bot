# Daksh Binance Futures Trading Bot

## Overview

A professional Python trading bot for Binance USDT-M Futures with comprehensive order types and safety-first design. Runs in dryrun mode by default with optional live trading capabilities.

**Key Features:**
- Market, Limit, and Stop-Limit orders
- OCO (One-Cancels-Other) emulation with paired TP/SL
- TWAP (Time-Weighted Average Price) execution
- Bracket Orders (Entry + TP + SL automation)
- Retry with exponential backoff for resilient order placement
- Trade journal export to CSV for analysis and reporting
- Professional JSON logging with full audit trail

## Safety

**Safety-First Design:**
- `MODE` defaults to `dryrun` - switch to live trading by setting `MODE=live` in `.env`
- All exit orders use `reduceOnly=True` where applicable to prevent position size increases
- **Important**: OCO and Bracket orders do not auto-cancel sibling orders on fill - this is intentional for this version and should be considered when using in live trading
- All operations are logged with complete traceability

## Setup

**Requirements:** Python 3.8+

1. **Create virtual environment:**
   ```bash
   py -m venv .venv
   .venv\Scripts\Activate.ps1  # Windows
   # or
   source .venv/bin/activate   # Linux/Mac
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment (`.env` file):**
   ```env
   BINANCE_API_KEY=your_api_key_here
   BINANCE_API_SECRET=your_secret_here
   MODE=dryrun
   DEFAULT_SYMBOL=BTCUSDT
   ```

## Usage Examples

### Basic Orders

**Market Orders:**
```bash
python src/market_orders.py BTCUSDT BUY 0.001
```

**Limit Orders:**
```bash
python src/limit_orders.py BTCUSDT SELL 0.001 65000
```

### Advanced Orders

**Stop-Limit Orders:**
```bash
python src/advanced/stop_limit.py BTCUSDT SELL 0.001 --stopPrice 59000 --limitPrice 58800
```

**OCO Emulation:**
```bash
# With stop-limit
python src/advanced/oco.py BTCUSDT SELL 0.001 --takeProfit 62000 --stopPrice 59000 --stopLimitPrice 58800

# With stop-market
python src/advanced/oco.py BTCUSDT SELL 0.001 --takeProfit 62000 --stopPrice 59000
```

**TWAP (Time-Weighted Average Price):**
```bash
python src/advanced/twap.py BTCUSDT BUY 0.01 --slices 5 --intervalSec 10
```

**Bracket Orders:**
```bash
# Market entry with stop-limit SL
python src/advanced/bracket.py BTCUSDT BUY 0.002 --entryType MARKET --takeProfit 62000 --stopPrice 59000 --stopLimitPrice 58800

# Limit entry with stop-market SL
python src/advanced/bracket.py BTCUSDT SELL 0.002 --entryType LIMIT --price 65000 --takeProfit 64000 --stopPrice 66000
```

**Trade Journal Export:**
```bash
python scripts/export_journal.py
```

## Architecture

The bot follows a clean architectural pattern: **CLI → Validation/Logger → Order Handlers → Client Factory**. In dryrun mode, orders route through a FakeClient that simulates responses and logs activity. In live mode, orders route through the Binance client. All order placement is wrapped with a retry+backoff mechanism that handles transient network errors, timestamp skew, and connection issues with exponential backoff (0.5s base, up to 3 attempts). This retry wrapper is integrated into all major order scripts (market, limit, stop-limit, OCO, bracket, and TWAP), ensuring resilient order execution in production environments.

**Note**: The provided `.env` file contains placeholder credentials only. Real Binance API credentials are not required to run the bot in dryrun mode - all operations are simulated locally.

## Known Limitations

- **OCO/Bracket Auto-Cancel**: Orders do not auto-cancel sibling orders on fill - requires user data stream integration and sophisticated order management
- **TWAP Remainder**: Small remainder quantities after per-slice rounding are ignored rather than added to final slice
- **Exchange Filters**: Minimum quantity, step size, and tick size filters are not enforced in this version - relies on exchange rejection
- **Position Awareness**: No position size tracking or risk management guardrails implemented

## How to Extend

**Immediate Improvements:**
- Add WebSocket user data stream integration for true OCO/bracket cancel-on-fill behavior
- Implement exchange filter validation with automatic quantity/price rounding
- Add position-aware exit logic and risk management guardrails (daily loss limits, maximum position sizes)
- Create comprehensive unit test suite for validators and request builders

**Advanced Features:**
- Real-time market data integration for better entry/exit timing
- Portfolio-level risk management and correlation analysis
- Machine learning integration for dynamic parameter optimization
- Multi-exchange support and cross-exchange arbitrage capabilities

## Live Trading Switch

**IMPORTANT**: This bot defaults to `dryrun` mode for safety. To enable live trading:

1. Obtain valid Binance API credentials with futures trading permissions
2. Update `.env` file with your real API keys
3. Change `MODE=dryrun` to `MODE=live` in `.env`
4. **Test thoroughly** with small quantities before scaling up

**Warning**: Live trading involves real financial risk. Always start with minimal quantities and ensure you understand all order types before using with significant capital.

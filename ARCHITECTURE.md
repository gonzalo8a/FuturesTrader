# FuturesTrader - Technical Architecture

## Overview
Automated cryptocurrency futures day-trading bot that replicates a proven manual Bollinger Band mean reversion strategy on Binance USDT-M Futures.

## Proven Strategy (User's Manual Method)
- **Market**: BTC/USDT Perpetual Futures (Binance USDT-M)
- **Timeframe**: 15-minute candles
- **Entry Signal**: Price touches Bollinger Band outer bounds (2σ)
- **Direction**: Mean reversion (upper band touch → SHORT, lower band touch → LONG)
- **Position Sizing**: 50% of equity per trade
- **Leverage**: 20x (configurable, default 20x)
- **Max Concurrent**: 1 position (due to 50% allocation)
- **Stop-Loss**: 20-30% of position value (≈10-15% of account at 20x leverage)
- **Take-Profit**: Adaptive, range 5-100% based on volatility (ATR-based multi-level)
- **Volume Filter**: Avoid trades during low 15m volume periods
- **Hold Strategy**: Hold losing trades expecting mean reversion, but cut at -20-30% if reversion doesn't occur

## Risk Profile
**EXTREMELY AGGRESSIVE** - User has proven this works manually growing $50 → $300+ using:
- 20x+ leverage
- 50% capital per trade (previously 100% up to $300)
- Mean reversion hold strategy (can sustain drawdowns)
- No traditional stop-loss (uses -20-30% position exit threshold)

## System Architecture

### Core Components

```
src/
├── data/                    # Data collection and storage
│   ├── binance_client.py   # Binance Futures API wrapper
│   ├── websocket_feed.py   # Real-time WebSocket streams
│   ├── database.py         # SQLite persistence
│   └── market_data.py      # OHLCV, orderbook, funding data structures
│
├── strategies/              # Trading strategies
│   ├── base_strategy.py    # Abstract base class
│   ├── bb_mean_reversion.py # Bollinger Band mean reversion (PRIMARY)
│   └── indicators.py       # Technical indicators (BB, ATR, RSI, etc.)
│
├── risk/                    # Risk management
│   ├── position_sizer.py   # Kelly criterion, fixed %, etc.
│   ├── risk_manager.py     # Pre-trade checks, limits, circuit breakers
│   └── liquidation.py      # Liquidation price calculation and monitoring
│
├── execution/               # Order execution
│   ├── order_manager.py    # Order lifecycle (create, cancel, fill tracking)
│   ├── executor.py         # Execute orders via Binance API
│   └── position_tracker.py # Track open positions and PnL
│
├── backtest/                # Backtesting engine
│   ├── backtester.py       # Historical simulation
│   ├── fee_model.py        # Taker/maker fees, funding fees
│   └── slippage_model.py   # Realistic slippage simulation
│
├── paper/                   # Paper trading (real data, simulated execution)
│   ├── paper_trader.py     # Real-time paper trading engine
│   ├── sim_fills.py        # Simulated fill logic (spread, partial fills)
│   └── virtual_account.py  # Virtual balance and position tracking
│
├── live/                    # Live trading
│   ├── live_trader.py      # Real order execution
│   └── reconciliation.py   # Sync local state with Binance
│
└── utils/                   # Utilities
    ├── config.py           # Configuration loader (YAML + env vars)
    ├── logger.py           # Structured logging (JSON)
    ├── metrics.py          # Performance metrics (Sharpe, drawdown, etc.)
    └── kill_switch.py      # Emergency shutdown logic
```

### Data Flow

```
[Binance Futures API]
        ↓
   [WebSocket Feed] ← Real-time price, volume, trades
        ↓
   [Market Data] → Store in SQLite
        ↓
   [Strategy] → BB mean reversion signal generation
        ↓
   [Risk Manager] → Validate trade (size, leverage, limits)
        ↓
   [Execution Engine]
        ├→ [Paper Trader] → Simulate fills
        └→ [Live Trader] → Real Binance orders
        ↓
   [Position Tracker] → Monitor PnL, liquidation risk
        ↓
   [Reporting] → Metrics, logs, alerts
```

### Trading Modes

#### 1. Backtest Mode
- Historical BTC/USDT 15m candle data from Binance
- Simulates:
  - Bollinger Band signals
  - Position sizing (50% equity)
  - Leverage (20x)
  - Stop-loss at -20-30% position value
  - Adaptive take-profit levels
  - Taker fees (0.04%), maker fees (0.02%)
  - Funding fees (8-hourly)
  - Slippage (configurable, default 0.02%)
- Outputs: Equity curve, trade log, performance metrics

#### 2. Paper Trading Mode (LOCAL SIMULATION)
- Real-time data from Binance WebSocket
- **NO REAL ORDERS** - all fills simulated locally
- Simulates:
  - Order book matching (limit orders at specific prices)
  - Spread impact
  - Partial fills (if size > book liquidity)
  - Market impact slippage
  - Taker/maker fees
  - Funding fees
  - Liquidation logic
- Virtual starting balance: $50
- SQLite persistence (survives restarts)
- Runs 24/7 with real market data

#### 3. Live Trading Mode
- **REAL ORDERS** on Binance Futures
- Requires:
  - 7+ days successful paper trading
  - No kill-switch triggers in paper mode
  - Max drawdown < 50% in paper mode
  - User confirmation
- Safety checks:
  - Pre-trade risk validation
  - Position reconciliation every 60s
  - Emergency stop-loss at liquidation buffer
  - Kill switch on anomalies

### Risk Management Framework

#### Position-Level Limits
- **Max leverage**: 20x (configurable, hard cap 25x)
- **Max position size**: 50% of equity
- **Max concurrent positions**: 1
- **Stop-loss**: 20-30% of position value (≈1-1.5% price move at 20x)
- **Liquidation buffer**: Emergency exit at 70% of liquidation price
- **Time-based stop**: Close position after 4 hours if stagnant

#### Account-Level Limits
- **Max daily loss**: 30% of starting daily equity → STOP TRADING
- **Max drawdown**: 50% from peak → DISABLE BOT
- **Max trades per day**: 20 (configurable)
- **Consecutive losses**: 4 → reduce position size by 50% for next trade
- **Daily profit cap**: Optional (lock gains mode)

#### Circuit Breakers
- **Spread anomaly**: Bid-ask spread > 0.5% → reject trade
- **Volatility spike**: ATR increases > 3x in 15m → pause trading for 1 hour
- **Volume collapse**: 15m volume < 10% of 24h average → no new trades
- **API instability**: Failed requests > 20% over 5 minutes → emergency close all
- **Liquidation event**: Any liquidation (even in paper mode) → full stop for review
- **Funding rate shock**: Funding > 0.5% → avoid new positions in that direction

### Kill Switch Triggers
Emergency shutdown and close all positions if:
1. Realized daily loss > 35% (beyond max daily loss limit)
2. Approaching liquidation (< 10% margin remaining)
3. API connection lost for > 5 minutes during active position
4. 3+ consecutive stop-losses within 1 hour
5. Manual trigger (Ctrl+C, /kill command, or emergency file flag)
6. Unexpected error in critical path (position tracking, order execution)

## Configuration

### Environment Variables (.env)
```
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BINANCE_TESTNET=false
```

### YAML Configuration (config/bb_mean_reversion.yaml)
```yaml
mode: paper  # backtest | paper | live

exchange:
  name: binance_futures
  margin_mode: ISOLATED  # ISOLATED | CROSSED

market:
  symbol: BTCUSDT
  timeframe: 15m
  contract_type: perpetual

strategy:
  name: bb_mean_reversion
  params:
    bb_period: 20
    bb_std: 2.0
    volume_filter_multiplier: 0.1  # Min volume = 10% of 24h avg

risk:
  starting_capital: 50.0
  max_position_size_pct: 50.0  # 50% of equity per trade
  max_leverage: 20
  hard_leverage_cap: 25
  max_concurrent_positions: 1
  stop_loss_pct: 25.0  # 25% of position value
  liquidation_buffer_pct: 70.0  # Exit at 70% of liq price
  max_daily_loss_pct: 30.0
  max_drawdown_pct: 50.0
  max_trades_per_day: 20

execution:
  order_type: LIMIT  # LIMIT | MARKET
  limit_order_timeout_sec: 30
  retry_on_timeout: true
  max_retries: 1
  post_only: false  # Don't require maker fees
  reduce_only_exits: true

profit_targets:
  mode: adaptive  # adaptive | fixed
  levels:
    - {pct: 5.0, size_pct: 25}   # Take 25% profit at 5%
    - {pct: 10.0, size_pct: 25}  # Take 25% profit at 10%
    - {pct: 25.0, size_pct: 25}  # Take 25% profit at 25%
    - {pct: 50.0, size_pct: 25}  # Take 25% profit at 50%
  trailing_stop_activation: 20.0  # Enable trailing after 20% profit
  trailing_stop_distance_pct: 10.0

session:
  trading_hours: "00:00-23:00"  # UTC, close all at 23:00
  timezone: UTC

data:
  db_path: data/futures_trader.db
  log_path: logs/

paper:
  starting_balance: 50.0
  simulate_slippage: true
  slippage_bps: 2.0  # 0.02% slippage
  simulate_funding: true
  funding_interval_hours: 8

fees:
  maker: 0.02  # 0.02% maker fee
  taker: 0.04  # 0.04% taker fee

logging:
  level: INFO  # DEBUG | INFO | WARNING | ERROR
  format: json

alerts:
  enabled: true
  channels: [console]  # console | file | email | telegram
```

## Data Persistence (SQLite Schema)

### Tables

#### candles
```sql
CREATE TABLE candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    quote_volume REAL NOT NULL,
    trades INTEGER,
    UNIQUE(symbol, timeframe, timestamp)
);
```

#### orderbook_snapshots
```sql
CREATE TABLE orderbook_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    bids TEXT NOT NULL,  -- JSON: [[price, qty], ...]
    asks TEXT NOT NULL,  -- JSON: [[price, qty], ...]
    spread_bps REAL
);
```

#### funding_rates
```sql
CREATE TABLE funding_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    funding_rate REAL NOT NULL,
    UNIQUE(symbol, timestamp)
);
```

#### trades
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL,  -- backtest | paper | live
    trade_id TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    strategy TEXT NOT NULL,
    side TEXT NOT NULL,  -- LONG | SHORT
    entry_time INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    size REAL NOT NULL,
    leverage REAL NOT NULL,
    notional REAL NOT NULL,
    exit_time INTEGER,
    exit_price REAL,
    pnl REAL,
    pnl_pct REAL,
    fees REAL,
    funding_fees REAL,
    exit_reason TEXT,  -- take_profit | stop_loss | time_stop | manual | kill_switch
    max_profit REAL,
    max_drawdown REAL,
    metadata TEXT  -- JSON: signals, indicators, etc.
);
```

#### positions
```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL,
    position_id TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    size REAL NOT NULL,
    entry_price REAL NOT NULL,
    leverage REAL NOT NULL,
    liquidation_price REAL,
    unrealized_pnl REAL,
    status TEXT NOT NULL,  -- OPEN | CLOSED
    opened_at INTEGER NOT NULL,
    closed_at INTEGER,
    updated_at INTEGER NOT NULL
);
```

#### account_snapshots
```sql
CREATE TABLE account_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    equity REAL NOT NULL,
    balance REAL NOT NULL,
    unrealized_pnl REAL NOT NULL,
    margin_used REAL NOT NULL,
    margin_available REAL NOT NULL,
    open_positions INTEGER NOT NULL,
    daily_pnl REAL,
    drawdown_pct REAL
);
```

#### events
```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    event_type TEXT NOT NULL,  -- TRADE | RISK_LIMIT | KILL_SWITCH | ERROR
    severity TEXT NOT NULL,  -- INFO | WARNING | ERROR | CRITICAL
    message TEXT NOT NULL,
    metadata TEXT  -- JSON
);
```

## Performance Metrics

### Real-Time Monitoring
- Current equity
- Unrealized PnL
- Open positions (size, leverage, liquidation distance)
- Daily PnL %
- Drawdown from peak
- Win rate (today / all-time)
- Average profit per trade
- Average loss per trade
- Profit factor
- Number of trades today
- Risk limits status (% used)

### End-of-Day Reporting
- Equity curve chart
- Trade-by-trade breakdown
- Cumulative PnL
- Max drawdown
- Sharpe ratio (if sufficient trades)
- Total fees paid
- Total funding fees paid/received
- Kill-switch events
- Risk violations
- Slippage impact
- Win rate by hour of day
- Best/worst trades

## Safety Checklist (Before Live Trading)

### Paper Trading Validation (7+ days minimum)
- [ ] Bot runs continuously without crashes
- [ ] No unhandled exceptions in logs
- [ ] Position tracking matches simulated Binance state
- [ ] Stop-losses trigger correctly
- [ ] Take-profit levels execute properly
- [ ] Liquidation buffer logic never breached
- [ ] Daily loss limit honored (no trading after hit)
- [ ] Max drawdown limit stops trading
- [ ] Kill switch triggers on anomalies
- [ ] Volume filter prevents trades in low liquidity
- [ ] Time-based exit closes positions at cutoff (23:00 UTC)
- [ ] Consecutive loss logic reduces size correctly
- [ ] Funding fee simulation reasonable
- [ ] Equity curve trending positively or stable

### Pre-Live Checklist
- [ ] Binance API keys created with **ONLY Futures trading** permission
- [ ] API keys restricted by IP address (if possible)
- [ ] Withdrawals disabled on API keys
- [ ] `.env` file secured (chmod 600, not in git)
- [ ] Starting capital deposited in Binance Futures wallet ($50+)
- [ ] Config file reviewed (leverage, position size, limits)
- [ ] Manual test: place/cancel small LIMIT order on Binance
- [ ] Emergency stop procedure documented
- [ ] Monitoring plan in place (check logs every 4-8 hours)
- [ ] Understand that **total loss is possible**
- [ ] Ready to shut down if performance degrades

## Assumptions & Limitations

### Assumptions
1. **Binance Futures API availability**: Bot assumes <10ms latency and 99.9% uptime
2. **BTC/USDT liquidity**: Assumes sufficient liquidity for $50-$5000 position sizes at all times
3. **Mean reversion hypothesis**: Assumes BTC exhibits mean reversion on 15m timeframe during range-bound periods
4. **Funding rate stability**: Assumes funding rates stay within -0.5% to +0.5%
5. **Execution quality**: Assumes LIMIT orders fill within 30 seconds at entry price
6. **No extreme events**: Assumes no flash crashes, exchange hacks, or >50% BTC moves in minutes
7. **User's manual edge translates to automation**: Assumes the discretionary elements (intuition, profit targets) can be approximated algorithmically

### Limitations
1. **No multi-asset support**: Only BTC/USDT, cannot diversify across ETH, SOL, etc. (future enhancement)
2. **No adaptive leverage**: Leverage is fixed per config, doesn't adjust based on volatility
3. **Simplified profit targets**: Uses ATR-based levels, not true discretionary intuition
4. **Single strategy**: Only BB mean reversion implemented (momentum breakout as future addition)
5. **No news/sentiment analysis**: Ignores Twitter, news, on-chain data
6. **No inter-exchange arbitrage**: Only trades on Binance
7. **Slippage model is approximation**: Real slippage varies with order size and liquidity
8. **Funding fee simulation**: May not perfectly match Binance's actual funding rates
9. **Partial fills**: Simplified model (may not match real Binance partial fill behavior)
10. **Recovery from crashes**: Bot restarts cleanly, but may miss 1-2 candles of data during downtime

## Future Enhancements (Out of Scope for V1)
- Multiple symbol support (ETH, altcoins)
- Multiple concurrent strategies
- Machine learning signal ranking
- Sentiment analysis integration
- Adaptive leverage based on volatility regime
- Cross-exchange data aggregation
- Advanced order types (iceberg, TWAP)
- Telegram bot for remote monitoring/control
- Email/SMS alerts
- Web dashboard for live monitoring
- Cloud deployment (AWS, GCP)
- Multi-account support
- Arbitrage strategies

## Technical Stack
- **Language**: Python 3.10+
- **Exchange API**: `ccxt` (Binance Futures wrapper)
- **WebSocket**: `websockets` + `asyncio`
- **Data**: `pandas`, `numpy`
- **Indicators**: `pandas-ta` or custom implementations
- **Database**: `sqlite3`
- **Logging**: `structlog` (structured JSON logs)
- **Config**: `PyYAML`, `python-dotenv`
- **Testing**: `pytest`
- **Validation**: `pydantic` (config/data validation)
- **CLI**: `click` or `argparse`

## Development Environment
- **OS**: Ubuntu 22.04 LTS
- **IDE**: Visual Studio Code
  - Extensions: Python, Pylance, Python Test Explorer
- **Python**: 3.10+ (via pyenv or apt)
- **Git**: Version control
- **Virtual Environment**: `venv`

## Disclaimers

### ⚠️ EXTREME RISK WARNING
- This bot uses **20x leverage** with **50% capital per trade**
- A single adverse 5% BTC move can result in **100% position loss** (liquidation)
- With 50% capital allocation, 2 liquidations = **total account loss**
- Mean reversion can FAIL in strong trending markets
- **Past manual performance does NOT guarantee future automated results**
- Automation introduces new failure modes (bugs, API issues, connectivity)
- **YOU CAN LOSE ALL YOUR CAPITAL**

### No Profit Guarantees
- This system is designed to replicate a proven manual strategy
- Automated execution may underperform manual trading due to:
  - Lack of human intuition
  - Simplified profit target logic
  - Fixed stop-loss rules (vs. discretionary exits)
  - API latency
  - Slippage
- Market conditions change - past performance ≠ future results
- **Do not expect to turn $50 into $10,000** - this is statistically unlikely even with an edge

### Responsibility
- User assumes **ALL RISK**
- Developer provides code "AS IS" with no warranty
- User must monitor the bot, especially in live mode
- User responsible for API key security
- User responsible for tax reporting on gains/losses
- **Trade at your own risk**

---

**Version**: 1.0.0
**Last Updated**: 2026-01-19
**Author**: Automated Futures Trading System
**License**: Private Use

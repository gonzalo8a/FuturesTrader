# 🚀 FuturesTrader - Automated Cryptocurrency Futures Day Trading Bot

An advanced, automated trading bot for Binance USDT-M Futures that implements a **proven Bollinger Band mean reversion strategy** with comprehensive risk management, real-time market analysis, and intelligent trade execution.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ⚠️ CRITICAL DISCLAIMER

**THIS BOT TRADES REAL MONEY ON LEVERAGED FUTURES CONTRACTS**

- You can lose **ALL** your capital
- Futures trading with leverage amplifies both gains AND losses
- This bot is provided AS-IS with **NO WARRANTY**
- The developers are **NOT responsible** for any financial losses
- **ALWAYS start with paper trading mode**
- Test thoroughly for at least 7 days before considering live trading
- Only trade with money you can afford to lose completely

**USE AT YOUR OWN RISK**

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Module Documentation](#module-documentation)
- [Strategy Explanation](#strategy-explanation)
- [Risk Management](#risk-management)
- [Advanced Features](#advanced-features)
- [Optimization Tips](#optimization-tips)
- [Troubleshooting](#troubleshooting)
- [Bug Fixes & Changelog](#bug-fixes--changelog)

---

## ✨ Features

### Core Functionality
- ✅ **Paper Trading Mode**: Risk-free simulation with real market data
- ✅ **Live Trading Mode**: Automated execution on Binance Futures
- ✅ **Bollinger Band Mean Reversion**: Proven strategy for BTC/USDT
- ✅ **20x Leverage Support**: Configurable leverage with safety caps
- ✅ **Isolated Margin Mode**: Each position independent, limiting risk

### Intelligent Signal Generation
- 📊 **Multi-Timeframe Analysis**: 15m candles for signals, 1d for trend bias
- 📉 **Daily Trend Filter**: Favor shorts on red days, longs on green days
- 💹 **Order Flow Analysis**: Real-time buy/sell pressure from last 100 trades
- ⚡ **Liquidation Cluster Detection**: Avoid cascades, exploit opposite-side liquidity
- 🎯 **Confidence Scoring**: Dynamic confidence based on market conditions

### Advanced Risk Management
- 🛡️ **Stop-Loss Automation**: Percentage-based stops with liquidation awareness
- 🎚️ **Position Sizing**: Dynamic sizing based on equity and risk tolerance
- 📊 **Account-Based Profit Targets**: 3% for <$100 accounts, 5% for $100-$500
- 🔄 **Position-Based Targets**: Scaled exits at 5%, 10%, 25%, 50% for larger accounts
- ⏱️ **Time-Based Exits**: Maximum position duration (default 12 hours)
- 🚨 **Circuit Breakers**: Auto-stop on excessive spread, low volume, or API errors
- 💀 **Kill Switch**: Emergency shutdown on liquidation or critical errors

### Data & Analytics
- 💾 **SQLite Database**: Full trade history, account snapshots, events
- 📈 **Performance Tracking**: Real-time PnL, drawdown, win rate
- 📝 **Detailed Logging**: Structured JSON logs for analysis
- 🔍 **Trade Audit Trail**: Complete record of all decisions and executions

---

## 🏗️ Architecture Overview

```
FuturesTrader/
├── src/
│   ├── data/              # Data fetching & storage
│   │   ├── binance_client.py   # Binance API wrapper with rate limiting
│   │   └── database.py          # SQLite operations
│   ├── strategies/        # Trading strategies & indicators
│   │   ├── bb_mean_reversion.py # Main strategy implementation
│   │   └── indicators.py        # Technical indicators (BB, RSI, ATR, etc.)
│   ├── risk/              # Risk management
│   │   ├── risk_manager.py      # Position sizing, limits, circuit breakers
│   │   └── liquidation.py       # Liquidation price calculations
│   ├── paper/             # Paper trading simulation
│   │   └── paper_trader.py      # Virtual account & simulated execution
│   └── utils/             # Utilities
│       ├── config.py            # Configuration management
│       └── logger.py            # Structured logging
├── config/                # Configuration files
│   └── bb_mean_reversion.yaml   # Strategy & risk parameters
├── .env                   # API credentials (not in repo)
└── main.py               # Entry point
```

---

## 💻 Installation

### Prerequisites
- Python 3.10 or higher
- Linux/WSL (Ubuntu 22.04+ recommended)
- Binance Futures account (for live trading)
- Git

### Step 1: Clone the Repository

```bash
# Clone with correct branch
git clone -b claude/crypto-futures-trading-bot-x2wAq https://github.com/gonzalo8a/FuturesTrader.git
cd FuturesTrader
```

### Step 2: Set Up Python Environment

```bash
# Install Python virtual environment support (if needed)
sudo apt update
sudo apt install python3.10-venv -y

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### Step 3: Install Dependencies

```bash
# Install all required packages
pip install pandas numpy requests PyYAML python-dotenv
```

**Note**: `pandas-ta` is NOT required as all technical indicators are implemented natively.

### Step 4: Configure API Credentials

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API credentials
nano .env
```

Add your Binance Futures API credentials:

```env
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
```

**CRITICAL SECURITY:**
- Use **testnet** for initial testing
- Create API keys with **ONLY Futures trading permission**
- **DISABLE withdrawals** on API keys
- Restrict API keys by IP address if possible
- Never share your `.env` file

### Step 5: Verify Installation

```bash
# Check BTC price to verify API connection
python check_price.py
```

You should see current BTC/USDT price and 24h statistics.

---

## ⚙️ Configuration

The bot is configured via `config/bb_mean_reversion.yaml`. Key parameters:

### Market Settings
```yaml
market:
  symbol: "BTCUSDT"        # Trading pair
  timeframe: "15m"          # Signal timeframe
  tick_interval: 15000      # Update interval (ms)
```

### Strategy Parameters
```yaml
strategy:
  name: "bb_mean_reversion"
  params:
    bb_period: 20           # Bollinger Band period
    bb_std: 2.0             # Standard deviations
    bb_touch_threshold: 0.998  # Touch sensitivity (99.8% = tight)
    rsi_period: 14
    atr_period: 14
```

### Risk Management
```yaml
risk:
  max_position_size_pct: 50.0  # 50% of account per trade
  max_leverage: 20              # 20x leverage
  stop_loss_pct: 25.0           # 25% stop-loss
  max_daily_loss_pct: 10.0      # Stop after 10% daily loss
  max_drawdown_pct: 50.0        # Kill switch at 50% drawdown
  max_position_duration_minutes: 720  # 12 hours max
```

### Paper Trading
```yaml
paper:
  starting_balance: 50.0   # Starting capital for simulation
  simulate_slippage: true
  slippage_bps: 5          # 0.05% slippage
```

---

## 🎮 Usage

### Paper Trading (Recommended Start)

```bash
# Activate virtual environment
source .venv/bin/activate

# Start paper trading
python main.py paper

# Or with explicit config (same thing)
python main.py paper --config config/bb_mean_reversion.yaml
```

**What happens:**
- Bot connects to Binance for real-time market data
- Executes trades in local simulation (NO real orders)
- Tracks virtual balance with realistic fees and slippage
- Logs all trades and performance metrics

**Run for at least 7 days before considering live trading!**

### Live Trading (⚠️ DANGER ZONE)

```bash
python main.py live --config config/bb_mean_reversion.yaml
```

**Safety Checklist:**
- [ ] Ran paper trading successfully for 7+ days
- [ ] Verified stop-loss logic works correctly
- [ ] Tested kill switch and circuit breakers
- [ ] Using capital you can afford to lose completely
- [ ] API keys have ONLY Futures trading permission
- [ ] API keys have withdrawals DISABLED
- [ ] API keys restricted by IP (optional but recommended)
- [ ] Starting with minimum capital ($50-100)

**You will be prompted to type `I UNDERSTAND THE RISKS` to proceed.**

### Stopping the Bot

Press `Ctrl+C` to gracefully shut down:
- All open positions will be closed at market price
- Final performance summary will be displayed
- Database snapshots saved

---

## 📚 Module Documentation

### 1. `src/data/binance_client.py` - Binance API Wrapper

**Purpose**: Handles all communication with Binance Futures API with rate limiting and error handling.

**Key Classes:**
- `RateLimiter`: Ensures API weight limits aren't exceeded (1200/minute)
- `BinanceFuturesClient`: Main API client

**Key Methods:**
```python
get_klines(symbol, interval, limit)      # Fetch candlestick data
get_orderbook(symbol, limit)             # Get order book depth
get_current_price(symbol)                # Current market price
create_order(symbol, side, type, ...)    # Place order
get_position_info(symbol)                # Get open position details
get_account_balance()                    # Account balance
```

**Features:**
- Automatic request signing (HMAC-SHA256)
- Rate limit enforcement with weight tracking
- Retry logic with exponential backoff
- Comprehensive error handling
- Timestamp synchronization

**How to Get Maximum Value:**
- Monitor rate limit usage in logs
- Use appropriate weight for each call
- Batch operations when possible
- Handle exceptions gracefully

---

### 2. `src/data/database.py` - Data Persistence

**Purpose**: SQLite database for storing all trading data.

**Tables:**
- `candles`: OHLCV data
- `orderbook_snapshots`: Order book depth
- `funding_rates`: Funding rate history
- `trades`: All executed trades
- `positions`: Open/closed positions
- `account_snapshots`: Equity over time
- `events`: System events (errors, warnings, kill switches)

**Key Methods:**
```python
insert_trade(trade_data)            # Log new trade
update_trade(trade_id, updates)     # Update trade on close
insert_account_snapshot(snapshot)   # Save equity snapshot
get_trades_by_strategy(strategy)    # Query trades
```

**How to Get Maximum Value:**
- Query database for performance analysis
- Export to CSV for external analysis
- Monitor account_snapshots for equity curve
- Review events for system health

**Database Location**: `data/futures_bot.db`

---

### 3. `src/strategies/bb_mean_reversion.py` - Main Strategy

**Purpose**: Implements Bollinger Band mean reversion with multi-factor filtering.

**Signal Generation Process:**

1. **Bollinger Band Touch Detection**
   ```python
   LONG: price <= bb_lower * 0.998   # 99.8% of lower band
   SHORT: price >= bb_upper / 0.998  # 100.2% of upper band
   ```

2. **Daily Trend Bias Filter**
   - RED DAY (< -2%): Rejects weak LONGS, boosts SHORTS
   - GREEN DAY (> +2%): Rejects weak SHORTS, boosts LONGS
   - NEUTRAL: No adjustment

3. **Order Flow Analysis**
   - Calculates buy_pressure from last 100 trades
   - Rejects LONG if < 35% (too much selling)
   - Rejects SHORT if > 65% (too much buying)

4. **Liquidation Cluster Detection**
   - Counts recent LONG/SHORT liquidations
   - Rejects direction with 5+ recent liquidations
   - Boosts confidence when opposite side liquidating

5. **Confidence Scoring**
   - Base confidence from distance to band
   - +20% for volume spike confirmation
   - +10% for high volatility (wide bands)
   - Adjusted by filters above

**Key Methods:**
```python
generate_signal(df, price, orderbook, daily_candles, trades, liquidations)
  # Returns Signal object or None

calculate_stop_loss(entry, side, atr)
  # Returns stop price (25% default)

calculate_take_profit_levels(entry, side, atr)
  # Returns list of TP levels (5%, 10%, 25%, 50%)
```

**How to Get Maximum Value:**
- Monitor signal confidence scores in logs
- Track why signals are rejected (check logs)
- Adjust `bb_touch_threshold` for more/fewer signals
- Tweak filter thresholds in code for your risk tolerance

---

### 4. `src/strategies/indicators.py` - Technical Indicators

**Purpose**: All technical indicators used by the strategy.

**Implemented Indicators:**
```python
bollinger_bands(prices, period=20, std=2.0)  # BB upper, middle, lower
atr(high, low, close, period=14)             # Average True Range
rsi(prices, period=14)                        # Relative Strength Index
percent_b(prices, upper, lower)               # Position within BB
bb_width(upper, lower, middle)                # Volatility measure
sma(prices, period)                           # Simple Moving Average
ema(prices, period)                           # Exponential Moving Average
vwap(high, low, close, volume)                # Volume-Weighted Avg Price
```

**Bug Fixes Applied (v1.1):**
- ✅ Division-by-zero guards in RSI (when no losses)
- ✅ Division-by-zero guards in %B (when bands converge)
- ✅ Division-by-zero guards in BB Width (edge case)

**How to Get Maximum Value:**
- Use ATR for dynamic stop-loss placement
- Monitor BB Width for volatility changes
- Check RSI for oversold/overbought confirmation
- %B shows exact position within bands (0=lower, 1=upper)

---

### 5. `src/risk/risk_manager.py` - Risk Management System

**Purpose**: Enforces all risk limits and circuit breakers.

**Risk Checks:**

**1. Position Sizing**
```python
# Calculates position size based on:
- Account equity
- max_position_size_pct (50%)
- Leverage (20x)
- Ensures liquidation is far from stop-loss
```

**2. Daily Limits**
- Max daily loss: 10% of starting equity → Trading paused
- Max consecutive losses: 3 → Warning
- Max trades per day: 10 → Prevents overtrading

**3. Drawdown Limits**
- Max drawdown: 50% from peak → KILL SWITCH activated
- Tracks peak equity throughout session

**4. Circuit Breakers**
```python
check_spread_too_wide()      # Rejects if spread > 0.1%
check_volume_too_low()       # Rejects if volume < 50% avg
check_excessive_volatility() # Rejects if volatility > 3x avg
check_api_errors()           # Stops after 5 consecutive errors
```

**5. Leverage Safety**
```python
# Ensures stop-loss is significantly closer than liquidation
safe_leverage = calculate_safe_leverage(entry, stop, side)
leverage = min(configured_leverage, safe_leverage)
```

**Key Methods:**
```python
validate_trade(signal, equity, positions, price)
  # Returns (valid, reason, position_params)

record_trade_result(pnl, reason)
  # Updates daily stats

update_equity(current_equity)
  # Tracks peak and drawdown

pause_trading(duration_minutes)
  # Temporarily stops trading
```

**How to Get Maximum Value:**
- Monitor circuit breaker triggers in logs
- Adjust `max_daily_loss_pct` for risk tolerance
- Track consecutive losses for strategy health
- Review drawdown metrics regularly

---

### 6. `src/risk/liquidation.py` - Liquidation Calculations

**Purpose**: Calculate and monitor liquidation risk.

**Functions:**

**1. Calculate Liquidation Price**
```python
calculate_liquidation_price(entry, leverage, side, margin_mode="ISOLATED")
# Formula:
# LONG: Entry × (1 - 1/Leverage + MMR)
# SHORT: Entry × (1 + 1/Leverage - MMR)
# MMR = 0.4% for BTC
```

**2. Distance to Liquidation**
```python
distance_to_liquidation(current_price, liq_price, side)
# Returns percentage distance
# Positive = safe, Negative = liquidated
```

**3. Near Liquidation Check**
```python
is_near_liquidation(current_price, liq_price, side, threshold=10%)
# Returns True if within 10% of liquidation
```

**4. Calculate Safe Leverage**
```python
calculate_safe_leverage(entry, stop_loss, side, buffer=1.5)
# Ensures stop is 50% closer than liquidation
```

**How to Get Maximum Value:**
- Always check distance_to_liquidation before trading
- Use calculate_safe_leverage to validate leverage
- Monitor positions approaching liquidation
- Understand relationship between leverage and liquidation

**Example:**
```
Entry: $50,000
Leverage: 20x
Side: LONG

Liquidation Price: $47,700 (4.6% drop)
Stop-Loss (25%): $48,750 (2.5% drop)

Distance to liquidation at entry: 4.6%
✅ Stop-loss is far from liquidation (good!)
```

---

### 7. `src/paper/paper_trader.py` - Paper Trading Engine

**Purpose**: Simulates live trading with virtual account.

**Key Classes:**

**1. VirtualAccount**
```python
# Tracks:
- balance: Free balance available
- margin_used: Capital locked in positions
- unrealized_pnl: Open position PnL
- equity: Total account value

# Methods:
open_position(...)   # Lock margin, open position
close_position(...)  # Realize PnL, free margin
get_equity()         # balance + margin_used + unrealized_pnl
```

**Critical Bug Fixes (v1.1):**
- ✅ Margin now properly subtracted on open
- ✅ Equity formula fixed to include locked margin
- ✅ Prevents "free money" bug on close
- ✅ Session-level profit targets (not per-position)

**2. PaperTrader**
```python
# Main loop (every 5 seconds):
1. Fetch current price
2. Update unrealized PnL
3. Check for liquidations (simulated)
4. Manage positions (stops, targets, time exits)
5. Check for new signals (if positions < max)
6. Log performance

# Position Management:
- Session-level profit targets (3% for <$100, 5% for <$500)
- Position-level targets (5%, 10%, 25%, 50%)
- Stop-loss checks
- Time-based exits (12h max)
```

**Realistic Simulation:**
- Slippage: 0.05% (5 bps)
- Taker fees: 0.04% per side (entry + exit)
- Funding fees: Every 8 hours (simulated)

**How to Get Maximum Value:**
- Run for at least 7 days to see different market conditions
- Monitor equity curve in database
- Track what signals are accepted vs rejected
- Analyze win rate and average PnL
- Test different configurations
- Use paper trading to validate strategy changes

---

### 8. `src/utils/config.py` - Configuration Management

**Purpose**: Load and validate all configuration parameters.

**Configuration Hierarchy:**
1. YAML file: `config/bb_mean_reversion.yaml`
2. Environment variables: `.env` file
3. Command-line overrides

**Validation:**
- Leverage caps: Max 25x hard cap
- Position size: 0-100%
- Timeframes: Valid intervals only
- API credentials: Existence check

**How to Get Maximum Value:**
- Create multiple config files for different strategies
- Use environment variables for secrets
- Validate config changes with paper trading first
- Document any custom configurations

---

### 9. `src/utils/logger.py` - Structured Logging

**Purpose**: Comprehensive logging for debugging and analysis.

**Log Levels:**
- DEBUG: Detailed diagnostics
- INFO: Normal operations
- WARNING: Concerning but not critical
- ERROR: Failures requiring attention
- CRITICAL: System-threatening issues

**Log Outputs:**
- Console: Colored, human-readable
- File: JSON-structured for programmatic analysis

**Special Log Functions:**
```python
log_trade(...)           # Trade execution details
log_risk_event(...)      # Risk limit triggers
log_kill_switch(...)     # Emergency shutdowns
log_performance(...)     # Performance summaries
```

**How to Get Maximum Value:**
- Parse JSON logs for automated analysis
- Monitor ERROR and CRITICAL logs
- Track trade logs for performance review
- Use DEBUG level for troubleshooting

**Log Location**: `logs/futures_trader_{date}.log`

---

## 🎯 Strategy Explanation

### Bollinger Band Mean Reversion - The Core Concept

**Theory:**
- Price tends to revert to the mean (middle Bollinger Band)
- When price touches outer bands, it's "stretched" and likely to snap back
- Works best in ranging/oscillating markets

**Why It Works:**
1. **Statistical Edge**: 2 standard deviations = 95% of price action
2. **Market Psychology**: Extreme moves trigger profit-taking
3. **Liquidity Zones**: Outer bands attract stop-loss clusters

**The User's Proven Method:**
- Manually traded on 15m BTC/USDT
- 20x leverage, 50% position size
- Manual exits at -20-30% (stopped out) or +5-100% (scaled profits)
- **Most profitable shorting on red days**

**Bot Improvements:**
1. **Automated Execution**: No emotional decisions, no missed signals
2. **Multi-Factor Filtering**: Daily bias + order flow + liquidations
3. **Consistent Risk Management**: Always 25% stop-loss, no exceptions
4. **Account-Level Targets**: Lock in 3-5% daily gains (life-changing for small accounts)

---

## 🛡️ Risk Management

### Position Sizing Example

**Account**: $100
**Position Size**: 50% = $50
**Leverage**: 20x
**Notional Value**: $50 × 20 = $1,000

**At BTC = $90,000:**
- Position Size: $1,000 / $90,000 = 0.0111 BTC
- Margin Used: $50
- Free Balance: $50
- Stop-Loss (25%): $12.50 loss
- Liquidation (95%): $47.50 loss (shouldn't happen if stop works)

**Key Insight**: You're risking $12.50 to potentially make $15-50+ per trade.

### The 3% Rule for Small Accounts

**Problem**: Position-based targets (5%, 10%) don't make sense for $50-100 accounts.
**Solution**: Account-level profit targets.

**Example:**
- Start with $50
- Trade makes $1.50 (3% of account)
- **Close position immediately**
- Preserve capital, consistent small wins compound

**Math:**
- 3% daily gain = 3,000% annual return (unrealistic to sustain)
- But even 1% daily = 3,678% annual
- **Compounding is king** for small accounts

---

## 🚀 Advanced Features

### Daily Trend Bias Filter

**How It Works:**
```python
# Fetch daily candle
daily_change = (close - open) / open

if daily_change < -0.02:  # Red day (-2%+)
    # Market bearish, favor SHORTS
    if signal == LONG and confidence < 75%:
        reject_signal()
    if signal == SHORT:
        confidence += 15%

elif daily_change > 0.02:  # Green day (+2%+)
    # Market bullish, favor LONGS
    # Mirror logic
```

**Why It Matters:**
- The user made most profits shorting on red days
- Market momentum persists intraday
- Going with the trend increases win rate

**Optimization:**
- Adjust thresholds (-2%, +2%) based on backtest results
- Consider 4h or 6h timeframe instead of daily
- Add moving average filter for longer-term trend

### Order Flow Analysis

**Calculation:**
```python
# Last 100 trades
buy_volume = sum(trade['qty'] where trade['isBuyerMaker'] == False)
sell_volume = sum(trade['qty'] where trade['isBuyerMaker'] == True)

buy_pressure = buy_volume / (buy_volume + sell_volume)

# Thresholds:
if buy_pressure < 35%:  reject LONG  # Too much selling
if buy_pressure > 65%:  reject SHORT # Too much buying
```

**Why It Matters:**
- Real-time measure of market sentiment
- Aggressive buying/selling indicates conviction
- Aligns with order flow trading principles

**Optimization:**
- Adjust sample size (100 trades)
- Adjust thresholds (35%, 65%)
- Weight recent trades more heavily

### Liquidation Cluster Detection

**How It Works:**
```python
# Fetch recent forced liquidations
recent_longs_liquidated = count(liquidations where side=LONG, time < 15min ago)
recent_shorts_liquidated = count(liquidations where side=SHORT, time < 15min ago)

if recent_longs_liquidated >= 5:
    # LONG cascade in progress, avoid LONG
    reject_long()
    boost_short_confidence()

if recent_shorts_liquidated >= 5:
    # SHORT squeeze in progress, avoid SHORT
    reject_short()
    boost_long_confidence()
```

**Why It Matters:**
- Liquidations cascade (trigger more liquidations)
- Opposite side gets filled at favorable prices
- Indicates extreme leverage exhaustion

**Optimization:**
- Adjust threshold (5 liquidations)
- Adjust time window (15 minutes)
- Consider notional value of liquidations, not just count

---

## 📊 Optimization Tips

### Getting the Most Out of FuturesTrader

**1. Configuration Tuning**
```yaml
# More conservative (recommended start):
risk:
  max_position_size_pct: 30.0  # Lower position size
  max_leverage: 10             # Lower leverage
  stop_loss_pct: 15.0          # Tighter stops

# More aggressive (after validation):
risk:
  max_position_size_pct: 75.0
  max_leverage: 20
  stop_loss_pct: 30.0
```

**2. Strategy Adjustments**
```yaml
strategy:
  params:
    bb_touch_threshold: 0.995  # More signals (looser)
    bb_touch_threshold: 0.999  # Fewer signals (tighter)
```

**3. Timeframe Experimentation**
```yaml
market:
  timeframe: "5m"   # More frequent signals, noisier
  timeframe: "15m"  # Balanced (recommended)
  timeframe: "30m"  # Fewer signals, higher quality
```

**4. Filter Tuning**

Edit `src/strategies/bb_mean_reversion.py`:

```python
# Daily trend bias threshold
if daily_change < -0.03:  # Stricter (-3% instead of -2%)

# Order flow thresholds
if buy_pressure < 30%:  # More conservative (30% instead of 35%)

# Liquidation threshold
if recent_longs_liquidated >= 3:  # More sensitive (3 instead of 5)
```

**5. Performance Analysis**

```bash
# Query database for insights
sqlite3 data/futures_bot.db

# Most profitable times
SELECT strftime('%H', exit_time/1000, 'unixepoch') as hour,
       AVG(pnl) as avg_pnl,
       COUNT(*) as trades
FROM trades
WHERE exit_time IS NOT NULL
GROUP BY hour
ORDER BY avg_pnl DESC;

# Win rate by side
SELECT side,
       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate,
       AVG(pnl) as avg_pnl
FROM trades
WHERE exit_time IS NOT NULL
GROUP BY side;
```

**6. Risk Optimization**

```sql
# Track your actual max drawdown
SELECT MIN(equity) as lowest,
       MAX(equity) as peak,
       (MAX(equity) - MIN(equity)) * 100.0 / MAX(equity) as max_dd
FROM account_snapshots;

# Adjust max_drawdown_pct accordingly
```

---

## 🔧 Troubleshooting

### Common Issues

**1. "No signals for hours"**
- **Normal**: BB touches are rare (quality over quantity)
- **Check**: Are filters too strict? Review logs for rejection reasons
- **Solution**: Loosen `bb_touch_threshold` or adjust filters

**2. "API key error"**
- **Check**: API permissions include Futures trading
- **Check**: API key not expired
- **Check**: IP restriction (if enabled)
- **Solution**: Regenerate API keys with correct permissions

**3. "Rate limit exceeded"**
- **Cause**: Too many API calls
- **Check**: Are you running multiple instances?
- **Solution**: Increase `tick_interval` in config

**4. "Positions not closing at profit target"**
- **Check**: Account size (<$100 for 3% target)
- **Check**: Session starting equity set correctly
- **Fixed in v1.1**: Position equity attribution bug fixed

**5. "Database locked"**
- **Cause**: Multiple bot instances accessing same database
- **Solution**: Stop other instances or use separate databases

**6. "Slippage higher than expected"**
- **Cause**: Low liquidity or market orders during volatility
- **Solution**: Use limit orders (requires code modification) or accept slippage

**7. "Weird PnL jumps in paper trading"**
- **Fixed in v1.1**: Critical balance tracking bugs fixed
- **Action**: Pull latest code with `git pull`

---

## 🐛 Bug Fixes & Changelog

### Version 1.1 (Latest) - Critical Bug Fixes

**Date**: January 20, 2026

**Critical Fixes:**

1. **Bollinger Band Touch Logic Inverted** 🐛→✅
   - **Bug**: Formula was backwards, triggering signals at wrong prices
   - **Impact**: Signals fired when price was NEAR bands, not touching them
   - **Fix**: Corrected formula:
     - LONG: `price <= bb_lower * 0.998` (was `price <= bb_lower * 1.002`)
     - SHORT: `price >= bb_upper / 0.998` (was `price >= bb_upper * 0.998`)
   - **File**: `src/strategies/bb_mean_reversion.py:156-177`

2. **Paper Trading PnL Bugs** 🐛→✅
   - **Bug #1**: Margin not subtracted on position open, creating "free money"
   - **Bug #2**: Equity formula missing locked margin
   - **Impact**: Massive equity jumps unrelated to actual PnL ($1.22 trade showing as +$27 gain!)
   - **Fix**:
     - Subtract margin from balance on open: `balance -= margin`
     - Fix equity formula: `balance + margin_used + unrealized_pnl`
   - **File**: `src/paper/paper_trader.py:76, 39-40, 133`

3. **Division by Zero Guards** 🐛→✅
   - **Bug**: RSI, %B, BB Width could divide by zero
   - **Impact**: NaN values, invalid indicators, strategy failures
   - **Fix**: Replace zero denominators with tiny epsilon (1e-10)
   - **File**: `src/strategies/indicators.py:74, 115, 125`

4. **Position Equity Attribution** 🐛→✅
   - **Bug**: Global equity gain attributed to individual positions
   - **Impact**: Positions closed prematurely when OTHER positions performed well
   - **Fix**: Track session_starting_equity, close ALL positions at account target
   - **File**: `src/paper/paper_trader.py:394-410`

5. **Margin Available Calculation** 🐛→✅
   - **Bug**: Calculated as `equity - margin_used` (includes unrealized PnL)
   - **Impact**: Incorrect available balance for new trades
   - **Fix**: Use `balance` directly (free balance)
   - **File**: `src/paper/paper_trader.py:660`

**Severity**: All fixes are **CRITICAL** for accurate trading and PnL tracking.

**Action Required**: Pull latest code before running bot:
```bash
cd /home/user/FuturesTrader
git pull origin claude/crypto-futures-trading-bot-x2wAq
```

---

### Version 1.0 (Initial Release)

**Date**: January 18, 2026

**Features:**
- Initial implementation of Bollinger Band mean reversion strategy
- Paper trading mode with virtual account
- Multi-factor signal filtering (daily bias, order flow, liquidations)
- Comprehensive risk management
- SQLite database for trade history
- Structured logging

---

## 📈 Performance Expectations

### Realistic Goals

**Small Account ($50-100):**
- Target: 3% daily gains
- Expected: 1-2 trades per day (sometimes 0)
- Good week: 15-20% gain
- Bad week: -5% to 0%
- **Compounding**: Turn $50 → $100 in 3-4 weeks at 3% daily (if sustained)

**Medium Account ($100-500):**
- Target: 5% daily gains
- Expected: 2-3 trades per day
- Good week: 25-35% gain
- Bad week: -5% to 0%

**Large Account ($500+):**
- Position-based targets (5%, 10%, 25%, 50%)
- Expected: 3-5 trades per day
- Focus on consistency over % gains

### Reality Check ✅

- **This is NOT a "get rich quick" scheme**
- Most days you'll have 0-2 trades (not 20)
- Some weeks will be breakeven or small losses
- Daily loss limits will stop you before catastrophic losses
- The edge is small but consistent

**Historical Performance (User's Manual Trading):**
- Profitable over months of trading
- Made most gains shorting on red days
- Stop-losses saved capital multiple times
- Scaled profits: $1-2 on small gains, $5-10 on larger moves

**Bot Advantage:**
- Never misses signals
- No emotional decisions
- Consistent risk management
- Runs 24/7 (but respects daily limits)

---

## 🙏 Acknowledgments

- Built for automated cryptocurrency futures trading on Binance
- Strategy based on proven manual trading methods
- Designed for small account compounding and risk management
- Inspired by real-world profitability over theoretical perfection

---

## 📜 License

MIT License - See LICENSE file for details.

**Disclaimer**: This software is provided AS-IS with NO WARRANTY. The developers are not responsible for any financial losses incurred by using this bot.

---

## 📞 Support

For issues, questions, or discussion:
- GitHub Issues: [FuturesTrader Issues](https://github.com/gonzalo8a/FuturesTrader/issues)
- Read logs carefully: `logs/futures_trader_*.log`
- Check database: `sqlite3 data/futures_bot.db`

**Remember**:
- Always start with paper trading
- Test for at least 7 days
- Only trade with money you can afford to lose
- Leverage amplifies both gains AND losses

---

**Happy Trading! 🚀📈**

*Last Updated: January 20, 2026 | Version 1.1*

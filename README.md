# FuturesTrader - Automated Cryptocurrency Futures Day Trading Bot

**⚠️ EXTREME RISK WARNING**

This bot trades cryptocurrency futures with **20x leverage** and **50% capital per trade**. This is an extremely aggressive strategy that can result in:
- **Total loss of capital**
- **Liquidation in minutes** during adverse market conditions
- **Rapid drawdowns** in volatile markets

**DO NOT** use this bot unless you:
1. Fully understand futures trading and leverage
2. Can afford to lose your entire trading capital
3. Have thoroughly tested in paper trading mode for at least 7 days
4. Accept that past performance does not guarantee future results

---

## Overview

FuturesTrader automates a proven Bollinger Band mean reversion strategy on Binance USDT-M Futures (BTC/USDT). The strategy is based on a manual trading method that has successfully grown small capital through high-leverage intraday trading.

### Key Features

- **Proven Strategy**: Bollinger Band mean reversion on 15m timeframe
- **Paper Trading**: Real-time simulation with live market data (NO REAL TRADES)
- **Risk Management**: Position sizing, stop-losses, daily limits, circuit breakers
- **Conservative Defaults**: While aggressive, the bot enforces risk limits
- **Full Logging**: Detailed trade logs and performance tracking
- **SQLite Storage**: Persistent storage of trades, positions, and account snapshots

### Strategy Details

- **Symbol**: BTC/USDT Perpetual Futures
- **Timeframe**: 15 minutes
- **Entry**: Price touches outer Bollinger Band (2 std dev)
- **Direction**: Mean reversion (price at upper band → SHORT, lower band → LONG)
- **Position Size**: 50% of equity per trade (configurable)
- **Leverage**: 20x (configurable)
- **Stop-Loss**: 25% of position value (≈1.25% price move at 20x leverage)
- **Take-Profit**: Multi-level (5%, 10%, 25%, 50%+)
- **Filters**: Volume, spread, volatility checks

---

## Installation (Ubuntu 22.04 + VS Code)

### Prerequisites

- Ubuntu 22.04 LTS (or similar Linux distribution)
- Internet connection
- Binance account with Futures enabled
- At least $50 in Binance Futures wallet (for live trading)

### Step 1: Install Python 3.10+

```bash
# Update package list
sudo apt update

# Install Python 3.10+ and pip
sudo apt install -y python3 python3-pip python3-venv

# Verify installation
python3 --version  # Should be 3.10 or higher
pip3 --version
```

**Troubleshooting Python/pip issues:**

If `pip3` doesn't work:
```bash
# Reinstall pip
sudo apt remove python3-pip
sudo apt install python3-pip

# Or install pip manually
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py
```

If you get "externally managed environment" error:
```bash
# Use virtual environment (recommended - see Step 4)
```

### Step 2: Install Git and VS Code

```bash
# Install Git
sudo apt install -y git

# Install VS Code
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
sudo install -o root -g root -m 644 packages.microsoft.gpg /etc/apt/trusted.gpg.d/
sudo sh -c 'echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'

sudo apt update
sudo apt install -y code

# Launch VS Code
code .
```

**Install VS Code Python Extension:**
1. Open VS Code
2. Click Extensions icon (left sidebar)
3. Search for "Python"
4. Install "Python" by Microsoft

### Step 3: Navigate to Project Directory

```bash
cd /home/user/FuturesTrader
```

### Step 4: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Your prompt should now show (.venv)
```

**Note**: Always activate the virtual environment before running the bot:
```bash
source .venv/bin/activate
```

### Step 5: Install Dependencies

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

**Troubleshooting dependency installation:**

If you encounter errors with `pandas-ta`:
```bash
pip install pandas-ta --no-deps
pip install pandas numpy
```

If you encounter SSL errors:
```bash
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### Step 6: Configure Environment Variables

```bash
# Copy example .env file
cp .env.example .env

# Edit .env file
nano .env
```

**Add your Binance API credentials:**

```env
BINANCE_API_KEY=your_actual_api_key_here
BINANCE_API_SECRET=your_actual_api_secret_here
BINANCE_TESTNET=false
```

**IMPORTANT**: To create Binance API keys:
1. Go to https://www.binance.com/en/my/settings/api-management
2. Create new API key
3. **Enable ONLY "Enable Futures" permission**
4. **DO NOT** enable Spot Trading, Margin, or Withdrawals
5. Restrict API key by IP address (if possible)
6. Save the API key and secret in `.env` file

**Security:**
```bash
# Make .env file readable only by you
chmod 600 .env

# Verify .env is in .gitignore (it should be)
cat .gitignore | grep .env
```

### Step 7: Test Installation

```bash
# Activate virtual environment (if not already active)
source .venv/bin/activate

# Test configuration loading
python -c "from src.utils.config import load_config; c = load_config('config/bb_mean_reversion.yaml'); print(f'✓ Config loaded: {c.mode} mode')"

# Test Binance API connection
python src/data/binance_client.py
```

You should see:
```
✓ Server time: ...
✓ BTC/USDT price: $...
✓ 24h volume: $...
✅ All tests passed!
```

---

## Usage

### Paper Trading Mode (Recommended First)

Paper trading uses **real-time market data** but **simulates all order execution**. No real trades are placed.

```bash
# Activate virtual environment
source .venv/bin/activate

# Run paper trading
python main.py paper --config config/bb_mean_reversion.yaml
```

**What to expect:**
- Bot connects to Binance and fetches live BTC/USDT prices
- Generates trading signals based on Bollinger Bands
- Simulates order execution with realistic slippage and fees
- Logs all activity to console and `logs/` directory
- Stores trades in `data/futures_trader.db` SQLite database

**Monitoring:**
- Watch console output for trade notifications
- Check `logs/` directory for detailed JSON logs
- Use Ctrl+C to stop gracefully

**Recommended duration**: Run for **at least 7 days** before considering live trading

### Backtest Mode

Historical simulation (not fully implemented yet - use paper trading for testing)

```bash
python main.py backtest --config config/bb_mean_reversion.yaml
```

### Live Trading Mode (⚠️ REAL MONEY)

**DO NOT RUN THIS UNTIL:**
1. ✅ You have successfully run paper trading for 7+ days
2. ✅ You understand the risks and can afford total loss
3. ✅ You have verified stop-loss logic works correctly
4. ✅ You have tested the kill switch
5. ✅ Your API keys have ONLY Futures permission (no withdrawals)

```bash
python main.py live --config config/bb_mean_reversion.yaml
```

**Note**: Live trading is currently disabled for safety. Complete paper trading first.

---

## Configuration

All settings are in `config/bb_mean_reversion.yaml`.

### Key Settings to Review:

```yaml
# Trading mode
mode: paper  # paper | backtest | live

# Risk settings
risk:
  starting_capital: 50.0           # Starting balance
  max_position_size_pct: 50.0      # 50% of equity per trade
  max_leverage: 20                 # 20x leverage
  stop_loss_pct: 25.0              # Stop at 25% position loss
  max_daily_loss_pct: 30.0         # Stop trading if down 30% for the day
  max_drawdown_pct: 50.0           # Disable bot if down 50% from peak

# Strategy parameters
strategy:
  params:
    bb_period: 20                  # Bollinger Band period
    bb_std: 2.0                    # Standard deviation (2 sigma)
    volume_filter_multiplier: 0.1  # Require 10% of average volume
```

**To modify settings:**
```bash
nano config/bb_mean_reversion.yaml
# Edit values, save (Ctrl+O), exit (Ctrl+X)
```

---

## Monitoring & Logs

### Console Output

Real-time output shows:
- Trade entries and exits
- Current equity and PnL
- Risk limit status
- Errors and warnings

### Log Files

All logs saved to `logs/` directory:
```bash
# View latest log
tail -f logs/paper_*.log

# Search for errors
grep ERROR logs/paper_*.log
```

### Database

All trades stored in SQLite database:
```bash
# View database
sqlite3 data/futures_trader.db

# Show all trades
sqlite> SELECT * FROM trades ORDER BY entry_time DESC LIMIT 10;

# Show account snapshots
sqlite> SELECT timestamp, equity, daily_pnl, drawdown_pct FROM account_snapshots ORDER BY timestamp DESC LIMIT 10;
```

---

## Safety Features

### Built-in Protections

1. **Position-Level:**
   - Stop-loss on every trade (≈1.25% at 20x leverage)
   - Liquidation buffer (emergency exit at 70% of liq price)
   - Time-based exit (close after 4 hours if stagnant)

2. **Account-Level:**
   - Max daily loss limit (30% → stop trading for the day)
   - Max drawdown limit (50% → disable bot completely)
   - Position size limits (50% max per trade)
   - Consecutive loss reduction (reduce size after 4 losses)

3. **Circuit Breakers:**
   - Spread anomaly detection (pause if spread > 0.5%)
   - Volatility spike detection (pause if ATR > 3x normal)
   - Volume collapse detection (pause if volume drops)
   - API error detection (pause if >20% requests fail)

4. **Kill Switch:**
   - Automatic shutdown on liquidation
   - Manual trigger (Ctrl+C or create file `.KILL_SWITCH`)
   - Closes all positions before shutdown

### Manual Kill Switch

To immediately stop the bot and close positions:
```bash
# Method 1: Keyboard interrupt
Ctrl+C

# Method 2: Create kill switch file
touch .KILL_SWITCH
```

---

## Performance Expectations

### Realistic Expectations

- **Starting capital**: $50
- **Target**: $10,000 (200x return)
- **Reality**: This target is extremely unrealistic and unlikely

**Why?**
- 200x return requires near-perfect execution
- Futures trading is zero-sum (for every winner, there's a loser)
- High leverage amplifies both gains AND losses
- Black swan events (flash crashes) can liquidate positions instantly
- Slippage and fees erode profits

### Conservative Goals

- **Survival**: Don't get liquidated
- **Consistency**: Small, steady gains over time
- **Risk-adjusted returns**: Positive Sharpe ratio
- **Learning**: Understand what works and what doesn't

### Typical Outcomes (No Guarantees)

- **Good case**: 10-30% monthly return with controlled risk
- **Expected case**: Break-even to small gains, some drawdowns
- **Bad case**: 20-50% drawdown requiring recovery
- **Worst case**: Total loss due to liquidation or black swan event

---

## Troubleshooting

### "ImportError: No module named ..."

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### "Config file not found"

```bash
# Check current directory
pwd

# Should be in project root (FuturesTrader/)
# If not:
cd /home/user/FuturesTrader

# Run again
python main.py paper --config config/bb_mean_reversion.yaml
```

### "Binance API error: Invalid API key"

Check your `.env` file:
```bash
cat .env
```

Verify:
- API key and secret are correct (no extra spaces)
- API key has Futures permission enabled
- API key is not expired

### "Permission denied" errors

```bash
# Fix permissions
chmod +x main.py
chmod 600 .env
```

### Bot stops immediately

Check logs:
```bash
tail -50 logs/paper_*.log
```

Common causes:
- API rate limit exceeded (wait 1 minute)
- Network connectivity issues
- Insufficient data (wait a few minutes for candles to populate)

---

## Quick Start Checklist

- [ ] Install Python 3.10+, pip, Git, VS Code
- [ ] Navigate to project directory: `cd /home/user/FuturesTrader`
- [ ] Create virtual environment: `python3 -m venv .venv`
- [ ] Activate virtual environment: `source .venv/bin/activate`
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Create `.env` file with Binance API keys
- [ ] Test installation: `python src/data/binance_client.py`
- [ ] Review config: `nano config/bb_mean_reversion.yaml`
- [ ] Run paper trading: `python main.py paper --config config/bb_mean_reversion.yaml`
- [ ] Monitor for 7+ days before considering live trading
- [ ] **NEVER** rush into live trading - capital preservation > speed

---

## Disclaimer

**THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.**

- ✅ You accept full responsibility for any losses
- ✅ You understand futures trading can result in total capital loss
- ✅ You have tested thoroughly in paper trading mode
- ✅ You can afford to lose your entire trading capital
- ✅ Past performance does not guarantee future results
- ✅ The creators assume no liability for your trading results

**Cryptocurrency futures trading is extremely risky. Only trade with money you can afford to lose.**

---

## Support & Resources

- **Binance Futures Documentation**: https://binance-docs.github.io/apidocs/futures/en/
- **Project Structure**: See `ARCHITECTURE.md` for detailed technical documentation
- **Configuration**: See `config/bb_mean_reversion.yaml` (well-commented)
- **Logs**: Check `logs/` directory for detailed execution logs

---

**Good luck, trade safely, and remember: preservation of capital is the first priority. 🛡️**
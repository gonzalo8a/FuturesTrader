"""
Paper Trading Mode - Simulates trading with real market data.

Implements:
- Real-time market data from Binance
- Local simulation of order execution
- Realistic slippage, fees, and funding
- Virtual account balance tracking
- All logic identical to live trading (except no real orders)
"""

import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd

from ..data.binance_client import BinanceFuturesClient
from ..data.database import Database
from ..strategies.bb_mean_reversion import BBMeanReversionStrategy
from ..risk.risk_manager import RiskManager
from ..risk.liquidation import calculate_liquidation_price, is_near_liquidation
from ..utils.logger import get_logger


class VirtualAccount:
    """Tracks virtual account balance and positions for paper trading."""

    def __init__(self, starting_balance: float, mode: str = "paper"):
        self.mode = mode
        self.balance = starting_balance
        self.starting_balance = starting_balance
        self.equity = starting_balance
        self.unrealized_pnl = 0.0
        self.margin_used = 0.0
        self.positions: Dict[str, Dict] = {}  # position_id -> position data

    def get_equity(self) -> float:
        """Get current equity (balance + margin in use + unrealized PnL)."""
        return self.balance + self.margin_used + self.unrealized_pnl

    def get_position_by_symbol(self, symbol: str) -> Optional[Dict]:
        """Get open position for symbol."""
        for pos in self.positions.values():
            if pos['symbol'] == symbol and pos['status'] == 'OPEN':
                return pos
        return None

    def open_position(
        self,
        position_id: str,
        symbol: str,
        side: str,
        size: float,
        entry_price: float,
        leverage: int,
        margin: float,
        liquidation_price: float
    ) -> None:
        """Open a new position."""
        self.positions[position_id] = {
            'position_id': position_id,
            'symbol': symbol,
            'side': side,
            'size': size,
            'entry_price': entry_price,
            'leverage': leverage,
            'margin': margin,
            'liquidation_price': liquidation_price,
            'unrealized_pnl': 0.0,
            'status': 'OPEN',
            'opened_at': int(time.time() * 1000),
            'updated_at': int(time.time() * 1000),
        }
        # Lock margin from available balance
        self.balance -= margin
        self.margin_used += margin

    def close_position(
        self,
        position_id: str,
        exit_price: float,
        fees: float,
        funding_fees: float = 0.0
    ) -> float:
        """Close a position and realize PnL."""
        if position_id not in self.positions:
            raise ValueError(f"Position {position_id} not found")

        pos = self.positions[position_id]

        # Calculate realized PnL
        if pos['side'] == 'LONG':
            pnl = (exit_price - pos['entry_price']) * pos['size']
        else:  # SHORT
            pnl = (pos['entry_price'] - exit_price) * pos['size']

        # Subtract fees and funding
        pnl -= fees
        pnl -= funding_fees

        # Update balance
        self.balance += (pos['margin'] + pnl)
        self.margin_used -= pos['margin']

        # Mark position as closed
        pos['status'] = 'CLOSED'
        pos['exit_price'] = exit_price
        pos['realized_pnl'] = pnl
        pos['fees'] = fees
        pos['funding_fees'] = funding_fees
        pos['closed_at'] = int(time.time() * 1000)

        return pnl

    def update_unrealized_pnl(self, current_prices: Dict[str, float]) -> None:
        """Update unrealized PnL for all open positions."""
        total_unrealized = 0.0

        for pos in self.positions.values():
            if pos['status'] == 'OPEN':
                symbol = pos['symbol']
                if symbol in current_prices:
                    current_price = current_prices[symbol]

                    if pos['side'] == 'LONG':
                        unrealized = (current_price - pos['entry_price']) * pos['size']
                    else:  # SHORT
                        unrealized = (pos['entry_price'] - current_price) * pos['size']

                    pos['unrealized_pnl'] = unrealized
                    total_unrealized += unrealized

        self.unrealized_pnl = total_unrealized
        self.equity = self.balance + self.margin_used + self.unrealized_pnl

    def get_open_positions(self) -> List[Dict]:
        """Get all open positions."""
        return [pos for pos in self.positions.values() if pos['status'] == 'OPEN']


class PaperTrader:
    """Paper trading engine with simulated execution."""

    def __init__(self, config):
        """
        Initialize paper trader.

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = get_logger()

        # Initialize components
        self.client = BinanceFuturesClient(
            config.api_key,
            config.api_secret,
            testnet=config.exchange.testnet
        )
        self.db = Database(config.data.db_path)
        self.strategy = BBMeanReversionStrategy(config)
        self.risk_mgr = RiskManager(config, self.logger)

        # Virtual account
        self.account = VirtualAccount(config.paper.starting_balance, mode="paper")

        # Simulation settings
        self.simulate_slippage = config.paper.simulate_slippage
        self.slippage_bps = config.paper.slippage_bps
        self.simulate_funding = config.paper.simulate_funding
        self.funding_interval_hours = config.paper.funding_interval_hours

        # State
        self.running = False
        self.last_funding_time = time.time()

        # Track session starting equity for account-level profit targets
        self.session_starting_equity = config.paper.starting_balance

        self.logger.info(f"Paper Trader initialized with ${config.paper.starting_balance} virtual balance")

    def run(self) -> None:
        """Run paper trading loop."""
        self.running = True
        self.logger.info("🚀 Starting paper trading mode...")

        # Main loop
        iteration = 0
        while self.running:
            try:
                iteration += 1

                # 1. Fetch latest market data
                current_price = self.client.get_current_price(self.config.market.symbol)

                # 2. Update unrealized PnL
                self.account.update_unrealized_pnl({self.config.market.symbol: current_price})

                # 3. Update risk manager equity
                self.risk_mgr.update_equity(self.account.get_equity())

                # 4. Check for liquidations (simulated)
                self._check_liquidations(current_price)

                # 5. Manage open positions (check stops, targets)
                self._manage_positions(current_price)

                # 6. Apply funding fees (if enabled)
                if self.simulate_funding:
                    self._apply_funding_fees()

                # 7. Generate new signals (if no open positions)
                if len(self.account.get_open_positions()) < self.config.risk.max_concurrent_positions:
                    self._check_for_signals(current_price)

                # 8. Log performance every 10 iterations
                if iteration % 10 == 0:
                    self._log_performance(current_price)

                # 9. Save account snapshot to database
                if iteration % 20 == 0:
                    self._save_snapshot(current_price)

                # Sleep (to avoid hammering API)
                time.sleep(5)  # Check every 5 seconds

            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt detected, shutting down...")
                self.stop()
                break

            except Exception as e:
                self.logger.error(f"Error in paper trading loop: {e}", exc_info=True)
                time.sleep(10)  # Back off on error

        self.logger.info("Paper trading stopped")

    def _check_for_signals(self, current_price: float) -> None:
        """Check for new trading signals."""
        try:
            # Fetch recent candle data (15m)
            df = self._get_recent_candles()

            if df is None or len(df) < 50:
                return  # Not enough data

            # Get orderbook for spread check
            orderbook = self.client.get_orderbook(self.config.market.symbol, limit=5)

            # Fetch daily candles for trend bias
            daily_df = self._get_daily_candles()

            # Fetch recent trades for order flow analysis
            recent_trades = self._get_recent_trades()

            # Fetch recent liquidations
            recent_liquidations = self._get_recent_liquidations()

            # Generate signal with enhanced filters
            signal = self.strategy.generate_signal(
                df,
                current_price,
                orderbook,
                daily_candles=daily_df,
                recent_trades=recent_trades,
                recent_liquidations=recent_liquidations
            )

            if signal is None:
                return  # No signal

            # Validate with risk manager
            equity = self.account.get_equity()
            open_positions = self.account.get_open_positions()

            valid, reason, position_params = self.risk_mgr.validate_trade(
                signal,
                equity,
                open_positions,
                current_price
            )

            if not valid:
                self.logger.debug(f"Signal rejected: {reason}")
                return

            # Execute virtual trade
            self._execute_entry(signal, position_params, current_price)

        except Exception as e:
            self.logger.error(f"Error checking for signals: {e}", exc_info=True)

    def _execute_entry(self, signal, position_params: Dict, current_price: float) -> None:
        """Execute entry (simulated)."""
        # Simulate slippage
        if self.simulate_slippage:
            slippage_pct = self.slippage_bps / 10000
            if signal.side == 'LONG':
                fill_price = current_price * (1 + slippage_pct)
            else:
                fill_price = current_price * (1 - slippage_pct)
        else:
            fill_price = current_price

        # Calculate fees (taker fee)
        notional = fill_price * position_params['size']
        fee = notional * (self.config.fees.taker / 100)

        # Deduct fee from balance
        self.account.balance -= fee

        # Calculate liquidation price
        liq_price = calculate_liquidation_price(
            fill_price,
            position_params['leverage'],
            signal.side,
            self.config.exchange.margin_mode
        )

        # Open position
        position_id = str(uuid.uuid4())
        self.account.open_position(
            position_id=position_id,
            symbol=signal.symbol,
            side=signal.side,
            size=position_params['size'],
            entry_price=fill_price,
            leverage=position_params['leverage'],
            margin=position_params['margin'],
            liquidation_price=liq_price
        )

        # Log trade
        self.logger.info(
            f"📈 OPENED {signal.side} {position_params['size']:.4f} {signal.symbol} "
            f"@ ${fill_price:,.2f} ({position_params['leverage']}x) "
            f"| Stop: ${position_params['stop_price']:,.2f} | Fee: ${fee:.2f}"
        )

        # Save to database
        self.db.insert_trade({
            'mode': 'paper',
            'trade_id': position_id,
            'symbol': signal.symbol,
            'strategy': self.config.strategy.name,
            'side': signal.side,
            'entry_time': int(time.time() * 1000),
            'entry_price': fill_price,
            'size': position_params['size'],
            'leverage': position_params['leverage'],
            'notional': notional,
            'fees': fee,
            'metadata': signal.indicators
        })

        # Store stop-loss for this position (for checking later)
        self.account.positions[position_id]['stop_price'] = position_params['stop_price']

        # Calculate and store take-profit levels
        atr_value = signal.indicators.get('atr', 500)  # Default ATR if not available
        tp_levels = self.strategy.calculate_take_profit_levels(
            fill_price,
            signal.side,
            atr_value
        )
        self.account.positions[position_id]['tp_levels'] = tp_levels
        self.account.positions[position_id]['tp_hit'] = [False] * len(tp_levels)

    def _manage_positions(self, current_price: float) -> None:
        """Manage open positions (check stops, targets, time exits)."""
        for pos in list(self.account.get_open_positions()):
            position_id = pos['position_id']

            # Check liquidation
            if is_near_liquidation(current_price, pos['liquidation_price'], pos['side'], threshold_pct=1.0):
                self.logger.critical(f"⚠️ Position {position_id} near liquidation!")

            # Check stop-loss
            stop_price = pos.get('stop_price')
            if stop_price:
                stop_hit = False
                if pos['side'] == 'LONG' and current_price <= stop_price:
                    stop_hit = True
                elif pos['side'] == 'SHORT' and current_price >= stop_price:
                    stop_hit = True

                if stop_hit:
                    self._close_position(position_id, current_price, "stop_loss")
                    continue

        # ACCOUNT-BASED PROFIT TARGETS (for small accounts < $100)
        # Check once per iteration if SESSION-LEVEL profit target is hit
        # Focus on 3-5% account equity gains rather than huge position targets
        current_equity = self.account.get_equity()
        session_equity_gain_pct = ((current_equity - self.session_starting_equity) / self.session_starting_equity) * 100

        # Close ALL positions if account-level target is hit
        if self.session_starting_equity < 100 and session_equity_gain_pct >= 3.0:
            # Small account: hit 3% session gain
            self.logger.info(f"🎯 Account profit target hit: {session_equity_gain_pct:.1f}% gain, closing all positions")
            for pos in list(self.account.get_open_positions()):
                self._close_position(pos['position_id'], current_price, f"session_target_{session_equity_gain_pct:.1f}%")
            return  # Exit early, all positions closed

        elif self.session_starting_equity < 500 and session_equity_gain_pct >= 5.0:
            # Medium account: hit 5% session gain
            self.logger.info(f"🎯 Account profit target hit: {session_equity_gain_pct:.1f}% gain, closing all positions")
            for pos in list(self.account.get_open_positions()):
                self._close_position(pos['position_id'], current_price, f"session_target_{session_equity_gain_pct:.1f}%")
            return  # Exit early, all positions closed

        # Now check individual position management (stops, position-based targets, time exits)
        for pos in list(self.account.get_open_positions()):
            position_id = pos['position_id']

            # Check liquidation
            if is_near_liquidation(current_price, pos['liquidation_price'], pos['side'], threshold_pct=1.0):
                self.logger.critical(f"⚠️ Position {position_id} near liquidation!")

            # Check stop-loss
            stop_price = pos.get('stop_price')
            if stop_price:
                stop_hit = False
                if pos['side'] == 'LONG' and current_price <= stop_price:
                    stop_hit = True
                elif pos['side'] == 'SHORT' and current_price >= stop_price:
                    stop_hit = True

                if stop_hit:
                    self._close_position(position_id, current_price, "stop_loss")
                    continue

            # Check take-profit levels (position-based, for larger accounts)
            tp_levels = pos.get('tp_levels', [])
            tp_hit = pos.get('tp_hit', [False] * len(tp_levels))

            for i, tp in enumerate(tp_levels):
                if not tp_hit[i]:
                    tp_price = tp['price']
                    tp_triggered = False

                    if pos['side'] == 'LONG' and current_price >= tp_price:
                        tp_triggered = True
                    elif pos['side'] == 'SHORT' and current_price <= tp_price:
                        tp_triggered = True

                    if tp_triggered:
                        # Partial close (scale out)
                        size_to_close_pct = tp['size_pct'] / 100
                        # For simplicity, just close entire position at first TP (full implementation would scale out)
                        self._close_position(position_id, current_price, f"take_profit_{tp['pct']:.0f}%")
                        tp_hit[i] = True
                        break  # Exit after first TP hit

            # Check time-based exit
            elapsed_minutes = (time.time() * 1000 - pos['opened_at']) / 60000
            if elapsed_minutes > self.config.risk.max_position_duration_minutes:
                self._close_position(position_id, current_price, "time_stop")

    def _close_position(self, position_id: str, exit_price: float, exit_reason: str) -> None:
        """Close a position (simulated)."""
        pos = self.account.positions.get(position_id)
        if not pos or pos['status'] != 'OPEN':
            return

        # Simulate slippage on exit
        if self.simulate_slippage:
            slippage_pct = self.slippage_bps / 10000
            if pos['side'] == 'LONG':
                fill_price = exit_price * (1 - slippage_pct)  # Sell lower
            else:
                fill_price = exit_price * (1 + slippage_pct)  # Buy higher
        else:
            fill_price = exit_price

        # Calculate fees
        notional = fill_price * pos['size']
        fee = notional * (self.config.fees.taker / 100)

        # Close position
        pnl = self.account.close_position(position_id, fill_price, fee, funding_fees=0.0)

        # Update risk manager
        self.risk_mgr.record_trade_result(pnl, exit_reason)

        # Log
        pnl_pct = (pnl / pos['margin']) * 100
        self.logger.info(
            f"📉 CLOSED {pos['side']} {pos['size']:.4f} {pos['symbol']} "
            f"@ ${fill_price:,.2f} | PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%) | Reason: {exit_reason}"
        )

        # Update database
        self.db.update_trade(position_id, {
            'exit_time': int(time.time() * 1000),
            'exit_price': fill_price,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason
        })

    def _check_liquidations(self, current_price: float) -> None:
        """Check if any positions should be liquidated."""
        for pos in list(self.account.get_open_positions()):
            liq_price = pos['liquidation_price']

            liquidated = False
            if pos['side'] == 'LONG' and current_price <= liq_price:
                liquidated = True
            elif pos['side'] == 'SHORT' and current_price >= liq_price:
                liquidated = True

            if liquidated:
                self.logger.critical(f"💀 LIQUIDATION: Position {pos['position_id']} liquidated!")
                # Close at liquidation price with 100% loss
                self.account.close_position(pos['position_id'], liq_price, fees=0.0)
                self.risk_mgr.record_trade_result(-pos['margin'], "liquidation")

                # Trigger kill switch
                self.logger.critical("🛑 Kill switch activated due to liquidation")
                self.stop()

    def _apply_funding_fees(self) -> None:
        """Apply funding fees every 8 hours (simulated)."""
        elapsed_hours = (time.time() - self.last_funding_time) / 3600

        if elapsed_hours >= self.funding_interval_hours:
            # Get funding rate
            try:
                mark_price_data = self.client.get_mark_price(self.config.market.symbol)
                funding_rate = float(mark_price_data.get('lastFundingRate', 0.0001))
            except:
                funding_rate = self.config.fees.funding_rate_default / 100  # Default 0.01%

            # Apply to open positions
            for pos in self.account.get_open_positions():
                notional = pos['entry_price'] * pos['size']
                funding_fee = notional * funding_rate

                # LONG pays funding if positive, receives if negative
                # SHORT receives funding if positive, pays if negative
                if pos['side'] == 'LONG':
                    self.account.balance -= funding_fee
                else:
                    self.account.balance += funding_fee

                self.logger.debug(f"Funding fee applied: ${funding_fee:+.4f} to {pos['side']} position")

            self.last_funding_time = time.time()

    def _get_recent_candles(self) -> Optional[pd.DataFrame]:
        """Fetch recent candle data (1 week for proper indicator calculation)."""
        try:
            # Fetch 1 week of data: 7 days * 24 hours * 4 (15m candles/hour) = 672
            # Using 700 for buffer
            klines = self.client.get_klines(
                self.config.market.symbol,
                self.config.market.timeframe,
                limit=700
            )

            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            df['timestamp'] = pd.to_numeric(df['timestamp'])
            df['open'] = pd.to_numeric(df['open'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['close'] = pd.to_numeric(df['close'])
            df['volume'] = pd.to_numeric(df['volume'])

            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

        except Exception as e:
            self.logger.error(f"Error fetching candles: {e}")
            return None

    def _get_daily_candles(self) -> Optional[pd.DataFrame]:
        """Fetch daily candle data for trend bias (30 days of context)."""
        try:
            klines = self.client.get_klines(
                self.config.market.symbol,
                '1d',  # Daily timeframe
                limit=30  # Increased from 10 for better trend analysis
            )

            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            df['timestamp'] = pd.to_numeric(df['timestamp'])
            df['open'] = pd.to_numeric(df['open'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['close'] = pd.to_numeric(df['close'])
            df['volume'] = pd.to_numeric(df['volume'])

            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

        except Exception as e:
            self.logger.error(f"Error fetching daily candles: {e}")
            return None

    def _get_recent_trades(self) -> Optional[List]:
        """Fetch recent trades for order flow analysis."""
        try:
            # Fetch last 100 trades
            trades = self.client._request('GET', '/fapi/v1/trades', params={
                'symbol': self.config.market.symbol,
                'limit': 100
            }, weight=1)
            return trades

        except Exception as e:
            self.logger.error(f"Error fetching recent trades: {e}")
            return None

    def _get_recent_liquidations(self) -> Optional[List]:
        """Fetch recent liquidation orders."""
        try:
            # Fetch recent forced liquidation orders
            liquidations = self.client._request('GET', '/fapi/v1/allForceOrders', params={
                'symbol': self.config.market.symbol,
                'limit': 50
            }, weight=1)
            return liquidations

        except Exception as e:
            # Liquidation endpoint sometimes fails, that's okay
            self.logger.debug(f"Error fetching liquidations: {e}")
            return None

    def _log_performance(self, current_price: float) -> None:
        """Log current performance metrics."""
        equity = self.account.get_equity()
        pnl = equity - self.account.starting_balance
        pnl_pct = (pnl / self.account.starting_balance) * 100
        drawdown = ((self.risk_mgr.peak_equity - equity) / self.risk_mgr.peak_equity) * 100

        self.logger.info(
            f"💰 BTC: ${current_price:,.2f} | Equity: ${equity:.2f} | PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%) | "
            f"DD: {drawdown:.2f}% | Open: {len(self.account.get_open_positions())}"
        )

    def _save_snapshot(self, current_price: float) -> None:
        """Save account snapshot to database."""
        equity = self.account.get_equity()

        self.db.insert_account_snapshot({
            'mode': 'paper',
            'timestamp': int(time.time() * 1000),
            'current_price': current_price,
            'equity': equity,
            'balance': self.account.balance,
            'unrealized_pnl': self.account.unrealized_pnl,
            'margin_used': self.account.margin_used,
            'margin_available': self.account.balance,  # Free balance available for new trades
            'open_positions': len(self.account.get_open_positions()),
            'daily_pnl': self.risk_mgr.daily_pnl,
            'drawdown_pct': ((self.risk_mgr.peak_equity - equity) / self.risk_mgr.peak_equity) * 100
        })

    def stop(self) -> None:
        """Stop paper trading."""
        self.running = False
        self.logger.info("Stopping paper trader...")

        # Close all open positions
        current_price = self.client.get_current_price(self.config.market.symbol)
        for pos in list(self.account.get_open_positions()):
            self._close_position(pos['position_id'], current_price, "manual_shutdown")

        # Final performance summary
        equity = self.account.get_equity()
        pnl = equity - self.account.starting_balance
        pnl_pct = (pnl / self.account.starting_balance) * 100

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"PAPER TRADING SUMMARY")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Starting Balance: ${self.account.starting_balance:.2f}")
        self.logger.info(f"Final Equity: ${equity:.2f}")
        self.logger.info(f"Total PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
        self.logger.info(f"Peak Equity: ${self.risk_mgr.peak_equity:.2f}")
        self.logger.info(f"Total Trades: {self.risk_mgr.daily_trades}")
        self.logger.info(f"{'='*60}\n")


if __name__ == "__main__":
    from ..utils.config import load_config
    from ..utils.logger import init_logger

    config = load_config("config/bb_mean_reversion.yaml")
    config.mode = "paper"

    init_logger(config)

    trader = PaperTrader(config)
    trader.run()

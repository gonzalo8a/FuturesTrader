"""
Risk Manager - validates trades and monitors risk limits.
"""

import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque

from .liquidation import (
    calculate_liquidation_price,
    distance_to_liquidation,
    is_near_liquidation
)


class RiskManager:
    """
    Manages risk limits and validates trades.

    Enforces:
    - Position size limits
    - Leverage limits
    - Daily loss limits
    - Max drawdown limits
    - Consecutive loss handling
    - Circuit breakers
    """

    def __init__(self, config, logger):
        """
        Initialize risk manager.

        Args:
            config: Configuration object
            logger: Logger instance
        """
        self.config = config
        self.logger = logger

        # Risk limits
        self.max_position_size_pct = config.risk.max_position_size_pct
        self.max_leverage = config.risk.max_leverage
        self.hard_leverage_cap = config.risk.hard_leverage_cap
        self.max_concurrent_positions = config.risk.max_concurrent_positions
        self.max_trades_per_day = config.risk.max_trades_per_day
        self.max_daily_loss_pct = config.risk.max_daily_loss_pct
        self.max_drawdown_pct = config.risk.max_drawdown_pct

        # Consecutive loss handling
        self.max_consecutive_losses = config.risk.max_consecutive_losses
        self.consecutive_loss_size_reduction = config.risk.consecutive_loss_size_reduction

        # Circuit breakers
        self.circuit_breakers = config.circuit_breakers

        # State tracking
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.peak_equity = config.risk.starting_capital
        self.consecutive_losses = 0
        self.recent_stop_losses = deque(maxlen=10)
        self.trading_paused = False
        self.pause_reason = ""
        self.pause_until = None

        # Daily reset
        self.last_reset_date = datetime.utcnow().date()

    def validate_trade(
        self,
        signal,
        current_equity: float,
        open_positions: List[Dict],
        current_price: float
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate if a trade can be executed.

        Args:
            signal: Trading signal
            current_equity: Current account equity
            open_positions: List of open positions
            current_price: Current market price

        Returns:
            (is_valid, reason, position_params)
            position_params: {'size': float, 'leverage': int, 'stop_price': float, ...}
        """
        # Reset daily counters if new day
        self._check_daily_reset()

        # Check if trading is paused
        if self.trading_paused:
            if self.pause_until and datetime.utcnow() < self.pause_until:
                return False, f"Trading paused: {self.pause_reason}", None
            else:
                # Unpause
                self.trading_paused = False
                self.pause_reason = ""
                self.logger.info("Trading resumed after pause")

        # 1. Max concurrent positions
        if len(open_positions) >= self.max_concurrent_positions:
            return False, f"Max concurrent positions reached ({self.max_concurrent_positions})", None

        # 2. Max trades per day
        if self.daily_trades >= self.max_trades_per_day:
            return False, f"Max daily trades reached ({self.max_trades_per_day})", None

        # 3. Daily loss limit
        if self.daily_pnl < 0 and abs(self.daily_pnl / current_equity) * 100 > self.max_daily_loss_pct:
            self._pause_trading(
                f"Daily loss limit exceeded: {abs(self.daily_pnl):.2f} ({abs(self.daily_pnl/current_equity)*100:.2f}%)",
                until_tomorrow=True
            )
            return False, "Daily loss limit exceeded", None

        # 4. Max drawdown
        drawdown_pct = ((self.peak_equity - current_equity) / self.peak_equity) * 100
        if drawdown_pct > self.max_drawdown_pct:
            self._pause_trading(
                f"Max drawdown exceeded: {drawdown_pct:.2f}%",
                until_tomorrow=False  # Requires manual intervention
            )
            return False, "Max drawdown exceeded - TRADING DISABLED", None

        # 5. Calculate position size (with consecutive loss adjustment)
        position_size_pct = self.max_position_size_pct

        # Reduce size after consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            position_size_pct *= self.consecutive_loss_size_reduction
            self.logger.warning(
                f"Reducing position size to {position_size_pct:.1f}% "
                f"after {self.consecutive_losses} consecutive losses"
            )

        # Calculate position parameters
        position_params = self._calculate_position_params(
            signal,
            current_equity,
            position_size_pct,
            current_price
        )

        # 6. Validate leverage
        if position_params['leverage'] > self.hard_leverage_cap:
            return False, f"Leverage {position_params['leverage']}x exceeds hard cap {self.hard_leverage_cap}x", None

        # 7. Validate minimum order size
        # (This would check against exchange minimums, simplified here)
        if position_params['size'] < 0.001:  # Example minimum
            return False, "Position size below exchange minimum", None

        # 8. Liquidation distance check
        liq_price = calculate_liquidation_price(
            position_params['entry_price'],
            position_params['leverage'],
            signal.side,
            self.config.exchange.margin_mode
        )

        stop_price = position_params['stop_price']

        # Ensure stop-loss is significantly closer than liquidation
        if signal.side == "LONG":
            if stop_price <= liq_price:
                return False, "Stop-loss too close to liquidation price", None
        else:  # SHORT
            if stop_price >= liq_price:
                return False, "Stop-loss too close to liquidation price", None

        # All checks passed
        return True, "OK", position_params

    def _calculate_position_params(
        self,
        signal,
        current_equity: float,
        position_size_pct: float,
        current_price: float
    ) -> Dict:
        """Calculate position sizing and stops."""
        # Capital allocated to this trade
        allocated_capital = current_equity * (position_size_pct / 100)

        # Leverage (from config)
        leverage = min(self.max_leverage, self.hard_leverage_cap)

        # Notional position size
        notional_size = allocated_capital * leverage

        # Contract size (in base asset, e.g., BTC)
        size = notional_size / current_price

        # Calculate stop-loss price
        # User's method: 25% of position value = 1.25% price move at 20x leverage
        position_loss_pct = self.config.risk.stop_loss_pct / 100  # 0.25
        price_move_pct = position_loss_pct / leverage  # 0.0125 at 20x

        if signal.side == "LONG":
            stop_price = current_price * (1 - price_move_pct)
        else:  # SHORT
            stop_price = current_price * (1 + price_move_pct)

        # Margin required (isolated)
        margin = allocated_capital

        return {
            'size': size,
            'leverage': leverage,
            'notional': notional_size,
            'margin': margin,
            'entry_price': current_price,
            'stop_price': stop_price,
            'allocated_capital': allocated_capital,
        }

    def record_trade_result(self, pnl: float, exit_reason: str) -> None:
        """
        Record trade result and update risk tracking.

        Args:
            pnl: Realized PnL
            exit_reason: Why the trade was closed
        """
        # Update daily PnL
        self.daily_pnl += pnl
        self.daily_trades += 1

        # Track consecutive losses
        if pnl < 0:
            self.consecutive_losses += 1
            if exit_reason in ['stop_loss', 'liquidation']:
                self.recent_stop_losses.append(time.time())
        else:
            self.consecutive_losses = 0  # Reset on win

        # Check for consecutive stop-loss circuit breaker
        if self.circuit_breakers.enable_all:
            recent_stops = [
                ts for ts in self.recent_stop_losses
                if time.time() - ts < 3600  # Within last hour
            ]
            if len(recent_stops) >= self.circuit_breakers.consecutive_stop_loss_limit:
                self._pause_trading(
                    f"{len(recent_stops)} stop-losses in 1 hour",
                    minutes=self.circuit_breakers.consecutive_stop_loss_pause_minutes
                )

        self.logger.info(
            f"Trade result: PnL ${pnl:+.2f} ({exit_reason}) | "
            f"Daily: ${self.daily_pnl:+.2f} | "
            f"Consecutive losses: {self.consecutive_losses}"
        )

    def update_equity(self, equity: float) -> None:
        """Update equity and track peak."""
        if equity > self.peak_equity:
            self.peak_equity = equity

    def check_circuit_breakers(
        self,
        spread_bps: Optional[float] = None,
        atr_ratio: Optional[float] = None,
        volume_ratio: Optional[float] = None,
        funding_rate: Optional[float] = None,
        api_error_rate: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Check if any circuit breakers should trigger.

        Returns:
            (should_pause, reason)
        """
        if not self.circuit_breakers.enable_all:
            return False, ""

        # Spread anomaly
        if spread_bps and spread_bps > self.circuit_breakers.spread_anomaly_bps:
            return True, f"Spread anomaly: {spread_bps:.2f} bps"

        # Volatility spike
        if atr_ratio and atr_ratio > self.circuit_breakers.volatility_spike_multiplier:
            return True, f"Volatility spike: ATR {atr_ratio:.2f}x normal"

        # Volume collapse
        if volume_ratio and volume_ratio < self.circuit_breakers.volume_collapse_multiplier:
            return True, f"Volume collapse: {volume_ratio:.2%} of normal"

        # Funding rate shock
        if funding_rate and abs(funding_rate) > self.circuit_breakers.funding_rate_shock_threshold:
            return True, f"Funding rate shock: {funding_rate:.4f}"

        # API instability
        if api_error_rate and api_error_rate > self.circuit_breakers.api_error_rate_threshold:
            return True, f"API instability: {api_error_rate:.1%} error rate"

        return False, ""

    def _pause_trading(self, reason: str, until_tomorrow: bool = False, minutes: Optional[int] = None) -> None:
        """Pause trading temporarily or until manual intervention."""
        self.trading_paused = True
        self.pause_reason = reason

        if until_tomorrow:
            # Pause until next day (UTC)
            tomorrow = datetime.utcnow().date() + timedelta(days=1)
            self.pause_until = datetime.combine(tomorrow, datetime.min.time())
        elif minutes:
            self.pause_until = datetime.utcnow() + timedelta(minutes=minutes)
        else:
            self.pause_until = None  # Requires manual intervention

        self.logger.critical(f"🛑 TRADING PAUSED: {reason}")
        if self.pause_until:
            self.logger.critical(f"   Will resume at: {self.pause_until}")

    def _check_daily_reset(self) -> None:
        """Reset daily counters at midnight UTC."""
        today = datetime.utcnow().date()
        if today > self.last_reset_date:
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.last_reset_date = today
            self.logger.info(f"Daily counters reset for {today}")

    def get_status(self, current_equity: float, open_positions: int) -> Dict:
        """Get current risk status."""
        drawdown_pct = ((self.peak_equity - current_equity) / self.peak_equity) * 100 if self.peak_equity > 0 else 0

        return {
            'trading_enabled': not self.trading_paused,
            'pause_reason': self.pause_reason if self.trading_paused else None,
            'daily_trades': self.daily_trades,
            'daily_trades_remaining': max(0, self.max_trades_per_day - self.daily_trades),
            'daily_pnl': self.daily_pnl,
            'daily_pnl_pct': (self.daily_pnl / current_equity) * 100 if current_equity > 0 else 0,
            'daily_loss_limit_pct': self.max_daily_loss_pct,
            'drawdown_pct': drawdown_pct,
            'max_drawdown_pct': self.max_drawdown_pct,
            'consecutive_losses': self.consecutive_losses,
            'open_positions': open_positions,
            'max_positions': self.max_concurrent_positions,
        }


if __name__ == "__main__":
    # Test risk manager
    from ..utils.config import load_config
    from ..utils.logger import setup_logger

    config = load_config("config/bb_mean_reversion.yaml")
    logger = setup_logger("test", console_format="text")

    risk_mgr = RiskManager(config, logger)

    print("✓ Risk manager initialized")
    print(f"  Max position size: {risk_mgr.max_position_size_pct}%")
    print(f"  Max leverage: {risk_mgr.max_leverage}x")
    print(f"  Daily loss limit: {risk_mgr.max_daily_loss_pct}%")

    # Test validation
    from ..strategies.bb_mean_reversion import Signal

    signal = Signal(
        timestamp=int(time.time() * 1000),
        symbol="BTCUSDT",
        side="LONG",
        entry_price=50000.0,
        confidence=0.8,
        indicators={},
        reason="Test signal"
    )

    valid, reason, params = risk_mgr.validate_trade(signal, 50.0, [], 50000.0)
    print(f"\n✓ Trade validation: {valid}")
    if valid:
        print(f"  Size: {params['size']:.4f} BTC")
        print(f"  Leverage: {params['leverage']}x")
        print(f"  Stop: ${params['stop_price']:.2f}")

    print("\n✅ Risk manager test complete!")

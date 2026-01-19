"""
Bollinger Band Mean Reversion Strategy.

Replicates the user's proven manual trading method:
- Entry: Price touches outer Bollinger Band (2 std dev) on 15m timeframe
- Direction: Counter to the touch (upper band = SHORT, lower band = LONG)
- Exit: Multi-level take-profits (5%, 10%, 25%, 50%+) with trailing stop
- Stop: 20-30% of position value (≈10-15% of account at 20x leverage)
- Filters: Volume, spread, volatility
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from .indicators import (
    bollinger_bands,
    atr,
    percent_b,
    bb_width,
    volume_sma,
    is_volume_spike
)


@dataclass
class Signal:
    """Trading signal."""
    timestamp: int
    symbol: str
    side: str  # LONG or SHORT
    entry_price: float
    confidence: float  # 0.0 - 1.0
    indicators: Dict[str, float]
    reason: str


class BBMeanReversionStrategy:
    """
    Bollinger Band Mean Reversion Strategy.

    This is the user's PROVEN method automated.
    """

    def __init__(self, config):
        """
        Initialize strategy.

        Args:
            config: Configuration object with strategy parameters
        """
        self.config = config
        self.params = config.strategy.params

        # Bollinger Band settings
        self.bb_period = self.params.bb_period
        self.bb_std = self.params.bb_std
        self.bb_touch_threshold = self.params.bb_touch_threshold

        # Volume filter
        self.volume_filter_multiplier = self.params.volume_filter_multiplier
        self.require_volume_spike = self.params.require_volume_spike
        self.volume_spike_multiplier = self.params.volume_spike_multiplier

        # ATR for volatility filter
        self.atr_period = self.params.atr_period
        self.max_atr_multiplier = self.params.max_atr_multiplier

        # Spread filter
        self.max_spread_bps = self.params.max_spread_bps

    def generate_signal(
        self,
        df: pd.DataFrame,
        current_price: float,
        orderbook: Optional[Dict] = None
    ) -> Optional[Signal]:
        """
        Generate trading signal based on Bollinger Band mean reversion.

        Args:
            df: DataFrame with OHLCV data (columns: timestamp, open, high, low, close, volume)
            current_price: Current market price
            orderbook: Optional orderbook data for spread check

        Returns:
            Signal object if conditions met, None otherwise
        """
        if len(df) < max(self.bb_period, self.atr_period) + 1:
            return None  # Not enough data

        # Calculate indicators
        df = df.copy()
        upper, middle, lower = bollinger_bands(
            df['close'],
            period=self.bb_period,
            std_dev=self.bb_std
        )
        df['bb_upper'] = upper
        df['bb_middle'] = middle
        df['bb_lower'] = lower

        # ATR for volatility check
        df['atr'] = atr(df['high'], df['low'], df['close'], period=self.atr_period)

        # %B indicator (position within bands)
        df['percent_b'] = percent_b(df['close'], upper, lower)

        # BB Width (volatility measure)
        df['bb_width'] = bb_width(upper, lower, middle)

        # Volume analysis
        df['volume_avg'] = volume_sma(df['volume'], period=20)
        df['volume_spike'] = is_volume_spike(
            df['volume'],
            multiplier=self.volume_spike_multiplier,
            period=20
        )

        # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # === PRE-FLIGHT CHECKS ===

        # 1. Volume filter: Require minimum volume
        if latest['volume'] < latest['volume_avg'] * self.volume_filter_multiplier:
            return None  # Insufficient volume

        # 2. Volatility spike check (circuit breaker)
        atr_avg = df['atr'].iloc[-20:].mean()
        if latest['atr'] > atr_avg * self.max_atr_multiplier:
            return None  # Volatility too high

        # 3. Spread check (if orderbook provided)
        if orderbook:
            spread_bps = self._calculate_spread_bps(orderbook)
            if spread_bps > self.max_spread_bps:
                return None  # Spread too wide

        # === SIGNAL GENERATION ===

        signal_side = None
        confidence = 0.0
        reason = ""

        # LONG signal: Price touches or breaks below lower BB
        if current_price <= latest['bb_lower'] * (2 - self.bb_touch_threshold):
            # Price is at or below lower band (mean reversion opportunity)
            signal_side = "LONG"

            # Calculate confidence based on:
            # - How far below the band (more = higher confidence)
            # - Volume spike (confirmation)
            # - BB width (wider = more stretched = higher reversion potential)

            distance_below = (latest['bb_lower'] - current_price) / latest['bb_lower']
            confidence = min(0.5 + distance_below * 100, 1.0)  # Base confidence

            if latest['volume_spike']:
                confidence = min(confidence + 0.2, 1.0)  # Volume confirmation

            if latest['bb_width'] > df['bb_width'].iloc[-50:].mean() * 1.2:
                confidence = min(confidence + 0.1, 1.0)  # High volatility = more reversion potential

            reason = f"Price touched lower BB (${latest['bb_lower']:.2f}), expecting mean reversion"

        # SHORT signal: Price touches or breaks above upper BB
        elif current_price >= latest['bb_upper'] * self.bb_touch_threshold:
            # Price is at or above upper band (mean reversion opportunity)
            signal_side = "SHORT"

            # Calculate confidence
            distance_above = (current_price - latest['bb_upper']) / latest['bb_upper']
            confidence = min(0.5 + distance_above * 100, 1.0)

            if latest['volume_spike']:
                confidence = min(confidence + 0.2, 1.0)

            if latest['bb_width'] > df['bb_width'].iloc[-50:].mean() * 1.2:
                confidence = min(confidence + 0.1, 1.0)

            reason = f"Price touched upper BB (${latest['bb_upper']:.2f}), expecting mean reversion"

        # No signal if not touching bands
        if signal_side is None:
            return None

        # === ADDITIONAL FILTERS ===

        # Volume spike requirement (if enabled)
        if self.require_volume_spike and not latest['volume_spike']:
            return None  # Require volume confirmation

        # Confidence threshold
        if confidence < 0.5:
            return None  # Signal not strong enough

        # Create signal
        signal = Signal(
            timestamp=int(latest['timestamp']),
            symbol=self.config.market.symbol,
            side=signal_side,
            entry_price=current_price,
            confidence=confidence,
            indicators={
                'bb_upper': latest['bb_upper'],
                'bb_middle': latest['bb_middle'],
                'bb_lower': latest['bb_lower'],
                'percent_b': latest['percent_b'],
                'bb_width': latest['bb_width'],
                'atr': latest['atr'],
                'volume': latest['volume'],
                'volume_avg': latest['volume_avg'],
                'volume_spike': bool(latest['volume_spike']),
            },
            reason=reason
        )

        return signal

    def calculate_stop_loss(self, entry_price: float, side: str, leverage: int) -> float:
        """
        Calculate stop-loss price.

        User's method: Exit if down 20-30% of position value
        At 20x leverage, 25% position loss = 1.25% price move

        Args:
            entry_price: Entry price
            side: LONG or SHORT
            leverage: Position leverage

        Returns:
            Stop-loss price
        """
        # Position loss target: 25% (configurable via config.risk.stop_loss_pct)
        position_loss_pct = self.config.risk.stop_loss_pct / 100  # 0.25

        # Convert to price move percentage
        price_move_pct = position_loss_pct / leverage

        if side == "LONG":
            # Stop below entry
            stop_price = entry_price * (1 - price_move_pct)
        else:  # SHORT
            # Stop above entry
            stop_price = entry_price * (1 + price_move_pct)

        return stop_price

    def calculate_take_profit_levels(
        self,
        entry_price: float,
        side: str,
        atr_value: float
    ) -> List[Dict[str, float]]:
        """
        Calculate multi-level take-profit targets.

        User's method: Adaptive 5-100% targets based on volatility

        Args:
            entry_price: Entry price
            side: LONG or SHORT
            atr_value: Current ATR value

        Returns:
            List of take-profit levels: [{'pct': 5.0, 'price': 50250, 'size_pct': 25}, ...]
        """
        tp_levels = []

        for level in self.config.profit_targets.levels:
            target_pct = level['pct'] / 100  # Convert to decimal
            size_pct = level['size_pct']

            if side == "LONG":
                # Take profit above entry
                tp_price = entry_price * (1 + target_pct)
            else:  # SHORT
                # Take profit below entry
                tp_price = entry_price * (1 - target_pct)

            tp_levels.append({
                'pct': level['pct'],
                'price': tp_price,
                'size_pct': size_pct
            })

        return tp_levels

    def _calculate_spread_bps(self, orderbook: Dict) -> float:
        """Calculate bid-ask spread in basis points."""
        if not orderbook or not orderbook.get('bids') or not orderbook.get('asks'):
            return 0.0

        best_bid = float(orderbook['bids'][0][0])
        best_ask = float(orderbook['asks'][0][0])

        spread_bps = ((best_ask - best_bid) / best_bid) * 10000
        return spread_bps

    def should_close_position(
        self,
        position: Dict,
        current_price: float,
        df: pd.DataFrame,
        elapsed_minutes: int
    ) -> Tuple[bool, str]:
        """
        Determine if position should be closed (other than stop/target hit).

        Args:
            position: Position data
            current_price: Current market price
            df: Recent candle data
            elapsed_minutes: Minutes since position opened

        Returns:
            (should_close, reason)
        """
        # Time-based exit: Close if position stagnant for too long
        max_duration = self.config.risk.max_position_duration_minutes
        if elapsed_minutes >= max_duration:
            return True, "time_stop"

        # Opposite band touch: If we're LONG and price hits upper band, close
        # (Mean reversion complete)
        if len(df) >= self.bb_period:
            upper, middle, lower = bollinger_bands(
                df['close'],
                period=self.bb_period,
                std_dev=self.bb_std
            )
            latest_upper = upper.iloc[-1]
            latest_lower = lower.iloc[-1]
            latest_middle = middle.iloc[-1]

            if position['side'] == 'LONG':
                # Close if price reaches middle band or upper band
                if current_price >= latest_middle:
                    return True, "bb_middle_reached"
            else:  # SHORT
                # Close if price reaches middle band or lower band
                if current_price <= latest_middle:
                    return True, "bb_middle_reached"

        return False, ""


if __name__ == "__main__":
    # Test strategy
    from ..utils.config import load_config

    config = load_config("config/bb_mean_reversion.yaml")
    strategy = BBMeanReversionStrategy(config)

    # Create sample data
    dates = pd.date_range(end=datetime.now(), periods=100, freq='15T')
    np.random.seed(42)
    prices = 50000 + np.cumsum(np.random.randn(100) * 100)

    df = pd.DataFrame({
        'timestamp': [int(d.timestamp() * 1000) for d in dates],
        'open': prices,
        'high': prices + np.random.rand(100) * 50,
        'low': prices - np.random.rand(100) * 50,
        'close': prices,
        'volume': np.random.rand(100) * 100 + 50
    })

    # Generate signal
    signal = strategy.generate_signal(df, prices[-1])
    if signal:
        print(f"✓ Signal generated: {signal.side} @ ${signal.entry_price:.2f}")
        print(f"  Confidence: {signal.confidence:.2%}")
        print(f"  Reason: {signal.reason}")
    else:
        print("✓ No signal (filters not met)")

    print("Strategy test complete!")

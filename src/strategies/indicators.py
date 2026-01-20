"""
Technical indicators for trading strategies.
Implements Bollinger Bands, ATR, RSI, and other indicators.
"""

import numpy as np
import pandas as pd
from typing import Tuple


def bollinger_bands(
    prices: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands.

    Args:
        prices: Price series (typically close prices)
        period: Moving average period
        std_dev: Standard deviation multiplier

    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    middle_band = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)

    return upper_band, middle_band, lower_band


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR).

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: ATR period

    Returns:
        ATR series
    """
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Average True Range
    atr_values = tr.rolling(window=period).mean()
    return atr_values


def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).

    Args:
        prices: Price series
        period: RSI period

    Returns:
        RSI series (0-100)
    """
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    # Avoid division by zero
    rs = gain / loss.replace(0, 1e-10)  # Replace 0 with tiny number
    rsi_values = 100 - (100 / (1 + rs))

    return rsi_values


def sma(prices: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return prices.rolling(window=period).mean()


def ema(prices: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return prices.ewm(span=period, adjust=False).mean()


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Volume Weighted Average Price.

    Args:
        high, low, close: Price series
        volume: Volume series

    Returns:
        VWAP series
    """
    typical_price = (high + low + close) / 3
    return (typical_price * volume).cumsum() / volume.cumsum()


def percent_b(prices: pd.Series, upper: pd.Series, lower: pd.Series) -> pd.Series:
    """
    %B indicator - position of price within Bollinger Bands.

    Returns:
        %B values:
        - > 1.0 = above upper band
        - 0.5 = at middle band
        - < 0.0 = below lower band
    """
    # Avoid division by zero when bands converge
    band_width = upper - lower
    band_width = band_width.replace(0, 1e-10)  # Replace 0 with tiny number
    return (prices - lower) / band_width


def bb_width(upper: pd.Series, lower: pd.Series, middle: pd.Series) -> pd.Series:
    """
    Bollinger Band Width - measures volatility.

    Returns:
        BB Width as percentage
    """
    # Avoid division by zero if middle price is somehow 0
    safe_middle = middle.replace(0, 1e-10)
    return ((upper - lower) / safe_middle) * 100


def volume_sma(volume: pd.Series, period: int = 20) -> pd.Series:
    """Volume moving average."""
    return volume.rolling(window=period).mean()


def is_volume_spike(volume: pd.Series, multiplier: float = 1.5, period: int = 20) -> pd.Series:
    """
    Detect volume spikes.

    Returns:
        Boolean series: True where volume > multiplier * average
    """
    vol_avg = volume_sma(volume, period)
    return volume > (vol_avg * multiplier)

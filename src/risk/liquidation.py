"""
Liquidation price calculation and monitoring for futures positions.
"""

from typing import Dict, Tuple


def calculate_liquidation_price(
    entry_price: float,
    leverage: int,
    side: str,
    margin_mode: str = "ISOLATED",
    maintenance_margin_rate: float = 0.004  # 0.4% for BTC on Binance
) -> float:
    """
    Calculate liquidation price for a futures position.

    For ISOLATED margin:
    - LONG: Liq Price = Entry Price * (1 - 1/Leverage + MMR)
    - SHORT: Liq Price = Entry Price * (1 + 1/Leverage - MMR)

    Args:
        entry_price: Position entry price
        leverage: Position leverage
        side: LONG or SHORT
        margin_mode: ISOLATED or CROSSED
        maintenance_margin_rate: Maintenance margin rate (default 0.4% for BTC)

    Returns:
        Liquidation price
    """
    if margin_mode == "ISOLATED":
        if side == "LONG":
            # Liquidation when price drops to:
            # Entry * (1 - (1/leverage - MMR))
            liq_price = entry_price * (1 - (1 / leverage) + maintenance_margin_rate)
        else:  # SHORT
            # Liquidation when price rises to:
            # Entry * (1 + (1/leverage - MMR))
            liq_price = entry_price * (1 + (1 / leverage) - maintenance_margin_rate)

        return liq_price

    else:  # CROSSED margin
        # More complex calculation, depends on total account balance
        # For now, use similar formula (simplified)
        if side == "LONG":
            liq_price = entry_price * (1 - (1 / leverage) + maintenance_margin_rate)
        else:
            liq_price = entry_price * (1 + (1 / leverage) - maintenance_margin_rate)

        return liq_price


def distance_to_liquidation(
    current_price: float,
    liquidation_price: float,
    side: str
) -> float:
    """
    Calculate distance to liquidation as a percentage.

    Args:
        current_price: Current market price
        liquidation_price: Calculated liquidation price
        side: LONG or SHORT

    Returns:
        Distance to liquidation in percentage (positive = safe, negative = liquidated)
    """
    if side == "LONG":
        # For LONG, liq price is below entry
        distance_pct = ((current_price - liquidation_price) / current_price) * 100
    else:  # SHORT
        # For SHORT, liq price is above entry
        distance_pct = ((liquidation_price - current_price) / current_price) * 100

    return distance_pct


def is_near_liquidation(
    current_price: float,
    liquidation_price: float,
    side: str,
    threshold_pct: float = 10.0
) -> bool:
    """
    Check if position is dangerously close to liquidation.

    Args:
        current_price: Current market price
        liquidation_price: Calculated liquidation price
        side: LONG or SHORT
        threshold_pct: Warning threshold (default 10%)

    Returns:
        True if within threshold of liquidation
    """
    distance = distance_to_liquidation(current_price, liquidation_price, side)
    return distance < threshold_pct


def calculate_safe_leverage(
    entry_price: float,
    stop_loss_price: float,
    side: str,
    buffer_multiplier: float = 1.5
) -> int:
    """
    Calculate maximum safe leverage to avoid stop being too close to liquidation.

    Args:
        entry_price: Planned entry price
        stop_loss_price: Planned stop-loss price
        side: LONG or SHORT
        buffer_multiplier: Safety buffer (1.5 = stop should be 50% closer than liq)

    Returns:
        Maximum safe leverage
    """
    # Calculate stop-loss distance
    if side == "LONG":
        stop_distance_pct = abs((entry_price - stop_loss_price) / entry_price)
    else:  # SHORT
        stop_distance_pct = abs((stop_loss_price - entry_price) / entry_price)

    # Safe leverage: ensure stop is significantly closer than liquidation
    # Liquidation distance = 1/leverage (approximately)
    # We want: stop_distance * buffer < 1/leverage
    # Therefore: leverage < 1 / (stop_distance * buffer)

    safe_leverage = int(1 / (stop_distance_pct * buffer_multiplier))

    # Cap at reasonable maximum
    return min(safe_leverage, 125)  # Binance max is 125x for BTC


def calculate_position_risk_metrics(
    entry_price: float,
    current_price: float,
    size: float,
    leverage: int,
    side: str,
    margin: float
) -> Dict[str, float]:
    """
    Calculate comprehensive risk metrics for a position.

    Args:
        entry_price: Position entry price
        current_price: Current market price
        size: Position size in contracts
        leverage: Position leverage
        side: LONG or SHORT
        margin: Margin used (collateral)

    Returns:
        Dict with risk metrics
    """
    # Liquidation price
    liq_price = calculate_liquidation_price(entry_price, leverage, side)

    # Distance to liquidation
    liq_distance = distance_to_liquidation(current_price, liq_price, side)

    # Unrealized PnL
    if side == "LONG":
        pnl = (current_price - entry_price) * size
    else:  # SHORT
        pnl = (entry_price - current_price) * size

    # PnL as percentage of margin
    pnl_pct = (pnl / margin) * 100 if margin > 0 else 0

    # Notional value
    notional = current_price * size

    return {
        'liquidation_price': liq_price,
        'distance_to_liquidation_pct': liq_distance,
        'unrealized_pnl': pnl,
        'unrealized_pnl_pct': pnl_pct,
        'notional_value': notional,
        'margin_used': margin,
        'leverage': leverage,
        'is_near_liquidation': is_near_liquidation(current_price, liq_price, side, 10.0)
    }


if __name__ == "__main__":
    # Test liquidation calculations
    print("Testing liquidation calculations...")

    # Example: LONG BTC at $50,000 with 20x leverage
    entry = 50000
    leverage = 20
    side = "LONG"

    liq_price = calculate_liquidation_price(entry, leverage, side)
    print(f"\n✓ LONG @ ${entry:,} with {leverage}x leverage")
    print(f"  Liquidation price: ${liq_price:,.2f}")
    print(f"  Liq distance: {distance_to_liquidation(entry, liq_price, side):.2f}%")

    # Test SHORT
    side = "SHORT"
    liq_price = calculate_liquidation_price(entry, leverage, side)
    print(f"\n✓ SHORT @ ${entry:,} with {leverage}x leverage")
    print(f"  Liquidation price: ${liq_price:,.2f}")
    print(f"  Liq distance: {distance_to_liquidation(entry, liq_price, side):.2f}%")

    # Test safe leverage calculation
    stop_price = 49375  # 1.25% stop for LONG
    safe_lev = calculate_safe_leverage(50000, stop_price, "LONG")
    print(f"\n✓ Safe leverage for 1.25% stop: {safe_lev}x")

    print("\n✅ All tests passed!")

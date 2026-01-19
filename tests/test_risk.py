"""
Unit tests for risk management components.
"""

import pytest
from src.risk.liquidation import (
    calculate_liquidation_price,
    distance_to_liquidation,
    is_near_liquidation,
    calculate_safe_leverage
)


class TestLiquidationCalculations:
    """Test liquidation price calculations."""

    def test_long_liquidation_price(self):
        """Test LONG position liquidation price."""
        entry = 50000
        leverage = 20
        side = "LONG"

        liq_price = calculate_liquidation_price(entry, leverage, side)

        # For 20x LONG, liq should be around entry * (1 - 1/20 + MMR)
        # ≈ 50000 * (1 - 0.05 + 0.004) = 50000 * 0.954 = 47700
        assert liq_price < entry
        assert liq_price > entry * 0.90
        assert liq_price < entry * 0.96

    def test_short_liquidation_price(self):
        """Test SHORT position liquidation price."""
        entry = 50000
        leverage = 20
        side = "SHORT"

        liq_price = calculate_liquidation_price(entry, leverage, side)

        # For 20x SHORT, liq should be above entry
        assert liq_price > entry
        assert liq_price < entry * 1.10

    def test_distance_to_liquidation(self):
        """Test distance calculation."""
        liq_price = 47700
        current_price = 50000
        side = "LONG"

        distance = distance_to_liquidation(current_price, liq_price, side)

        # Should be positive (safe)
        assert distance > 0
        assert distance < 10  # Within reasonable range

    def test_is_near_liquidation(self):
        """Test liquidation proximity check."""
        # Safe position
        assert not is_near_liquidation(50000, 47500, "LONG", 10.0)

        # Near liquidation
        assert is_near_liquidation(48000, 47500, "LONG", 10.0)

    def test_safe_leverage_calculation(self):
        """Test safe leverage calculation."""
        entry = 50000
        stop = 49375  # 1.25% stop

        safe_lev = calculate_safe_leverage(entry, stop, "LONG")

        # Should recommend reasonable leverage
        assert safe_lev > 0
        assert safe_lev < 125


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

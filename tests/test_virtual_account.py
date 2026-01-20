"""
Unit tests for VirtualAccount paper trading balance tracking.
"""

import pytest
from src.paper.paper_trader import VirtualAccount


class TestVirtualAccountBalanceTracking:
    """Test that virtual account properly tracks balance and equity."""

    def test_balance_decreases_on_open_position(self):
        """Test that balance decreases by margin amount when opening position."""
        account = VirtualAccount(starting_balance=100.0)

        # Open position with $25 margin
        account.open_position(
            position_id="test_1",
            symbol="BTCUSDT",
            side="LONG",
            size=0.01,
            entry_price=50000.0,
            leverage=20,
            margin=25.0,
            liquidation_price=47500.0
        )

        # Balance should decrease by margin amount
        assert account.balance == 75.0  # 100 - 25
        assert account.margin_used == 25.0

    def test_winning_trade_pnl_calculation(self):
        """Test that a winning trade correctly updates balance."""
        account = VirtualAccount(starting_balance=100.0)

        # Open LONG position
        account.open_position(
            position_id="test_1",
            symbol="BTCUSDT",
            side="LONG",
            size=0.01,
            entry_price=50000.0,
            leverage=20,
            margin=25.0,
            liquidation_price=47500.0
        )

        assert account.balance == 75.0  # Margin locked

        # Close at profit (entry $50k, exit $51k = $10 profit on 0.01 BTC)
        # PnL = (51000 - 50000) * 0.01 = $10
        # Fees = $2 (example)
        # Net PnL = $10 - $2 = $8
        pnl = account.close_position(
            position_id="test_1",
            exit_price=51000.0,
            fees=2.0,
            funding_fees=0.0
        )

        assert pnl == 8.0  # Net profit
        assert account.balance == 108.0  # 75 + 25 (margin returned) + 8 (profit) = 108
        assert account.margin_used == 0.0

    def test_losing_trade_pnl_calculation(self):
        """Test that a losing trade correctly updates balance."""
        account = VirtualAccount(starting_balance=100.0)

        # Open LONG position
        account.open_position(
            position_id="test_1",
            symbol="BTCUSDT",
            side="LONG",
            size=0.01,
            entry_price=50000.0,
            leverage=20,
            margin=25.0,
            liquidation_price=47500.0
        )

        assert account.balance == 75.0  # Margin locked

        # Close at loss (entry $50k, exit $49k = -$10 loss on 0.01 BTC)
        # PnL = (49000 - 50000) * 0.01 = -$10
        # Fees = $2
        # Net PnL = -$10 - $2 = -$12
        pnl = account.close_position(
            position_id="test_1",
            exit_price=49000.0,
            fees=2.0,
            funding_fees=0.0
        )

        assert pnl == -12.0  # Net loss
        assert account.balance == 88.0  # 75 + 25 (margin) - 12 (loss) = 88
        assert account.margin_used == 0.0

    def test_short_position_profit(self):
        """Test SHORT position profit calculation."""
        account = VirtualAccount(starting_balance=100.0)

        # Open SHORT position
        account.open_position(
            position_id="test_1",
            symbol="BTCUSDT",
            side="SHORT",
            size=0.01,
            entry_price=50000.0,
            leverage=20,
            margin=25.0,
            liquidation_price=52500.0
        )

        assert account.balance == 75.0

        # Close SHORT at profit (entry $50k, exit $49k = $10 profit)
        # PnL = (50000 - 49000) * 0.01 = $10
        # Fees = $2
        # Net PnL = $10 - $2 = $8
        pnl = account.close_position(
            position_id="test_1",
            exit_price=49000.0,
            fees=2.0,
            funding_fees=0.0
        )

        assert pnl == 8.0
        assert account.balance == 108.0  # 75 + 25 + 8 = 108

    def test_equity_calculation_with_open_position(self):
        """Test that equity correctly includes margin and unrealized PnL."""
        account = VirtualAccount(starting_balance=100.0)

        # Open position
        account.open_position(
            position_id="test_1",
            symbol="BTCUSDT",
            side="LONG",
            size=0.01,
            entry_price=50000.0,
            leverage=20,
            margin=25.0,
            liquidation_price=47500.0
        )

        # Balance should be 75 (100 - 25 locked margin)
        assert account.balance == 75.0
        assert account.margin_used == 25.0

        # Update unrealized PnL (price went to $51k = +$10 unrealized profit)
        account.update_unrealized_pnl({"BTCUSDT": 51000.0})

        # Equity should include:
        # - Free balance: $75
        # - Locked margin: $25
        # - Unrealized profit: $10
        # Total: $110
        assert account.unrealized_pnl == 10.0
        assert account.get_equity() == 110.0

    def test_equity_with_losing_position(self):
        """Test equity calculation with an unrealized loss."""
        account = VirtualAccount(starting_balance=100.0)

        # Open position
        account.open_position(
            position_id="test_1",
            symbol="BTCUSDT",
            side="LONG",
            size=0.01,
            entry_price=50000.0,
            leverage=20,
            margin=25.0,
            liquidation_price=47500.0
        )

        # Price drops to $49k = -$10 unrealized loss
        account.update_unrealized_pnl({"BTCUSDT": 49000.0})

        # Equity should be:
        # - Free balance: $75
        # - Locked margin: $25
        # - Unrealized loss: -$10
        # Total: $90
        assert account.unrealized_pnl == -10.0
        assert account.get_equity() == 90.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

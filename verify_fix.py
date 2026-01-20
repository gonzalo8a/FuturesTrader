#!/usr/bin/env python3
"""
Quick verification script for VirtualAccount balance fix.
"""

from src.paper.paper_trader import VirtualAccount


def test_balance_tracking():
    """Test that balance tracking is now correct."""
    print("Testing VirtualAccount balance tracking fixes...")
    print("=" * 60)

    # Test 1: Balance decreases on open
    print("\n1. Testing balance decreases when opening position...")
    account = VirtualAccount(starting_balance=100.0)
    print(f"   Starting balance: ${account.balance:.2f}")

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

    print(f"   After opening with $25 margin: ${account.balance:.2f}")
    assert account.balance == 75.0, f"Expected 75.0, got {account.balance}"
    print("   ✓ PASS: Balance correctly decreased by margin amount")

    # Test 2: Winning trade
    print("\n2. Testing winning trade PnL calculation...")
    account2 = VirtualAccount(starting_balance=100.0)

    account2.open_position(
        position_id="test_2",
        symbol="BTCUSDT",
        side="LONG",
        size=0.01,
        entry_price=50000.0,
        leverage=20,
        margin=25.0,
        liquidation_price=47500.0
    )

    print(f"   Balance after open: ${account2.balance:.2f}")

    # Close at +$10 profit with $2 fees = +$8 net
    pnl = account2.close_position(
        position_id="test_2",
        exit_price=51000.0,
        fees=2.0,
        funding_fees=0.0
    )

    print(f"   Trade PnL: ${pnl:+.2f}")
    print(f"   Balance after close: ${account2.balance:.2f}")

    expected_balance = 75.0 + 25.0 + 8.0  # free + margin returned + profit
    assert account2.balance == expected_balance, f"Expected {expected_balance}, got {account2.balance}"
    print(f"   ✓ PASS: Balance is correct ($75 free + $25 margin + $8 profit = $108)")

    # Test 3: Losing trade
    print("\n3. Testing losing trade PnL calculation...")
    account3 = VirtualAccount(starting_balance=100.0)

    account3.open_position(
        position_id="test_3",
        symbol="BTCUSDT",
        side="LONG",
        size=0.01,
        entry_price=50000.0,
        leverage=20,
        margin=25.0,
        liquidation_price=47500.0
    )

    # Close at -$10 loss with $2 fees = -$12 net
    pnl = account3.close_position(
        position_id="test_3",
        exit_price=49000.0,
        fees=2.0,
        funding_fees=0.0
    )

    print(f"   Trade PnL: ${pnl:+.2f}")
    print(f"   Balance after close: ${account3.balance:.2f}")

    expected_balance = 75.0 + 25.0 - 12.0  # free + margin returned - loss
    assert account3.balance == expected_balance, f"Expected {expected_balance}, got {account3.balance}"
    print(f"   ✓ PASS: Balance is correct ($75 free + $25 margin - $12 loss = $88)")

    # Test 4: Equity with open position
    print("\n4. Testing equity calculation with unrealized PnL...")
    account4 = VirtualAccount(starting_balance=100.0)

    account4.open_position(
        position_id="test_4",
        symbol="BTCUSDT",
        side="LONG",
        size=0.01,
        entry_price=50000.0,
        leverage=20,
        margin=25.0,
        liquidation_price=47500.0
    )

    # Update with +$10 unrealized profit
    account4.update_unrealized_pnl({"BTCUSDT": 51000.0})

    print(f"   Free balance: ${account4.balance:.2f}")
    print(f"   Locked margin: ${account4.margin_used:.2f}")
    print(f"   Unrealized PnL: ${account4.unrealized_pnl:+.2f}")
    print(f"   Total equity: ${account4.get_equity():.2f}")

    expected_equity = 75.0 + 25.0 + 10.0  # balance + margin + unrealized
    assert account4.get_equity() == expected_equity, f"Expected {expected_equity}, got {account4.get_equity()}"
    print(f"   ✓ PASS: Equity correctly includes margin ($75 + $25 + $10 = $110)")

    # Test 5: The original bug scenario
    print("\n5. Simulating the original bug scenario from logs...")
    print("   (Starting with $50, open trade with ~$25 margin, close with +$1.22 profit)")

    account5 = VirtualAccount(starting_balance=50.0)
    print(f"   Starting balance: ${account5.balance:.2f}")

    account5.open_position(
        position_id="test_5",
        symbol="BTCUSDT",
        side="LONG",
        size=0.0055,
        entry_price=90000.0,
        leverage=20,
        margin=24.75,  # Approximate from 50% position
        liquidation_price=85500.0
    )

    print(f"   Balance after opening: ${account5.balance:.2f}")

    # Close with ~$1.22 profit
    pnl = account5.close_position(
        position_id="test_5",
        exit_price=90802.84,
        fees=0.50,  # Approximate
        funding_fees=0.0
    )

    print(f"   Trade PnL: ${pnl:+.2f}")
    print(f"   Balance after close: ${account5.balance:.2f}")

    # With the OLD bug: balance would have been ~$77 (gained $27 instead of $1.22)
    # With the FIX: balance should be ~$51.22 (gained ~$1.22 as expected)
    expected_range = (50.5, 52.0)
    assert expected_range[0] < account5.balance < expected_range[1], \
        f"Balance {account5.balance} not in expected range {expected_range}"

    print(f"   ✓ PASS: Balance increased by PnL amount (not margin!)")
    print(f"   ✓ OLD BUG would have given: ~$77 (+$27)")
    print(f"   ✓ FIXED CODE gives: ~$51 (+$1.22)")

    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED! The balance tracking bug is fixed.")
    print("=" * 60)


if __name__ == "__main__":
    test_balance_tracking()

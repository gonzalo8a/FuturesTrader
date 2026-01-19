#!/usr/bin/env python3
"""
FuturesTrader - Cryptocurrency Futures Day Trading Bot

Usage:
    python main.py paper --config config/bb_mean_reversion.yaml
    python main.py backtest --config config/bb_mean_reversion.yaml
    python main.py live --config config/bb_mean_reversion.yaml

Modes:
    backtest - Historical simulation
    paper    - Real-time simulation with live data
    live     - Real trading (CAUTION!)
"""

import sys
import signal
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import load_config
from src.utils.logger import init_logger, get_logger
from src.paper.paper_trader import PaperTrader


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    logger = get_logger()
    logger.info("\nReceived shutdown signal, stopping...")
    sys.exit(0)


def run_paper_mode(config):
    """Run paper trading mode."""
    logger = get_logger()
    logger.info("="*70)
    logger.info(" PAPER TRADING MODE")
    logger.info("="*70)
    logger.info(f" Symbol: {config.market.symbol}")
    logger.info(f" Timeframe: {config.market.timeframe}")
    logger.info(f" Strategy: {config.strategy.name}")
    logger.info(f" Starting Balance: ${config.paper.starting_balance}")
    logger.info(f" Max Leverage: {config.risk.max_leverage}x")
    logger.info(f" Position Size: {config.risk.max_position_size_pct}%")
    logger.info("="*70)
    logger.info("")

    trader = PaperTrader(config)

    try:
        trader.run()
    except KeyboardInterrupt:
        logger.info("\nShutdown requested...")
        trader.stop()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        trader.stop()


def run_backtest_mode(config):
    """Run backtesting mode."""
    logger = get_logger()
    logger.info("="*70)
    logger.info(" BACKTEST MODE")
    logger.info("="*70)
    logger.info(f" Symbol: {config.market.symbol}")
    logger.info(f" Timeframe: {config.market.timeframe}")
    logger.info(f" Period: {config.data.backtest_start_date} to {config.data.backtest_end_date}")
    logger.info("="*70)
    logger.info("")

    logger.warning("⚠️ Backtesting not fully implemented yet - use paper trading for now")
    logger.info("To backtest: Run paper mode and analyze the results")


def run_live_mode(config):
    """Run live trading mode."""
    logger = get_logger()

    logger.critical("="*70)
    logger.critical(" ⚠️  LIVE TRADING MODE - REAL MONEY AT RISK ⚠️")
    logger.critical("="*70)
    logger.critical("")
    logger.critical(" This mode will execute REAL trades on Binance Futures")
    logger.critical(" You can lose ALL your capital")
    logger.critical("")

    # Safety checks
    logger.critical(" SAFETY CHECKLIST:")
    logger.critical(" [ ] Have you run paper trading for 7+ days successfully?")
    logger.critical(" [ ] Have you verified stop-loss logic works correctly?")
    logger.critical(" [ ] Have you tested the kill switch?")
    logger.critical(" [ ] Is your starting capital an amount you can afford to lose?")
    logger.critical(" [ ] Have you set up API keys with ONLY Futures trading permission?")
    logger.critical(" [ ] Have you restricted API keys by IP address?")
    logger.critical(" [ ] Have you disabled withdrawals on your API keys?")
    logger.critical("")

    if config.live_safety.require_user_confirmation:
        response = input("Type 'I UNDERSTAND THE RISKS' to continue: ")
        if response != "I UNDERSTAND THE RISKS":
            logger.info("Live trading cancelled")
            return

    logger.critical("")
    logger.critical("🚨 LIVE TRADING NOT FULLY IMPLEMENTED YET 🚨")
    logger.critical("This is for your safety. Complete implementation requires:")
    logger.critical("1. More extensive testing of paper trading")
    logger.critical("2. Live order execution module")
    logger.critical("3. Position reconciliation with exchange")
    logger.critical("4. Additional safety checks")
    logger.critical("")
    logger.critical("Please use PAPER TRADING mode for now.")
    logger.critical("")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="FuturesTrader - Automated Cryptocurrency Futures Day Trading Bot"
    )

    parser.add_argument(
        'mode',
        choices=['backtest', 'paper', 'live'],
        help='Trading mode (backtest, paper, or live)'
    )

    parser.add_argument(
        '--config',
        '-c',
        type=str,
        default='config/bb_mean_reversion.yaml',
        help='Path to configuration file (default: config/bb_mean_reversion.yaml)'
    )

    parser.add_argument(
        '--version',
        '-v',
        action='version',
        version='FuturesTrader 1.0.0'
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
        config.mode = args.mode  # Override mode from command line
    except FileNotFoundError:
        print(f"❌ Config file not found: {args.config}")
        print(f"\nExample: python main.py paper --config config/bb_mean_reversion.yaml")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        sys.exit(1)

    # Initialize logger
    logger = init_logger(config)

    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run appropriate mode
    if args.mode == 'paper':
        run_paper_mode(config)
    elif args.mode == 'backtest':
        run_backtest_mode(config)
    elif args.mode == 'live':
        run_live_mode(config)


if __name__ == '__main__':
    main()

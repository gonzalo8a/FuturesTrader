"""
Configuration loader for FuturesTrader bot.
Loads settings from YAML files and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class ExchangeConfig:
    """Exchange configuration."""
    name: str = "binance_futures"
    margin_mode: str = "ISOLATED"
    testnet: bool = False


@dataclass
class MarketConfig:
    """Market configuration."""
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    contract_type: str = "perpetual"


@dataclass
class StrategyParams:
    """Strategy-specific parameters."""
    bb_period: int = 20
    bb_std: float = 2.0
    volume_filter_multiplier: float = 0.1
    min_spread_bps: float = 0.5
    max_spread_bps: float = 50.0
    atr_period: int = 14
    max_atr_multiplier: float = 3.0
    bb_touch_threshold: float = 0.998
    require_volume_spike: bool = True
    volume_spike_multiplier: float = 1.5


@dataclass
class StrategyConfig:
    """Strategy configuration."""
    name: str = "bb_mean_reversion"
    params: StrategyParams = field(default_factory=StrategyParams)


@dataclass
class RiskConfig:
    """Risk management configuration."""
    starting_capital: float = 50.0
    max_position_size_pct: float = 50.0
    max_leverage: int = 20
    hard_leverage_cap: int = 25
    max_concurrent_positions: int = 1
    max_trades_per_day: int = 20
    stop_loss_pct: float = 25.0
    liquidation_buffer_pct: float = 70.0
    max_daily_loss_pct: float = 30.0
    max_drawdown_pct: float = 50.0
    max_consecutive_losses: int = 4
    consecutive_loss_size_reduction: float = 0.5
    max_position_duration_minutes: int = 240


@dataclass
class ExecutionConfig:
    """Execution configuration."""
    order_type: str = "LIMIT"
    limit_order_timeout_sec: int = 30
    retry_on_timeout: bool = True
    max_retries: int = 1
    post_only: bool = False
    reduce_only_exits: bool = True
    limit_order_offset_bps: float = 2.0


@dataclass
class ProfitTargetLevel:
    """Single profit target level."""
    pct: float
    size_pct: float


@dataclass
class ProfitTargetsConfig:
    """Profit targets configuration."""
    mode: str = "adaptive"
    levels: list = field(default_factory=lambda: [
        {"pct": 5.0, "size_pct": 25},
        {"pct": 10.0, "size_pct": 25},
        {"pct": 25.0, "size_pct": 25},
        {"pct": 50.0, "size_pct": 25},
    ])
    enable_trailing: bool = True
    trailing_stop_activation: float = 20.0
    trailing_stop_distance_pct: float = 10.0


@dataclass
class SessionConfig:
    """Trading session configuration."""
    trading_hours: str = "00:00-23:00"
    force_close_time: str = "23:00"
    timezone: str = "UTC"
    trade_weekends: bool = True


@dataclass
class DataConfig:
    """Data storage and collection configuration."""
    db_path: str = "data/futures_trader.db"
    log_path: str = "logs/"
    backtest_start_date: str = "2025-10-19"
    backtest_end_date: str = "2026-01-19"
    orderbook_levels: int = 10
    orderbook_update_interval_sec: int = 5
    enable_websocket: bool = True
    websocket_streams: list = field(default_factory=lambda: ["kline", "ticker", "aggTrade"])


@dataclass
class PaperConfig:
    """Paper trading configuration."""
    starting_balance: float = 50.0
    simulate_slippage: bool = True
    slippage_bps: float = 2.0
    simulate_partial_fills: bool = True
    partial_fill_probability: float = 0.1
    simulate_funding: bool = True
    funding_interval_hours: int = 8
    simulate_latency: bool = True
    latency_ms_mean: float = 50.0
    latency_ms_std: float = 20.0


@dataclass
class FeesConfig:
    """Fee configuration."""
    maker: float = 0.02
    taker: float = 0.04
    funding_rate_default: float = 0.01


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"
    max_file_size_mb: int = 100
    backup_count: int = 5
    console_level: str = "INFO"
    console_format: str = "text"


@dataclass
class AlertsConfig:
    """Alerts configuration."""
    enabled: bool = True
    channels: list = field(default_factory=lambda: ["console"])
    on_trade: bool = False
    on_stop_loss: bool = True
    on_take_profit: bool = False
    on_kill_switch: bool = True
    on_daily_loss_limit: bool = True
    on_max_drawdown: bool = True
    on_error: bool = True


@dataclass
class CircuitBreakersConfig:
    """Circuit breaker configuration."""
    enable_all: bool = True
    spread_anomaly_bps: float = 50.0
    volatility_spike_multiplier: float = 3.0
    volatility_spike_pause_minutes: int = 60
    volume_collapse_multiplier: float = 0.1
    api_error_rate_threshold: float = 0.2
    api_error_window_minutes: int = 5
    funding_rate_shock_threshold: float = 0.5
    consecutive_stop_loss_limit: int = 3
    consecutive_stop_loss_pause_minutes: int = 60


@dataclass
class KillSwitchConfig:
    """Kill switch configuration."""
    enable: bool = True
    on_liquidation: bool = True
    on_max_drawdown: bool = True
    on_daily_loss_exceeded: bool = True
    on_repeated_errors: bool = True
    emergency_file: str = ".KILL_SWITCH"
    close_all_positions: bool = True
    cancel_all_orders: bool = True


@dataclass
class LiveSafetyConfig:
    """Live trading safety configuration."""
    require_paper_trading_days: int = 7
    require_paper_positive_pnl: bool = False
    require_max_drawdown_check: bool = True
    require_user_confirmation: bool = True
    start_with_reduced_size: bool = False
    reduced_size_multiplier: float = 0.5
    reduced_size_trades: int = 10


@dataclass
class Config:
    """Main configuration object."""
    mode: str = "paper"
    exchange: ExchangeConfig = field(default_factory=ExchangeConfig)
    market: MarketConfig = field(default_factory=MarketConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    profit_targets: ProfitTargetsConfig = field(default_factory=ProfitTargetsConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    data: DataConfig = field(default_factory=DataConfig)
    paper: PaperConfig = field(default_factory=PaperConfig)
    fees: FeesConfig = field(default_factory=FeesConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    alerts: AlertsConfig = field(default_factory=AlertsConfig)
    circuit_breakers: CircuitBreakersConfig = field(default_factory=CircuitBreakersConfig)
    kill_switch: KillSwitchConfig = field(default_factory=KillSwitchConfig)
    live_safety: LiveSafetyConfig = field(default_factory=LiveSafetyConfig)

    # API credentials (from environment)
    api_key: str = ""
    api_secret: str = ""


def load_config(config_path: str) -> Config:
    """
    Load configuration from YAML file and environment variables.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Config object

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is invalid
    """
    # Load environment variables from .env file
    load_dotenv()

    # Load YAML configuration
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_file, 'r') as f:
        yaml_config = yaml.safe_load(f)

    # Create Config object
    config = Config()

    # Top-level settings
    config.mode = yaml_config.get('mode', 'paper')

    # Exchange
    if 'exchange' in yaml_config:
        exc = yaml_config['exchange']
        config.exchange = ExchangeConfig(
            name=exc.get('name', 'binance_futures'),
            margin_mode=exc.get('margin_mode', 'ISOLATED'),
            testnet=exc.get('testnet', False)
        )

    # Market
    if 'market' in yaml_config:
        mkt = yaml_config['market']
        config.market = MarketConfig(
            symbol=mkt.get('symbol', 'BTCUSDT'),
            timeframe=mkt.get('timeframe', '15m'),
            contract_type=mkt.get('contract_type', 'perpetual')
        )

    # Strategy
    if 'strategy' in yaml_config:
        strat = yaml_config['strategy']
        params_dict = strat.get('params', {})
        config.strategy = StrategyConfig(
            name=strat.get('name', 'bb_mean_reversion'),
            params=StrategyParams(**params_dict)
        )

    # Risk
    if 'risk' in yaml_config:
        config.risk = RiskConfig(**yaml_config['risk'])

    # Execution
    if 'execution' in yaml_config:
        config.execution = ExecutionConfig(**yaml_config['execution'])

    # Profit targets
    if 'profit_targets' in yaml_config:
        pt = yaml_config['profit_targets']
        config.profit_targets = ProfitTargetsConfig(**pt)

    # Session
    if 'session' in yaml_config:
        config.session = SessionConfig(**yaml_config['session'])

    # Data
    if 'data' in yaml_config:
        config.data = DataConfig(**yaml_config['data'])

    # Paper
    if 'paper' in yaml_config:
        config.paper = PaperConfig(**yaml_config['paper'])

    # Fees
    if 'fees' in yaml_config:
        config.fees = FeesConfig(**yaml_config['fees'])

    # Logging
    if 'logging' in yaml_config:
        config.logging = LoggingConfig(**yaml_config['logging'])

    # Alerts
    if 'alerts' in yaml_config:
        config.alerts = AlertsConfig(**yaml_config['alerts'])

    # Circuit breakers
    if 'circuit_breakers' in yaml_config:
        config.circuit_breakers = CircuitBreakersConfig(**yaml_config['circuit_breakers'])

    # Kill switch
    if 'kill_switch' in yaml_config:
        config.kill_switch = KillSwitchConfig(**yaml_config['kill_switch'])

    # Live safety
    if 'live_safety' in yaml_config:
        config.live_safety = LiveSafetyConfig(**yaml_config['live_safety'])

    # Load API credentials from environment
    testnet = config.exchange.testnet or os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'

    if testnet:
        config.api_key = os.getenv('BINANCE_TESTNET_API_KEY', '')
        config.api_secret = os.getenv('BINANCE_TESTNET_API_SECRET', '')
    else:
        config.api_key = os.getenv('BINANCE_API_KEY', '')
        config.api_secret = os.getenv('BINANCE_API_SECRET', '')

    # Validate critical settings
    _validate_config(config)

    return config


def _validate_config(config: Config) -> None:
    """
    Validate configuration for critical issues.

    Raises:
        ValueError: If configuration is invalid
    """
    # Mode validation
    if config.mode not in ['backtest', 'paper', 'live']:
        raise ValueError(f"Invalid mode: {config.mode}. Must be 'backtest', 'paper', or 'live'")

    # API key validation (required for paper and live)
    if config.mode in ['paper', 'live']:
        if not config.api_key or not config.api_secret:
            raise ValueError(
                f"API keys required for {config.mode} mode. "
                "Set BINANCE_API_KEY and BINANCE_API_SECRET in .env file"
            )

    # Risk validation
    if config.risk.max_leverage > config.risk.hard_leverage_cap:
        raise ValueError(
            f"max_leverage ({config.risk.max_leverage}) cannot exceed "
            f"hard_leverage_cap ({config.risk.hard_leverage_cap})"
        )

    if config.risk.max_position_size_pct <= 0 or config.risk.max_position_size_pct > 100:
        raise ValueError(f"max_position_size_pct must be between 0 and 100")

    if config.risk.starting_capital <= 0:
        raise ValueError(f"starting_capital must be positive")

    # Margin mode validation
    if config.exchange.margin_mode not in ['ISOLATED', 'CROSSED']:
        raise ValueError(f"margin_mode must be 'ISOLATED' or 'CROSSED'")

    # Timeframe validation
    valid_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h']
    if config.market.timeframe not in valid_timeframes:
        raise ValueError(f"timeframe must be one of {valid_timeframes}")

    # Warning for aggressive settings
    if config.risk.max_leverage >= 10:
        print(f"⚠️  WARNING: High leverage ({config.risk.max_leverage}x) - risk of liquidation!")

    if config.risk.max_position_size_pct >= 50:
        print(f"⚠️  WARNING: Large position size ({config.risk.max_position_size_pct}%) - high risk!")


def save_config(config: Config, output_path: str) -> None:
    """
    Save configuration to YAML file.

    Args:
        config: Config object
        output_path: Path to save YAML file
    """
    # Convert config to dict (simplified)
    config_dict = {
        'mode': config.mode,
        'exchange': {
            'name': config.exchange.name,
            'margin_mode': config.exchange.margin_mode,
            'testnet': config.exchange.testnet,
        },
        'market': {
            'symbol': config.market.symbol,
            'timeframe': config.market.timeframe,
            'contract_type': config.market.contract_type,
        },
        # Add other sections as needed
    }

    with open(output_path, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)


if __name__ == "__main__":
    # Test config loading
    import sys
    if len(sys.argv) > 1:
        config = load_config(sys.argv[1])
        print(f"✓ Loaded config: {config.mode} mode")
        print(f"  Symbol: {config.market.symbol}")
        print(f"  Timeframe: {config.market.timeframe}")
        print(f"  Strategy: {config.strategy.name}")
        print(f"  Max Leverage: {config.risk.max_leverage}x")
        print(f"  Position Size: {config.risk.max_position_size_pct}%")
        print(f"  Stop Loss: {config.risk.stop_loss_pct}%")
    else:
        print("Usage: python config.py <config_file.yaml>")

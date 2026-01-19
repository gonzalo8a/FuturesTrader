"""
Structured logging utility for FuturesTrader bot.
Supports both JSON (for machine parsing) and text (for humans) formats.
"""

import logging
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler


class JSONFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, 'extra'):
            log_data.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Format log records with colors for console output."""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: str,
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: str = "json",
    console_level: str = "INFO",
    console_format: str = "text",
    max_file_size_mb: int = 100,
    backup_count: int = 5,
) -> logging.Logger:
    """
    Setup logger with file and console handlers.

    Args:
        name: Logger name
        log_level: File log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (if None, no file logging)
        log_format: File format ('json' or 'text')
        console_level: Console log level
        console_format: Console format ('json' or 'text')
        max_file_size_mb: Max log file size before rotation
        backup_count: Number of backup log files to keep

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Capture everything, filter at handler level
    logger.handlers = []  # Clear existing handlers

    # File handler (JSON or text)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))

        if log_format == 'json':
            file_handler.setFormatter(JSONFormatter())
        else:
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)

        logger.addHandler(file_handler)

    # Console handler (colored text or JSON)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_level.upper()))

    if console_format == 'json':
        console_handler.setFormatter(JSONFormatter())
    else:
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

    logger.addHandler(console_handler)

    return logger


def log_trade(
    logger: logging.Logger,
    action: str,
    symbol: str,
    side: str,
    size: float,
    price: float,
    **kwargs
) -> None:
    """
    Log a trade event with structured data.

    Args:
        logger: Logger instance
        action: Trade action (OPEN, CLOSE, CANCEL)
        symbol: Trading symbol
        side: LONG or SHORT
        size: Position size
        price: Execution price
        **kwargs: Additional trade data
    """
    trade_data = {
        'event': 'trade',
        'action': action,
        'symbol': symbol,
        'side': side,
        'size': size,
        'price': price,
        **kwargs
    }

    message = f"{action} {side} {size} {symbol} @ {price}"
    logger.info(message, extra=trade_data)


def log_risk_event(
    logger: logging.Logger,
    event_type: str,
    severity: str,
    message: str,
    **kwargs
) -> None:
    """
    Log a risk management event.

    Args:
        logger: Logger instance
        event_type: Type of risk event
        severity: INFO, WARNING, ERROR, CRITICAL
        message: Event description
        **kwargs: Additional event data
    """
    risk_data = {
        'event': 'risk',
        'type': event_type,
        **kwargs
    }

    log_func = getattr(logger, severity.lower())
    log_func(message, extra=risk_data)


def log_kill_switch(
    logger: logging.Logger,
    trigger: str,
    reason: str,
    **kwargs
) -> None:
    """
    Log a kill switch activation.

    Args:
        logger: Logger instance
        trigger: What triggered the kill switch
        reason: Why it was triggered
        **kwargs: Additional context
    """
    kill_switch_data = {
        'event': 'kill_switch',
        'trigger': trigger,
        'reason': reason,
        **kwargs
    }

    logger.critical(f"🛑 KILL SWITCH ACTIVATED: {trigger} - {reason}", extra=kill_switch_data)


def log_performance(
    logger: logging.Logger,
    equity: float,
    pnl: float,
    pnl_pct: float,
    drawdown: float,
    **kwargs
) -> None:
    """
    Log performance metrics.

    Args:
        logger: Logger instance
        equity: Current equity
        pnl: Realized PnL
        pnl_pct: PnL percentage
        drawdown: Current drawdown from peak
        **kwargs: Additional metrics
    """
    perf_data = {
        'event': 'performance',
        'equity': equity,
        'pnl': pnl,
        'pnl_pct': pnl_pct,
        'drawdown': drawdown,
        **kwargs
    }

    message = f"Equity: ${equity:.2f} | PnL: {pnl:+.2f} ({pnl_pct:+.2f}%) | DD: {drawdown:.2f}%"
    logger.info(message, extra=perf_data)


# Global logger instance (initialized by main)
_global_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Get the global logger instance."""
    global _global_logger
    if _global_logger is None:
        # Fallback logger if not initialized
        _global_logger = setup_logger("FuturesTrader")
    return _global_logger


def init_logger(config: Any) -> logging.Logger:
    """
    Initialize global logger from config.

    Args:
        config: Config object

    Returns:
        Logger instance
    """
    global _global_logger

    # Create log directory
    log_dir = Path(config.data.log_path)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{config.mode}_{timestamp}.log"

    _global_logger = setup_logger(
        name="FuturesTrader",
        log_level=config.logging.level,
        log_file=str(log_file),
        log_format=config.logging.format,
        console_level=config.logging.console_level,
        console_format=config.logging.console_format,
        max_file_size_mb=config.logging.max_file_size_mb,
        backup_count=config.logging.backup_count,
    )

    _global_logger.info(f"Logger initialized: {log_file}")
    _global_logger.info(f"Mode: {config.mode}")
    _global_logger.info(f"Symbol: {config.market.symbol}")
    _global_logger.info(f"Strategy: {config.strategy.name}")

    return _global_logger


if __name__ == "__main__":
    # Test logger
    logger = setup_logger("test", console_format="text")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

    log_trade(logger, "OPEN", "BTCUSDT", "LONG", 0.01, 50000.0, leverage=20)
    log_risk_event(logger, "MAX_LEVERAGE", "WARNING", "Leverage limit reached", leverage=20)
    log_performance(logger, 55.50, 5.50, 11.0, 2.5, trades=5, win_rate=0.8)

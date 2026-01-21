"""
SQLite database for FuturesTrader.
Stores candles, orderbook, trades, positions, and performance data.
"""

import sqlite3
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager


class Database:
    """SQLite database manager."""

    def __init__(self, db_path: str):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dicts
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Candles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS candles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    quote_volume REAL NOT NULL,
                    trades INTEGER,
                    UNIQUE(symbol, timeframe, timestamp)
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_candles_symbol_timeframe_timestamp
                ON candles(symbol, timeframe, timestamp DESC)
            """)

            # Orderbook snapshots
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orderbook_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    bids TEXT NOT NULL,
                    asks TEXT NOT NULL,
                    spread_bps REAL
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_orderbook_timestamp
                ON orderbook_snapshots(timestamp DESC)
            """)

            # Funding rates
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS funding_rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    funding_rate REAL NOT NULL,
                    UNIQUE(symbol, timestamp)
                )
            """)

            # Trades
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode TEXT NOT NULL,
                    trade_id TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_time INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    size REAL NOT NULL,
                    leverage REAL NOT NULL,
                    notional REAL NOT NULL,
                    exit_time INTEGER,
                    exit_price REAL,
                    pnl REAL,
                    pnl_pct REAL,
                    fees REAL,
                    funding_fees REAL,
                    exit_reason TEXT,
                    max_profit REAL,
                    max_drawdown REAL,
                    metadata TEXT
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_mode_entry_time
                ON trades(mode, entry_time DESC)
            """)

            # Positions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode TEXT NOT NULL,
                    position_id TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    size REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    leverage REAL NOT NULL,
                    liquidation_price REAL,
                    unrealized_pnl REAL,
                    status TEXT NOT NULL,
                    opened_at INTEGER NOT NULL,
                    closed_at INTEGER,
                    updated_at INTEGER NOT NULL
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_positions_status
                ON positions(mode, status, opened_at DESC)
            """)

            # Account snapshots
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    current_price REAL,
                    equity REAL NOT NULL,
                    balance REAL NOT NULL,
                    unrealized_pnl REAL NOT NULL,
                    margin_used REAL NOT NULL,
                    margin_available REAL NOT NULL,
                    open_positions INTEGER NOT NULL,
                    daily_pnl REAL,
                    drawdown_pct REAL
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_mode_timestamp
                ON account_snapshots(mode, timestamp DESC)
            """)

            # Events
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    metadata TEXT
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON events(timestamp DESC)
            """)

    def insert_candle(
        self,
        symbol: str,
        timeframe: str,
        timestamp: int,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        quote_volume: float,
        trades: Optional[int] = None
    ) -> None:
        """Insert or update a candle."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO candles
                (symbol, timeframe, timestamp, open, high, low, close, volume, quote_volume, trades)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, timeframe, timestamp, open_, high, low, close, volume, quote_volume, trades))

    def get_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve candles."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM candles WHERE symbol = ? AND timeframe = ?"
            params = [symbol, timeframe]

            if start_time is not None:
                query += " AND timestamp >= ?"
                params.append(start_time)

            if end_time is not None:
                query += " AND timestamp <= ?"
                params.append(end_time)

            query += " ORDER BY timestamp ASC"

            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def insert_orderbook_snapshot(
        self,
        symbol: str,
        timestamp: int,
        bids: List[List[float]],
        asks: List[List[float]]
    ) -> None:
        """Insert orderbook snapshot."""
        # Calculate spread
        best_bid = bids[0][0] if bids else 0
        best_ask = asks[0][0] if asks else 0
        spread_bps = ((best_ask - best_bid) / best_bid * 10000) if best_bid > 0 else 0

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO orderbook_snapshots (symbol, timestamp, bids, asks, spread_bps)
                VALUES (?, ?, ?, ?, ?)
            """, (symbol, timestamp, json.dumps(bids), json.dumps(asks), spread_bps))

    def insert_funding_rate(self, symbol: str, timestamp: int, funding_rate: float) -> None:
        """Insert or update funding rate."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO funding_rates (symbol, timestamp, funding_rate)
                VALUES (?, ?, ?)
            """, (symbol, timestamp, funding_rate))

    def insert_trade(self, trade_data: Dict[str, Any]) -> None:
        """Insert a trade record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades
                (mode, trade_id, symbol, strategy, side, entry_time, entry_price, size, leverage,
                 notional, exit_time, exit_price, pnl, pnl_pct, fees, funding_fees, exit_reason,
                 max_profit, max_drawdown, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data['mode'],
                trade_data['trade_id'],
                trade_data['symbol'],
                trade_data['strategy'],
                trade_data['side'],
                trade_data['entry_time'],
                trade_data['entry_price'],
                trade_data['size'],
                trade_data['leverage'],
                trade_data['notional'],
                trade_data.get('exit_time'),
                trade_data.get('exit_price'),
                trade_data.get('pnl'),
                trade_data.get('pnl_pct'),
                trade_data.get('fees'),
                trade_data.get('funding_fees'),
                trade_data.get('exit_reason'),
                trade_data.get('max_profit'),
                trade_data.get('max_drawdown'),
                json.dumps(trade_data.get('metadata', {}))
            ))

    def update_trade(self, trade_id: str, updates: Dict[str, Any]) -> None:
        """Update a trade record."""
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [trade_id]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE trades SET {set_clause} WHERE trade_id = ?
            """, values)

    def get_trades(
        self,
        mode: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve trades."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM trades WHERE mode = ?"
            params = [mode]

            if start_time is not None:
                query += " AND entry_time >= ?"
                params.append(start_time)

            if end_time is not None:
                query += " AND entry_time <= ?"
                params.append(end_time)

            if status == 'open':
                query += " AND exit_time IS NULL"
            elif status == 'closed':
                query += " AND exit_time IS NOT NULL"

            query += " ORDER BY entry_time DESC"

            cursor.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]

            # Parse metadata JSON
            for row in rows:
                if row['metadata']:
                    row['metadata'] = json.loads(row['metadata'])

            return rows

    def insert_position(self, position_data: Dict[str, Any]) -> None:
        """Insert or update position."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO positions
                (mode, position_id, symbol, side, size, entry_price, leverage, liquidation_price,
                 unrealized_pnl, status, opened_at, closed_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position_data['mode'],
                position_data['position_id'],
                position_data['symbol'],
                position_data['side'],
                position_data['size'],
                position_data['entry_price'],
                position_data['leverage'],
                position_data.get('liquidation_price'),
                position_data.get('unrealized_pnl', 0),
                position_data['status'],
                position_data['opened_at'],
                position_data.get('closed_at'),
                position_data['updated_at']
            ))

    def get_open_positions(self, mode: str) -> List[Dict[str, Any]]:
        """Get all open positions."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM positions WHERE mode = ? AND status = 'OPEN'
                ORDER BY opened_at DESC
            """, (mode,))
            return [dict(row) for row in cursor.fetchall()]

    def insert_account_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """Insert account snapshot."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO account_snapshots
                (mode, timestamp, current_price, equity, balance, unrealized_pnl, margin_used, margin_available,
                 open_positions, daily_pnl, drawdown_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot['mode'],
                snapshot['timestamp'],
                snapshot.get('current_price'),
                snapshot['equity'],
                snapshot['balance'],
                snapshot['unrealized_pnl'],
                snapshot['margin_used'],
                snapshot['margin_available'],
                snapshot['open_positions'],
                snapshot.get('daily_pnl'),
                snapshot.get('drawdown_pct')
            ))

    def get_latest_snapshot(self, mode: str) -> Optional[Dict[str, Any]]:
        """Get most recent account snapshot."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM account_snapshots WHERE mode = ?
                ORDER BY timestamp DESC LIMIT 1
            """, (mode,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def insert_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Insert an event."""
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events (timestamp, event_type, severity, message, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (timestamp, event_type, severity, message, json.dumps(metadata or {})))

    def get_recent_events(self, limit: int = 100, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent events."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM events"
            params = []

            if severity:
                query += " WHERE severity = ?"
                params.append(severity)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]

            # Parse metadata
            for row in rows:
                if row['metadata']:
                    row['metadata'] = json.loads(row['metadata'])

            return rows


if __name__ == "__main__":
    # Test database
    db = Database("data/test.db")
    print("✓ Database created successfully")

    # Test candle insert
    now = int(datetime.utcnow().timestamp() * 1000)
    db.insert_candle("BTCUSDT", "15m", now, 50000, 50100, 49900, 50050, 100.5, 5000000, 1000)
    print("✓ Candle inserted")

    # Test candle retrieval
    candles = db.get_candles("BTCUSDT", "15m", limit=10)
    print(f"✓ Retrieved {len(candles)} candles")

    print("All tests passed!")

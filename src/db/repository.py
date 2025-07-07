"""
Repository Pattern for Database Layer - Enhanced
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import sqlite3
import pandas as pd
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class BaseRepository(ABC):
    """Abstract base repository interface"""

    @abstractmethod
    def add(self, item: Dict[str, Any]) -> str:
        """Add new item and return ID"""
        pass

    @abstractmethod
    def get(self, id_: str) -> Optional[Dict[str, Any]]:
        """Get item by ID"""
        pass

    @abstractmethod
    def list(self, **filters) -> List[Dict[str, Any]]:
        """List items with optional filters"""
        pass

    @abstractmethod
    def update(self, id_: str, updates: Dict[str, Any]) -> bool:
        """Update item by ID"""
        pass

    @abstractmethod
    def delete(self, id_: str) -> bool:
        """Delete item by ID"""
        pass


class SQLiteRepository(BaseRepository):
    """SQLite implementation of repository pattern"""

    def __init__(self, db_path: str, table_name: str):
        self.db_path = db_path
        self.table_name = table_name
        self._init_db()

    def _init_db(self):
        """Initialize database and create tables if needed"""
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")

    def _execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute query and return results as list of dicts"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def _execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute update/insert/delete query and return affected rows"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount


class StockDataRepository(SQLiteRepository):
    """Repository for stock market data"""

    def __init__(self, db_path: str):
        super().__init__(db_path, "stock_data")
        self._create_tables()

    def _create_tables(self):
        """Create stock data tables"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS stock_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date DATE NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            vwap REAL,
            trade_count INTEGER,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date)
        )
        """

        create_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_stock_data_symbol_date 
        ON stock_data(symbol, date)
        """

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(create_table_sql)
            conn.execute(create_index_sql)
            conn.commit()

    def add(self, item: Dict[str, Any]) -> str:
        """Add stock data record"""
        query = """
        INSERT OR REPLACE INTO stock_data 
        (symbol, date, open, high, low, close, volume, vwap, trade_count, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            item["symbol"],
            item["date"],
            item.get("open"),
            item.get("high"),
            item.get("low"),
            item.get("close"),
            item.get("volume"),
            item.get("vwap"),
            item.get("trade_count"),
            item.get("last_updated", datetime.now()),
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return str(cursor.lastrowid)

    def add_or_update(self, item: Dict[str, Any]) -> str:
        """Add or update stock data record"""
        return self.add(item)  # Uses INSERT OR REPLACE

    def get(self, id_: str) -> Optional[Dict[str, Any]]:
        """Get stock data by ID"""
        query = "SELECT * FROM stock_data WHERE id = ?"
        results = self._execute_query(query, (id_,))
        return results[0] if results else None

    def list(self, **filters) -> List[Dict[str, Any]]:
        """List stock data with filters"""
        query = "SELECT * FROM stock_data WHERE 1=1"
        params = []

        if "symbol" in filters:
            query += " AND symbol = ?"
            params.append(filters["symbol"])

        if "start_date" in filters:
            query += " AND date >= ?"
            params.append(filters["start_date"])

        if "end_date" in filters:
            query += " AND date <= ?"
            params.append(filters["end_date"])

        query += " ORDER BY date DESC"

        if "limit" in filters:
            query += f" LIMIT {filters['limit']}"

        return self._execute_query(query, tuple(params))

    def update(self, id_: str, updates: Dict[str, Any]) -> bool:
        """Update stock data by ID"""
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        query = f"UPDATE stock_data SET {set_clause} WHERE id = ?"

        params = list(updates.values()) + [id_]
        affected_rows = self._execute_update(query, tuple(params))
        return affected_rows > 0

    def delete(self, id_: str) -> bool:
        """Delete stock data by ID"""
        query = "DELETE FROM stock_data WHERE id = ?"
        affected_rows = self._execute_update(query, (id_,))
        return affected_rows > 0

    def get_data_by_symbol_and_date_range(
        self, symbol: str, start_date: str = None, end_date: str = None
    ) -> pd.DataFrame:
        """Get stock data as DataFrame"""
        filters = {"symbol": symbol}
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date

        data = self.list(**filters)
        return pd.DataFrame(data)

    def get_latest_date(self, symbol: str) -> Optional[date]:
        """Get latest date for a symbol"""
        query = "SELECT MAX(date) as latest_date FROM stock_data WHERE symbol = ?"
        results = self._execute_query(query, (symbol,))

        if results and results[0]["latest_date"]:
            return datetime.strptime(results[0]["latest_date"], "%Y-%m-%d").date()
        return None


class SymbolRepository(SQLiteRepository):
    """Repository for symbol metadata"""

    def __init__(self, db_path: str):
        super().__init__(db_path, "symbols")
        self._create_tables()

    def _create_tables(self):
        """Create symbols table"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            name TEXT,
            exchange TEXT,
            asset_class TEXT,
            tradable BOOLEAN DEFAULT 1,
            marginable BOOLEAN DEFAULT 0,
            shortable BOOLEAN DEFAULT 0,
            easy_to_borrow BOOLEAN DEFAULT 0,
            fractionable BOOLEAN DEFAULT 0,
            active BOOLEAN DEFAULT 1,
            metadata TEXT,  -- JSON string for additional metadata
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        create_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_symbols_symbol 
        ON symbols(symbol)
        """

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(create_table_sql)
            conn.execute(create_index_sql)
            conn.commit()

    def add(self, item: Dict[str, Any]) -> str:
        """Add symbol record"""
        query = """
        INSERT OR REPLACE INTO symbols 
        (symbol, name, exchange, asset_class, tradable, marginable, shortable, 
         easy_to_borrow, fractionable, active, metadata, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            item["symbol"],
            item.get("name"),
            item.get("exchange"),
            item.get("asset_class"),
            item.get("tradable", True),
            item.get("marginable", False),
            item.get("shortable", False),
            item.get("easy_to_borrow", False),
            item.get("fractionable", False),
            item.get("active", True),
            item.get("metadata"),
            item.get("last_updated", datetime.now()),
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return str(cursor.lastrowid)

    def add_or_update(self, item: Dict[str, Any]) -> str:
        """Add or update symbol record"""
        return self.add(item)  # Uses INSERT OR REPLACE

    def get(self, id_: str) -> Optional[Dict[str, Any]]:
        """Get symbol by ID"""
        query = "SELECT * FROM symbols WHERE id = ?"
        results = self._execute_query(query, (id_,))
        return results[0] if results else None

    def get_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol data by symbol name"""
        query = "SELECT * FROM symbols WHERE symbol = ?"
        results = self._execute_query(query, (symbol,))
        return results[0] if results else None

    def list(self, **filters) -> List[Dict[str, Any]]:
        """List symbols with filters"""
        query = "SELECT * FROM symbols WHERE 1=1"
        params = []

        if "active" in filters:
            query += " AND active = ?"
            params.append(filters["active"])

        if "exchange" in filters:
            query += " AND exchange = ?"
            params.append(filters["exchange"])

        if "tradable" in filters:
            query += " AND tradable = ?"
            params.append(filters["tradable"])

        query += " ORDER BY symbol"

        if "limit" in filters:
            query += f" LIMIT {filters['limit']}"

        return self._execute_query(query, tuple(params))

    def update(self, id_: str, updates: Dict[str, Any]) -> bool:
        """Update symbol by ID"""
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        query = f"UPDATE symbols SET {set_clause} WHERE id = ?"

        params = list(updates.values()) + [id_]
        affected_rows = self._execute_update(query, tuple(params))
        return affected_rows > 0

    def delete(self, id_: str) -> bool:
        """Delete symbol by ID"""
        query = "DELETE FROM symbols WHERE id = ?"
        affected_rows = self._execute_update(query, (id_,))
        return affected_rows > 0

    def get_active_symbols(self, limit: int = None) -> List[str]:
        """Get list of active symbol names"""
        query = "SELECT symbol FROM symbols WHERE active = 1 AND tradable = 1 ORDER BY symbol"
        if limit:
            query += f" LIMIT {limit}"

        results = self._execute_query(query)
        return [row["symbol"] for row in results]

    def update_metadata(self, symbol: str, metadata: Dict[str, Any]):
        """Update metadata for a symbol"""
        import json

        query = "UPDATE symbols SET metadata = ?, last_updated = ? WHERE symbol = ?"
        params = (json.dumps(metadata), datetime.now(), symbol)
        self._execute_update(query, params)


class SignalRepository(SQLiteRepository):
    """Repository for trading signals"""

    def __init__(self, db_path: str):
        super().__init__(db_path, "signals")
        self._create_tables()

    def _create_tables(self):
        """Create signals table - compatible with SQLModel models"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,  -- 'buy', 'sell'
            confidence_score REAL NOT NULL,
            strength REAL NOT NULL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            price_at_signal REAL NOT NULL,
            strategy_count INTEGER NOT NULL,
            contributing_strategies TEXT,  -- JSON string
            status TEXT DEFAULT 'pending'  -- 'pending', 'executed', 'rejected', 'expired'
        )
        """

        create_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_signals_symbol_generated_at 
        ON signals(symbol, generated_at)
        """

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(create_table_sql)
            conn.execute(create_index_sql)
            conn.commit()

    def add(self, item: Dict[str, Any]) -> str:
        """Add signal record"""
        query = """
        INSERT INTO signals 
        (symbol, direction, confidence_score, strength, generated_at, price_at_signal, strategy_count, contributing_strategies, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            item["symbol"],
            item["direction"],
            item["confidence_score"],
            item["strength"],
            item.get("generated_at", datetime.now()),
            item["price_at_signal"],
            item["strategy_count"],
            item.get("contributing_strategies"),
            item.get("status", "pending"),
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return str(cursor.lastrowid)

    def get(self, id_: str) -> Optional[Dict[str, Any]]:
        """Get signal by ID"""
        query = "SELECT * FROM signals WHERE id = ?"
        results = self._execute_query(query, (id_,))
        return results[0] if results else None

    def list(self, **filters) -> List[Dict[str, Any]]:
        """List signals with filters"""
        query = "SELECT * FROM signals WHERE 1=1"
        params = []

        if "symbol" in filters:
            query += " AND symbol = ?"
            params.append(filters["symbol"])

        if "direction" in filters:
            query += " AND direction = ?"
            params.append(filters["direction"])

        if "status" in filters:
            query += " AND status = ?"
            params.append(filters["status"])

        if "strategy_count" in filters:
            query += " AND strategy_count >= ?"
            params.append(filters["strategy_count"])

        query += " ORDER BY generated_at DESC"

        if "limit" in filters:
            query += f" LIMIT {filters['limit']}"

        return self._execute_query(query, tuple(params))

    def update(self, id_: str, updates: Dict[str, Any]) -> bool:
        """Update signal by ID"""
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        query = f"UPDATE signals SET {set_clause} WHERE id = ?"

        params = list(updates.values()) + [id_]
        affected_rows = self._execute_update(query, tuple(params))
        return affected_rows > 0

    def delete(self, id_: str) -> bool:
        """Delete signal by ID"""
        query = "DELETE FROM signals WHERE id = ?"
        affected_rows = self._execute_update(query, (id_,))
        return affected_rows > 0

    def mark_processed(self, signal_ids: List[str]) -> bool:
        """Mark signals as processed"""
        if not signal_ids:
            return True

        placeholders = ", ".join(["?" for _ in signal_ids])
        query = f"UPDATE signals SET processed = 1 WHERE id IN ({placeholders})"
        affected_rows = self._execute_update(query, tuple(signal_ids))
        return affected_rows > 0

    def get_unprocessed_signals(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get unprocessed signals"""
        filters = {"processed": False}
        if symbol:
            filters["symbol"] = symbol
        return self.list(**filters)

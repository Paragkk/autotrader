#!/usr/bin/env python3
"""
Database Migration Script: Add Multi-Broker Support
Migrates existing single-broker database to support multiple brokers
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backup_database(db_path: str) -> str:
    """Create backup of existing database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"

    try:
        import shutil

        shutil.copy2(db_path, backup_path)
        logger.info(f"✅ Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"❌ Failed to backup database: {e}")
        raise


def migrate_database(db_path: str):
    """Migrate database to support multiple brokers"""
    logger.info("Starting multi-broker database migration...")

    # Create backup first
    backup_path = backup_database(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Create broker_accounts table
        logger.info("Creating broker_accounts table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS broker_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                broker_name VARCHAR(20) NOT NULL UNIQUE,
                account_id VARCHAR(50) NOT NULL,
                buying_power REAL DEFAULT 0.0,
                cash REAL DEFAULT 0.0,
                portfolio_value REAL DEFAULT 0.0,
                equity REAL DEFAULT 0.0,
                day_trading_power REAL,
                pattern_day_trader BOOLEAN DEFAULT FALSE,
                account_status VARCHAR(20) DEFAULT 'active',
                paper_trading BOOLEAN DEFAULT TRUE,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Check if broker_name column exists in orders table
        cursor.execute("PRAGMA table_info(orders)")
        columns = [column[1] for column in cursor.fetchall()]

        if "broker_name" not in columns:
            logger.info("Adding broker_name column to orders table...")
            cursor.execute("ALTER TABLE orders ADD COLUMN broker_name VARCHAR(20)")

            # Update existing orders with default broker
            cursor.execute(
                "UPDATE orders SET broker_name = 'alpaca' WHERE broker_name IS NULL"
            )

            # Create index for better performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_orders_broker_name ON orders(broker_name)"
            )

        # 3. Check if broker_name column exists in positions table
        cursor.execute("PRAGMA table_info(positions)")
        columns = [column[1] for column in cursor.fetchall()]

        if "broker_name" not in columns:
            logger.info("Adding broker_name column to positions table...")
            cursor.execute("ALTER TABLE positions ADD COLUMN broker_name VARCHAR(20)")

            # Update existing positions with default broker
            cursor.execute(
                "UPDATE positions SET broker_name = 'alpaca' WHERE broker_name IS NULL"
            )

            # Create index for better performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_positions_broker_name ON positions(broker_name)"
            )

        # 4. Check if broker_name column exists in trade_logs table
        cursor.execute("PRAGMA table_info(trade_logs)")
        columns = [column[1] for column in cursor.fetchall()]

        if "broker_name" not in columns:
            logger.info("Adding broker_name column to trade_logs table...")
            cursor.execute("ALTER TABLE trade_logs ADD COLUMN broker_name VARCHAR(20)")

            # Update existing trade logs with default broker
            cursor.execute(
                "UPDATE trade_logs SET broker_name = 'alpaca' WHERE broker_name IS NULL"
            )

            # Create index for better performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_trade_logs_broker_name ON trade_logs(broker_name)"
            )

        # 5. Remove unique constraint from broker_order_id if it exists and recreate with composite key
        logger.info("Updating broker_order_id constraints...")

        # Check current schema
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='orders'"
        )
        schema = cursor.fetchone()[0]

        if "UNIQUE" in schema and "broker_order_id" in schema:
            logger.info("Recreating orders table with composite unique constraint...")

            # Create new table with correct schema
            cursor.execute("""
                CREATE TABLE orders_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    broker_name VARCHAR(20) NOT NULL,
                    broker_order_id VARCHAR(50),
                    symbol VARCHAR(10) NOT NULL,
                    side VARCHAR(10) NOT NULL,
                    quantity REAL NOT NULL,
                    order_type VARCHAR(20) NOT NULL,
                    price REAL,
                    stop_price REAL,
                    time_in_force VARCHAR(10) DEFAULT 'day',
                    status VARCHAR(20) NOT NULL,
                    filled_quantity REAL DEFAULT 0.0,
                    filled_price REAL,
                    commission REAL,
                    signal_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    submitted_at DATETIME,
                    filled_at DATETIME,
                    cancelled_at DATETIME,
                    UNIQUE(broker_name, broker_order_id),
                    FOREIGN KEY (signal_id) REFERENCES signals (id)
                )
            """)

            # Copy data
            cursor.execute("""
                INSERT INTO orders_new 
                SELECT * FROM orders
            """)

            # Drop old table and rename new one
            cursor.execute("DROP TABLE orders")
            cursor.execute("ALTER TABLE orders_new RENAME TO orders")

            # Recreate indexes
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_orders_broker_name ON orders(broker_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol)"
            )

        # 6. Insert default broker account if it doesn't exist
        cursor.execute(
            "SELECT COUNT(*) FROM broker_accounts WHERE broker_name = 'alpaca'"
        )
        if cursor.fetchone()[0] == 0:
            logger.info("Creating default Alpaca broker account record...")
            cursor.execute("""
                INSERT INTO broker_accounts 
                (broker_name, account_id, paper_trading) 
                VALUES ('alpaca', 'default_account', TRUE)
            """)

        # 7. Create additional indexes for performance
        logger.info("Creating performance indexes...")

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_positions_broker_symbol ON positions(broker_name, symbol)",
            "CREATE INDEX IF NOT EXISTS idx_orders_broker_status ON orders(broker_name, status)",
            "CREATE INDEX IF NOT EXISTS idx_trade_logs_broker_symbol ON trade_logs(broker_name, symbol)",
        ]

        for index_sql in indexes:
            cursor.execute(index_sql)

        # Commit all changes
        conn.commit()
        logger.info("✅ Database migration completed successfully!")

        # Run validation
        validate_migration(cursor)

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        conn.rollback()

        # Restore backup
        logger.info("Restoring database from backup...")
        conn.close()
        import shutil

        shutil.copy2(backup_path, db_path)
        raise

    finally:
        conn.close()


def validate_migration(cursor):
    """Validate that migration was successful"""
    logger.info("Validating migration...")

    # Check that broker_accounts table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='broker_accounts'"
    )
    if not cursor.fetchone():
        raise Exception("broker_accounts table not created")

    # Check that broker_name columns exist
    for table in ["orders", "positions", "trade_logs"]:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [column[1] for column in cursor.fetchall()]
        if "broker_name" not in columns:
            raise Exception(f"broker_name column not added to {table} table")

    # Check that default broker account exists
    cursor.execute("SELECT COUNT(*) FROM broker_accounts WHERE broker_name = 'alpaca'")
    if cursor.fetchone()[0] == 0:
        raise Exception("Default broker account not created")

    logger.info("✅ Migration validation passed!")


def main():
    """Main migration function"""
    # Default database path
    db_path = "data/trading.db"

    # Allow custom path via command line
    if len(sys.argv) > 1:
        db_path = sys.argv[1]

    if not os.path.exists(db_path):
        logger.error(f"❌ Database file not found: {db_path}")
        return 1

    try:
        migrate_database(db_path)
        logger.info("🎉 Multi-broker migration completed successfully!")

        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print("✅ Added broker_accounts table")
        print("✅ Added broker_name columns to orders, positions, trade_logs")
        print("✅ Created performance indexes")
        print("✅ Updated constraints for multi-broker support")
        print("✅ Created default Alpaca broker account")
        print("\n📋 Next Steps:")
        print("1. Update your configuration to use the new multi-broker format")
        print("2. Test broker connections")
        print("3. Verify that all existing data is accessible")
        print("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

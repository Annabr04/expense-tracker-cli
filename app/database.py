import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_ENV_VAR = "EXPENSE_TRACKER_DB"
DEFAULT_DB_PATH = Path(__file__).parent.parent / "expenses.db"

# Default on-disk location (repo-root expenses.db). Runtime callers must use
# get_db_path() so the EXPENSE_TRACKER_DB override is honored.
DB_PATH = DEFAULT_DB_PATH

_CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount_cents INTEGER NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        date TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
"""


def get_db_path() -> Path:
    env = os.environ.get(DB_ENV_VAR)
    if env:
        return Path(env)
    return DEFAULT_DB_PATH


def get_connection():
    path = get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _column_names(conn) -> set[str]:
    return {row["name"] for row in conn.execute("PRAGMA table_info(expenses)")}


def _migrate_legacy_real_amount(conn) -> None:
    """Convert a pre-Decimal schema (amount REAL, dollars) to amount_cents INTEGER.

    Existing dollar values are multiplied by 100 and rounded with SQLite's
    ROUND() (half away from zero). Back up expenses.db before upgrading a
    database you care about.
    """
    conn.execute("ALTER TABLE expenses RENAME TO expenses_legacy_dollars")
    conn.execute(_CREATE_TABLE)
    conn.execute(
        """
        INSERT INTO expenses (id, amount_cents, category, description, date, created_at)
        SELECT id,
               CAST(ROUND(amount * 100) AS INTEGER),
               category,
               description,
               date,
               created_at
        FROM expenses_legacy_dollars
        """
    )
    conn.execute("DROP TABLE expenses_legacy_dollars")


def migrate_if_needed(conn) -> None:
    cols = _column_names(conn)
    if not cols:
        return
    if "amount_cents" in cols and "amount" not in cols:
        return
    if "amount" in cols:
        _migrate_legacy_real_amount(conn)
        return
    raise RuntimeError(
        "expenses table exists but has no amount or amount_cents column; "
        "refusing to guess a migration"
    )


def init_db():
    with get_db() as conn:
        # If a legacy table already exists, this is a no-op; migrate_if_needed
        # then rewrites it. Fresh databases are created with amount_cents.
        conn.execute(_CREATE_TABLE)
        migrate_if_needed(conn)

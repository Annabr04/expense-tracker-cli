import csv
import hashlib
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from app.database import DEFAULT_DB_PATH, get_db_path
from app.main import app

runner = CliRunner()


def invoke(*args: str):
    return runner.invoke(app, list(args))


def add(amount: str, category: str = "food", **opts):
    args = ["add", amount, "--category", category]
    if "description" in opts:
        args += ["--description", opts["description"]]
    if "date" in opts:
        args += ["--date", opts["date"]]
    return invoke(*args)


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------

def test_db_path_uses_tmp_path_fixture(isolated_db):
    assert get_db_path() == isolated_db
    assert get_db_path() != DEFAULT_DB_PATH
    result = add("1.00")
    assert result.exit_code == 0
    assert isolated_db.exists()


def test_suite_does_not_touch_default_expenses_db(isolated_db, tmp_path):
    """A sentinel at the production path must be unchanged after CLI use."""
    sentinel = DEFAULT_DB_PATH
    payload = b"SENTINEL USER DATA DO NOT DELETE\n" + b"qa-isolation\n"
    existed = sentinel.exists()
    original = sentinel.read_bytes() if existed else None
    sentinel.write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest()
    try:
        assert add("15.50", description="Lunch").exit_code == 0
        assert invoke("list").exit_code == 0
        export_path = tmp_path / "out.csv"
        assert invoke("export", "--file", str(export_path)).exit_code == 0
        assert sentinel.exists()
        assert hashlib.sha256(sentinel.read_bytes()).hexdigest() == expected
        assert sentinel.read_bytes() == payload
        assert isolated_db.exists()
    finally:
        if existed and original is not None:
            sentinel.write_bytes(original)
        elif sentinel.exists():
            sentinel.unlink()


# ---------------------------------------------------------------------------
# Happy paths (existing coverage, kept)
# ---------------------------------------------------------------------------

def test_add_expense():
    result = add("15.50", description="Lunch")
    assert result.exit_code == 0
    assert "Added expense" in result.stdout
    assert "$15.50" in result.stdout


def test_add_rejects_non_positive_amount():
    result = invoke("add", "0", "--category", "food")
    assert result.exit_code == 1
    assert "Amount must be greater than 0" in result.stdout

    # Options first, then -- so -5 is parsed as the amount argument
    result = invoke("add", "--category", "food", "--", "-5")
    assert result.exit_code == 1
    assert "Amount must be greater than 0" in result.stdout


def test_list_expenses():
    add("10", "food")
    add("25", "transport")
    result = invoke("list")
    assert result.exit_code == 0
    assert "food" in result.stdout
    assert "transport" in result.stdout


def test_summary():
    add("20", "food")
    add("30", "food")
    add("15", "transport")
    result = invoke("summary")
    assert result.exit_code == 0
    assert "food" in result.stdout
    assert "Grand Total" in result.stdout
    assert "$65.00" in result.stdout


def test_delete_expense():
    add("9.99", "other")
    result = invoke("delete", "1")
    assert result.exit_code == 0
    assert "Deleted expense #1" in result.stdout


def test_export(tmp_path):
    add("5", "shopping")
    dest = tmp_path / "test_export.csv"
    result = invoke("export", "--file", str(dest))
    assert result.exit_code == 0
    assert "Exported" in result.stdout
    assert dest.exists()
    rows = list(csv.reader(dest.read_text(encoding="utf-8").splitlines()))
    assert rows[0] == ["id", "date", "category", "amount", "description"]
    assert rows[1][2] == "shopping"
    assert rows[1][3] == "5.00"


# ---------------------------------------------------------------------------
# Empty paths
# ---------------------------------------------------------------------------

def test_list_empty_db():
    result = invoke("list")
    assert result.exit_code == 0
    assert "No expenses found." in result.stdout


def test_summary_empty_db():
    result = invoke("summary")
    assert result.exit_code == 0
    assert "No expenses found" in result.stdout


def test_export_empty_db(tmp_path):
    dest = tmp_path / "empty.csv"
    result = invoke("export", "--file", str(dest))
    assert result.exit_code == 0
    assert "No expenses to export." in result.stdout
    assert not dest.exists()


def test_categories():
    result = invoke("categories")
    assert result.exit_code == 0
    assert "food" in result.stdout
    assert "transport" in result.stdout


# ---------------------------------------------------------------------------
# Failure paths / invalid input
# ---------------------------------------------------------------------------

def test_add_rejects_invalid_amount():
    result = invoke("add", "abc", "--category", "food")
    assert result.exit_code == 1
    assert "Amount must be a valid number" in result.stdout


def test_add_rejects_more_than_two_decimal_places():
    result = add("0.001")
    assert result.exit_code == 1
    assert "at most 2 decimal places" in result.stdout


def test_add_rejects_invalid_date():
    result = add("12.50", date="11-22-2026")
    assert result.exit_code == 1
    assert "Invalid date format" in result.stdout

    result = add("12.50", date="2026-13-01")
    assert result.exit_code == 1
    assert "Invalid date format" in result.stdout


def test_delete_missing_id():
    result = invoke("delete", "1")
    assert result.exit_code == 1
    assert "No expense found with ID 1" in result.stdout


def test_export_missing_parent_directory(tmp_path):
    dest = tmp_path / "missing-dir" / "out.csv"
    add("5", "shopping")
    result = invoke("export", "--file", str(dest))
    assert result.exit_code == 1
    assert "Directory does not exist" in result.stdout
    assert not dest.exists()


def test_list_category_filter():
    add("4.75", "food", description="Coffee", date="2026-09-15")
    add("45.00", "transport", description="Gas", date="2026-09-16")
    result = invoke("list", "--category", "FOOD")
    assert result.exit_code == 0
    assert "food" in result.stdout
    assert "Coffee" in result.stdout
    assert "transport" not in result.stdout

    result = invoke("list", "--category", "nope")
    assert result.exit_code == 0
    assert "No expenses found." in result.stdout


# ---------------------------------------------------------------------------
# --limit and --month validation
# ---------------------------------------------------------------------------

def test_list_limit_rejects_zero_and_negative():
    add("10", "food")
    result = invoke("list", "--limit", "0")
    assert result.exit_code == 1
    assert "--limit must be a positive integer" in result.stdout

    # Use --limit=-1 so Click does not treat -1 as an option name.
    result = invoke("list", "--limit=-1")
    assert result.exit_code == 1
    assert "--limit must be a positive integer" in result.stdout


def test_list_limit_positive_is_honored():
    add("10", "food", date="2026-01-01")
    add("20", "food", date="2026-01-02")
    result = invoke("list", "--limit", "1")
    assert result.exit_code == 0
    assert "Showing 1 expense" in result.stdout


def test_summary_month_validation():
    add("10", "food", date="2026-09-15")
    add("5", "food", date="2026-10-01")

    result = invoke("summary", "--month", "2026-09")
    assert result.exit_code == 0
    assert "$10.00" in result.stdout
    assert "2026-09" in result.stdout

    for bad in ("foo", "2026-13", "2026-9", "2026", "2026-00", "2026-09-15"):
        result = invoke("summary", "--month", bad)
        assert result.exit_code == 1, bad
        assert "Invalid month" in result.stdout

    result = invoke("summary", "--month", "2026-10")
    assert result.exit_code == 0
    assert "$5.00" in result.stdout


# ---------------------------------------------------------------------------
# Decimal / no float drift
# ---------------------------------------------------------------------------

def test_decimal_sum_has_no_float_drift():
    """0.1 + 0.2 is 0.30000000000000004 in binary float; must be $0.30 here."""
    add("0.10", "food", date="2026-03-01")
    add("0.20", "food", date="2026-03-01")
    result = invoke("summary", "--month", "2026-03")
    assert result.exit_code == 0
    assert "$0.30" in result.stdout
    assert "0.30000000000000004" not in result.stdout

    result = invoke("list")
    assert result.exit_code == 0
    assert "Subtotal: $0.30" in result.stdout


def test_legacy_real_amounts_are_migrated(isolated_db, monkeypatch):
    # Rebuild a pre-Decimal database at the already-isolated path.
    isolated_db.unlink(missing_ok=True)
    conn = sqlite3.connect(isolated_db)
    conn.execute(
        """
        CREATE TABLE expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.executemany(
        "INSERT INTO expenses (amount, category, description, date) VALUES (?, ?, ?, ?)",
        [
            (10.10, "food", "legacy-a", "2026-01-01"),
            (0.20, "food", "legacy-b", "2026-01-01"),
        ],
    )
    conn.commit()
    conn.close()

    result = invoke("summary", "--month", "2026-01")
    assert result.exit_code == 0
    assert "$10.30" in result.stdout

    conn = sqlite3.connect(isolated_db)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(expenses)")}
    assert "amount_cents" in cols
    assert "amount" not in cols
    cents = [row[0] for row in conn.execute("SELECT amount_cents FROM expenses ORDER BY id")]
    conn.close()
    assert cents == [1010, 20]


# ---------------------------------------------------------------------------
# Export overwrite protection and atomic write
# ---------------------------------------------------------------------------

def test_export_refuses_to_overwrite_without_force(tmp_path):
    add("5", "shopping")
    dest = tmp_path / "expenses.csv"
    dest.write_text("IMPORTANT USER DATA\n", encoding="utf-8")
    result = invoke("export", "--file", str(dest))
    assert result.exit_code == 1
    assert "Refusing to overwrite" in result.stdout
    assert dest.read_text(encoding="utf-8") == "IMPORTANT USER DATA\n"


def test_export_force_overwrites_atomically(tmp_path):
    add("5.50", "shopping", description="Widget", date="2026-04-01")
    dest = tmp_path / "expenses.csv"
    dest.write_text("IMPORTANT USER DATA\n", encoding="utf-8")
    result = invoke("export", "--file", str(dest), "--force")
    assert result.exit_code == 0
    assert "Exported" in result.stdout
    text = dest.read_text(encoding="utf-8")
    assert "IMPORTANT USER DATA" not in text
    rows = list(csv.reader(text.splitlines()))
    assert rows[0] == ["id", "date", "category", "amount", "description"]
    assert rows[1][3] == "5.50"
    assert rows[1][4] == "Widget"
    leftovers = list(tmp_path.glob(".expenses.csv.*.tmp"))
    assert leftovers == []

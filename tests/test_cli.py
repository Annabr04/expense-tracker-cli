import os
from pathlib import Path
from typer.testing import CliRunner
from app.main import app
from app.database import DB_PATH, init_db, get_db

runner = CliRunner()


def setup_function():
    """Clean database before each test."""
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_db()


def test_add_expense():
    result = runner.invoke(app, ["add", "15.50", "--category", "food", "--description", "Lunch"])
    assert result.exit_code == 0
    assert "Added expense" in result.stdout
    assert "$15.50" in result.stdout


def test_add_rejects_non_positive_amount():
    result = runner.invoke(app, ["add", "0", "--category", "food"])
    assert result.exit_code == 1
    assert "Amount must be greater than 0" in result.stdout

    result = runner.invoke(app, ["add", "-5", "--category", "food"])
    assert result.exit_code == 1
    assert "Amount must be greater than 0" in result.stdout


def test_list_expenses():
    runner.invoke(app, ["add", "10", "--category", "food"])
    runner.invoke(app, ["add", "25", "--category", "transport"])
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "food" in result.stdout
    assert "transport" in result.stdout


def test_summary():
    runner.invoke(app, ["add", "20", "--category", "food"])
    runner.invoke(app, ["add", "30", "--category", "food"])
    runner.invoke(app, ["add", "15", "--category", "transport"])
    result = runner.invoke(app, ["summary"])
    assert result.exit_code == 0
    assert "food" in result.stdout
    assert "Grand Total" in result.stdout


def test_delete_expense():
    runner.invoke(app, ["add", "9.99", "--category", "other"])
    result = runner.invoke(app, ["delete", "1"])
    assert result.exit_code == 0
    assert "Deleted expense #1" in result.stdout


def test_export():
    runner.invoke(app, ["add", "5", "--category", "shopping"])
    result = runner.invoke(app, ["export", "--file", "test_export.csv"])
    assert result.exit_code == 0
    assert "Exported" in result.stdout
    assert Path("test_export.csv").exists()
    Path("test_export.csv").unlink(missing_ok=True)

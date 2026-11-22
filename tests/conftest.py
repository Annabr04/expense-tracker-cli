import pytest


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Point every test at a throwaway SQLite file.

    The production default is repo-root expenses.db. Tests must never create,
    modify, or unlink that file. Override via EXPENSE_TRACKER_DB so the
    path is resolved at connection time, not at import time.
    """
    db_path = tmp_path / "expenses.db"
    monkeypatch.setenv("EXPENSE_TRACKER_DB", str(db_path))
    yield db_path

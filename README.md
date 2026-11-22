# Personal Expense Tracker (CLI)

A clean, practical command-line expense tracker built with **Python**, **Typer**, **SQLite**, and **Rich**.

Track daily spending, view summaries by category, and export your data — all from the terminal.

**Requires Python 3.11 or later.** CI runs on Python 3.11; the suite is also verified on 3.13.

---

## Features

| Command | Description |
|---------|-------------|
| `add` | Add a new expense with amount, category, and optional note |
| `list` | Show recent expenses (with optional category filter) |
| `summary` | Monthly spending breakdown by category |
| `delete` | Remove an expense by ID |
| `export` | Export all data to CSV |
| `categories` | Show suggested categories |

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/Annabr04/expense-tracker-cli.git
cd expense-tracker-cli

# 2. Create virtual environment (Python 3.11+)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run commands
python -m app.main add 12.50 --category food --description "Lunch"
python -m app.main list
python -m app.main summary
```

The SQLite database is created automatically as `expenses.db` in the project root. To use a different file, set `EXPENSE_TRACKER_DB` to an absolute or relative path.

---

## Example Usage

```bash
# Add expenses
python -m app.main add 4.75 -c food -d "Coffee"
python -m app.main add 45.00 -c transport -d "Gas"
python -m app.main add 89.99 -c shopping

# List recent expenses (default --limit 20)
python -m app.main list
python -m app.main list --category food
python -m app.main list --limit 5

# Monthly summary
python -m app.main summary
python -m app.main summary --month 2026-09

# Export to CSV (refuses to overwrite an existing file unless --force is given)
python -m app.main export --file my_expenses.csv
python -m app.main export --file my_expenses.csv --force

# Delete an entry
python -m app.main delete 3
```

---

## Input rules

- **Amounts** are decimal money, not floating-point. They must be greater than 0 and have at most two decimal places (`12.50` is fine; `0`, `-5`, and `0.001` are rejected). Values are stored as integer cents.
- **`list --limit` / `-n`** must be a positive integer (**1 or greater**; default 20). `0` and negative values are rejected. (A limit of 0 would always print “No expenses found.”, and SQLite treats `LIMIT -1` as “no limit”.)
- **`summary --month`** must be `YYYY-MM` with a real calendar month (January–December), for example `2026-09`. Unpadded values (`2026-9`), a bare year (`2026`), and invalid months (`2026-13`) are rejected. If you omit `--month`, the current month is used.
- **Dates** on `add --date` must be `YYYY-MM-DD`.
- **`export`** writes the destination file atomically (temp file + replace). If the file already exists, the command exits with a non-zero status and leaves it untouched unless you pass `--force`.
- Negative positional values (for example a negative amount, or `delete -1`) need a `--` separator so they are not parsed as options: `python -m app.main add --category food -- -5`.

### Existing databases

If you already have an `expenses.db` from an earlier version (where `amount` was a SQLite `REAL` dollar value), the first command you run migrates it in place to `amount_cents INTEGER`. Dollar values are multiplied by 100 and rounded with SQLite `ROUND()` (half away from zero). Back up `expenses.db` before that first run if you care about the old file.

---

## Project Structure

```
expense-tracker-cli/
├── app/
│   ├── __init__.py
│   ├── main.py          # CLI commands (Typer)
│   ├── database.py      # SQLite connection, schema, and migration
│   ├── money.py         # Decimal parsing and cents conversion
│   └── models.py
├── tests/
│   ├── conftest.py      # Isolates tests from the real expenses.db
│   └── test_cli.py
├── .github/workflows/ci.yml
├── LICENSE
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## What This Project Demonstrates

- Building a real command-line application with **Typer**
- Working with **SQLite** (create, insert, query, aggregate, and a schema migration)
- Exact money arithmetic with **`Decimal`** (no binary-float drift)
- Clean project structure and separation of concerns
- Pretty terminal output with **Rich**
- Input validation and helpful error messages
- Automated tests with **pytest**, isolated from the developer’s database
- Atomic CSV export that will not overwrite files by accident

---

## Future Improvements

- Recurring expenses
- Budgets and alerts
- Simple charts in the terminal
- Web dashboard companion (FastAPI)

## Tests

```bash
pytest -v
```

The suite points `EXPENSE_TRACKER_DB` at a temporary file, so running pytest will not create, modify, or delete your real `expenses.db`. `pytest.ini` sets `pythonpath = .`, so the command works from the repo root without setting `PYTHONPATH`.

GitHub Actions runs the suite on every push and pull request to `main` (Python 3.11).

## License

MIT. See [LICENSE](LICENSE).

---

Built as a portfolio project for junior Python developer roles.

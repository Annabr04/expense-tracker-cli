# Personal Expense Tracker (CLI)

A clean, practical command-line expense tracker built with **Python**, **Typer**, **SQLite**, and **Rich**.

Track daily spending, view summaries by category, and export your data — all from the terminal.

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

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run commands
python -m app.main add 12.50 --category food --description "Lunch"
python -m app.main list
python -m app.main summary
```

---

## Example Usage

```bash
# Add expenses
python -m app.main add 4.75 -c food -d "Coffee"
python -m app.main add 45.00 -c transport -d "Gas"
python -m app.main add 89.99 -c shopping

# List recent expenses
python -m app.main list
python -m app.main list --category food

# Monthly summary
python -m app.main summary
python -m app.main summary --month 2026-09

# Export to CSV
python -m app.main export --file my_expenses.csv

# Delete an entry
python -m app.main delete 3
```

---

## Project Structure

```
expense-tracker-cli/
├── app/
│   ├── __init__.py
│   ├── main.py          # CLI commands (Typer)
│   ├── database.py      # SQLite connection & setup
│   └── models.py
├── tests/
│   └── test_cli.py
├── requirements.txt
└── README.md
```

---

## What This Project Demonstrates

- Building a real command-line application with **Typer**
- Working with **SQLite** (create, insert, query, aggregate)
- Clean project structure and separation of concerns
- Pretty terminal output with **Rich**
- Input validation and helpful error messages
- Automated tests with **pytest**
- CSV export functionality

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

GitHub Actions runs that command on every push and pull request to `main`.

## License

MIT. See [LICENSE](LICENSE).

---

Built as a portfolio project for junior Python developer roles.

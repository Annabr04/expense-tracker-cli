import csv
import os
import re
import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .database import get_db, init_db
from .money import (
    MoneyError,
    cents_to_decimal,
    decimal_to_cents,
    format_dollars,
    parse_amount,
)

app = typer.Typer(
    name="expense",
    help="Personal Expense Tracker – track spending from the command line.",
    add_completion=False,
)
console = Console()

# Common categories for convenience
DEFAULT_CATEGORIES = [
    "food", "transport", "housing", "utilities",
    "entertainment", "health", "shopping", "other"
]

MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@app.callback()
def main():
    """Personal Expense Tracker CLI"""
    init_db()


def _validate_month(month: str) -> str:
    if not MONTH_PATTERN.fullmatch(month):
        console.print(
            "[red]Invalid month. Use YYYY-MM with a real month (e.g. 2026-09).[/red]"
        )
        raise typer.Exit(1)
    return month


def _validate_limit(limit: int) -> int:
    # 0 is rejected: it would always print "No expenses found." and is not a
    # useful page size. Negatives are also rejected (SQLite treats LIMIT -1
    # as no limit).
    if limit < 1:
        console.print("[red]--limit must be a positive integer (1 or greater).[/red]")
        raise typer.Exit(1)
    return limit


@app.command()
def add(
    amount: str = typer.Argument(..., help="Expense amount, positive, at most 2 decimal places (e.g. 12.50)"),
    category: str = typer.Option(..., "--category", "-c", help="Category (food, transport, etc.)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Optional note"),
    date_str: Optional[str] = typer.Option(None, "--date", help="Date YYYY-MM-DD (default: today)"),
):
    """Add a new expense."""
    try:
        parsed = parse_amount(amount)
    except MoneyError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    category = category.lower().strip()
    expense_date = date_str or date.today().isoformat()

    # Basic date validation
    try:
        datetime.strptime(expense_date, "%Y-%m-%d")
    except ValueError:
        console.print("[red]Invalid date format. Use YYYY-MM-DD[/red]")
        raise typer.Exit(1)

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO expenses (amount_cents, category, description, date)
            VALUES (?, ?, ?, ?)
            """,
            (decimal_to_cents(parsed), category, description, expense_date),
        )
        expense_id = cursor.lastrowid

    console.print(
        f"[green]✓[/green] Added expense #{expense_id}: "
        f"[bold]{format_dollars(parsed)}[/bold] in [cyan]{category}[/cyan]"
        + (f" ({description})" if description else "")
    )


@app.command("list")
def list_expenses(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max number of rows to show (must be >= 1; default: 20)"),
):
    """List recent expenses."""
    limit = _validate_limit(limit)

    query = "SELECT * FROM expenses"
    params = []

    if category:
        query += " WHERE category = ?"
        params.append(category.lower().strip())

    query += " ORDER BY date DESC, id DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()

    if not rows:
        console.print("[yellow]No expenses found.[/yellow]")
        return

    table = Table(title="Expenses", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=6)
    table.add_column("Date", width=12)
    table.add_column("Category", width=14)
    table.add_column("Amount", justify="right", width=10)
    table.add_column("Description")

    total = Decimal("0.00")
    for row in rows:
        amount = cents_to_decimal(row["amount_cents"])
        table.add_row(
            str(row["id"]),
            row["date"],
            row["category"],
            format_dollars(amount),
            row["description"] or "",
        )
        total += amount

    console.print(table)
    console.print(f"\n[bold]Showing {len(rows)} expense(s) | Subtotal: {format_dollars(total)}[/bold]")


@app.command()
def summary(
    month: Optional[str] = typer.Option(None, "--month", "-m", help="Month filter YYYY-MM (default: current month)"),
):
    """Show spending summary by category."""
    if month is None:
        month = date.today().strftime("%Y-%m")
    else:
        month = _validate_month(month)

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT category, COUNT(*) as count, SUM(amount_cents) as total_cents
            FROM expenses
            WHERE date LIKE ?
            GROUP BY category
            ORDER BY total_cents DESC
            """,
            (f"{month}-%",),
        ).fetchall()

        grand_cents = conn.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) FROM expenses WHERE date LIKE ?",
            (f"{month}-%",),
        ).fetchone()[0]

    if not rows:
        console.print(f"[yellow]No expenses found for {month}.[/yellow]")
        return

    grand_total = cents_to_decimal(grand_cents)

    table = Table(title=f"Spending Summary — {month}", show_header=True, header_style="bold magenta")
    table.add_column("Category", width=16)
    table.add_column("Count", justify="right", width=8)
    table.add_column("Total", justify="right", width=12)
    table.add_column("% of Total", justify="right", width=10)

    for row in rows:
        cat_total = cents_to_decimal(row["total_cents"])
        pct = (cat_total / grand_total * 100) if grand_total else Decimal("0")
        table.add_row(
            row["category"],
            str(row["count"]),
            format_dollars(cat_total),
            f"{pct:.1f}%",
        )

    console.print(table)
    console.print(Panel(f"[bold green]Grand Total: {format_dollars(grand_total)}[/bold green]", expand=False))


@app.command()
def delete(
    expense_id: int = typer.Argument(..., help="ID of the expense to delete"),
):
    """Delete an expense by ID."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        if cursor.rowcount == 0:
            console.print(f"[red]No expense found with ID {expense_id}[/red]")
            raise typer.Exit(1)

    console.print(f"[green]✓[/green] Deleted expense #{expense_id}")


@app.command()
def categories():
    """Show suggested categories."""
    console.print("[bold]Suggested categories:[/bold]")
    for cat in DEFAULT_CATEGORIES:
        console.print(f"  • {cat}")


def _atomic_write_csv(dest: Path, rows) -> None:
    parent = dest.parent if dest.parent.as_posix() != "" else Path(".")
    if dest.parent.as_posix() not in ("", ".") and not dest.parent.exists():
        console.print(f"[red]Directory does not exist: {dest.parent}[/red]")
        raise typer.Exit(1)

    fd, tmp_name = tempfile.mkstemp(prefix=f".{dest.name}.", suffix=".tmp", dir=str(parent))
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["id", "date", "category", "amount", "description"])
            for row in rows:
                amount = cents_to_decimal(row["amount_cents"])
                writer.writerow(
                    [
                        row["id"],
                        row["date"],
                        row["category"],
                        f"{amount:.2f}",
                        row["description"] or "",
                    ]
                )
        os.replace(tmp_name, dest)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


@app.command()
def export(
    filename: str = typer.Option("expenses.csv", "--file", "-f", help="Output CSV filename"),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite the output file if it already exists",
    ),
):
    """Export all expenses to a CSV file."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, date, category, amount_cents, description FROM expenses ORDER BY date, id"
        ).fetchall()

    if not rows:
        console.print("[yellow]No expenses to export.[/yellow]")
        return

    dest = Path(filename)
    if dest.exists() and not force:
        console.print(
            f"[red]Refusing to overwrite existing file: {filename} (use --force)[/red]"
        )
        raise typer.Exit(1)

    _atomic_write_csv(dest, rows)
    console.print(f"[green]✓[/green] Exported {len(rows)} expenses to [bold]{filename}[/bold]")


if __name__ == "__main__":
    app()

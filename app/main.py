from datetime import date, datetime
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .database import init_db, get_db

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


@app.callback()
def main():
    """Personal Expense Tracker CLI"""
    init_db()


@app.command()
def add(
    amount: float = typer.Argument(..., help="Expense amount (e.g. 12.50)"),
    category: str = typer.Option(..., "--category", "-c", help="Category (food, transport, etc.)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Optional note"),
    date_str: Optional[str] = typer.Option(None, "--date", help="Date YYYY-MM-DD (default: today)"),
):
    """Add a new expense."""
    if amount <= 0:
        console.print("[red]Amount must be greater than 0[/red]")
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
            INSERT INTO expenses (amount, category, description, date)
            VALUES (?, ?, ?, ?)
            """,
            (amount, category, description, expense_date),
        )
        expense_id = cursor.lastrowid

    console.print(
        f"[green]✓[/green] Added expense #{expense_id}: "
        f"[bold]${amount:.2f}[/bold] in [cyan]{category}[/cyan]"
        + (f" ({description})" if description else "")
    )


@app.command("list")
def list_expenses(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max number of rows to show"),
):
    """List recent expenses."""
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

    total = 0.0
    for row in rows:
        table.add_row(
            str(row["id"]),
            row["date"],
            row["category"],
            f"${row['amount']:.2f}",
            row["description"] or "",
        )
        total += row["amount"]

    console.print(table)
    console.print(f"\n[bold]Showing {len(rows)} expense(s) | Subtotal: ${total:.2f}[/bold]")


@app.command()
def summary(
    month: Optional[str] = typer.Option(None, "--month", "-m", help="Month filter YYYY-MM (default: current month)"),
):
    """Show spending summary by category."""
    if month is None:
        month = date.today().strftime("%Y-%m")

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT category, COUNT(*) as count, SUM(amount) as total
            FROM expenses
            WHERE date LIKE ?
            GROUP BY category
            ORDER BY total DESC
            """,
            (f"{month}%",),
        ).fetchall()

        grand_total = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE date LIKE ?",
            (f"{month}%",),
        ).fetchone()[0]

    if not rows:
        console.print(f"[yellow]No expenses found for {month}.[/yellow]")
        return

    table = Table(title=f"Spending Summary — {month}", show_header=True, header_style="bold magenta")
    table.add_column("Category", width=16)
    table.add_column("Count", justify="right", width=8)
    table.add_column("Total", justify="right", width=12)
    table.add_column("% of Total", justify="right", width=10)

    for row in rows:
        pct = (row["total"] / grand_total * 100) if grand_total else 0
        table.add_row(
            row["category"],
            str(row["count"]),
            f"${row['total']:.2f}",
            f"{pct:.1f}%",
        )

    console.print(table)
    console.print(Panel(f"[bold green]Grand Total: ${grand_total:.2f}[/bold green]", expand=False))


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


@app.command()
def export(
    filename: str = typer.Option("expenses.csv", "--file", "-f", help="Output CSV filename"),
):
    """Export all expenses to a CSV file."""
    import csv

    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, date, category, amount, description FROM expenses ORDER BY date, id"
        ).fetchall()

    if not rows:
        console.print("[yellow]No expenses to export.[/yellow]")
        return

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "date", "category", "amount", "description"])
        for row in rows:
            writer.writerow([row["id"], row["date"], row["category"], row["amount"], row["description"] or ""])

    console.print(f"[green]✓[/green] Exported {len(rows)} expenses to [bold]{filename}[/bold]")


if __name__ == "__main__":
    app()

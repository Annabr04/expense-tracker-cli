# PR draft: QA must-fixes for expense-tracker-cli

**Do not push or open this PR until the user approves.** This file is a local draft for the Scrum Master / reviewer.

- **Repo:** https://github.com/Annabr04/expense-tracker-cli
- **Base:** `origin/main` @ `2d7def845a438b5540bd1dfeacffbfedb48e7528` (`docs: add MIT license, .gitignore, and a tests section (#1)`)
- **Branch:** `fix/qa-must-fixes` (local only; no upstream)
- **Commit:** `053f79eebb6e81689830d21afc916da95fa7c68a`
- **Source of truth:** `/workspace/qa-portfolio/QA_SUMMARY.md` (QA Engineer, 22 November 2026, ET)

## Test counts

| Run | Result |
|---|---|
| Baseline, Python 3.11.18, pytest 9.2.0, `PYTHONPATH=. pytest -v` (matches CI / QA) | **6 passed**, 0.14s |
| Baseline, README-style `pytest -v` (no `PYTHONPATH`, no `pytest.ini`) | collection error: `ModuleNotFoundError: No module named 'app'` in this environment |
| Final, Python 3.11.18, pytest 9.2.0, README-style `pytest -v` (no `PYTHONPATH`) | **25 passed**, 0.54s |
| Final, Python 3.13.18, same command | **25 passed**, 0.31s |

Baseline of 6 matches QA's measured suite. The six original tests remain and still pass.

Pinned, verified install (same resolution QA recorded): `typer==0.29.2`, `rich==15.0.0`, `pytest==9.2.0`. The stale `typer[all]` extra is gone; a clean `pip install -r requirements.txt` no longer warns that the extra is missing.

## Isolation proof (blocker)

Before the baseline run, no `expenses.db` existed in the fresh clone. A sentinel file was written at `/workspace/expense-tracker-cli/expenses.db` and backed up to `/tmp/expenses.db.baseline-backup`.

- Sentinel content: `SENTINEL USER DATA DO NOT DELETE\nQA-BASELINE-SENTINEL\n`
- SHA-256 before any tests: `566a36ab3e06411131ce4041a693cd97b76584e0174ee682b84dd723b182b0bf`

After the **baseline** (old) suite:

- The file still existed but was **replaced** with a 12,288-byte SQLite database (`SQLite format 3...`).
- SHA-256 after baseline: `21fbf6e4d135976a8024050466b933388b4c68fe9ad9f0ef1c2c20b4cb2490e5`
- This confirms QA's blocker: `setup_function` unlinked the real `expenses.db` and tests leaked data into it.

After the **final** suite (sentinel restored first):

- File still present, bytes and checksum **unchanged**: `566a36ab3e06411131ce4041a693cd97b76584e0174ee682b84dd723b182b0bf`
- No leftover `*.csv` or `*.tmp` in the repo root
- `tests/conftest.py` autouse fixture sets `EXPENSE_TRACKER_DB` to a `tmp_path` file; `get_db_path()` is resolved at connection time
- `test_suite_does_not_touch_default_expenses_db` also plants a sentinel at the production path and checks the checksum

## Fixes

1. **BLOCKER — test isolation.** `DB_PATH` is no longer a single import-time constant used for every connection. `get_db_path()` honors `EXPENSE_TRACKER_DB`, otherwise the repo-root `expenses.db`. An autouse `tmp_path` fixture points every test at a temp file. Tests never create, modify, or unlink the real database.

2. **Failure-path and empty-path tests.** Coverage added for empty `list` / `summary` / `export`, invalid amount and date, delete of a missing id, export to a missing parent directory, `categories`, and `list --category` (including a case-insensitive match and a no-match filter).

3. **Pinned dependencies and `typer[all]`.** `requirements.txt` is now exact versions that were installed and tested: `typer==0.29.2`, `rich==15.0.0`, `pytest==9.2.0`. Plain `typer` plus an explicit `rich` dependency; no `typer[all]`. README documents **Python 3.11+** (CI stays on 3.11).

4. **`pytest.ini`** with `pythonpath = .` (and `testpaths = tests`). `pytest -v` from the repo root works without `PYTHONPATH`.

5. **`--limit` and `--month` validation.** `--limit` must be an integer **>= 1** (default still 20). `0` is rejected — a zero limit is not a useful page size and previously printed “No expenses found.” instead of an error. Negatives are rejected (`--limit=-1`; SQLite would treat `LIMIT -1` as no limit). `summary --month` must be `YYYY-MM` with a real calendar month. `foo`, `2026-13`, unpadded `2026-9`, bare `2026`, `2026-00`, and `2026-09-15` are rejected with exit code 1. The month query is now `date LIKE 'YYYY-MM-%'` after validation.

6. **Decimal amounts end to end.** Parsing uses `decimal.Decimal` (amount is taken as a string so a binary float never touches the value). Amounts must be `> 0` with **at most two decimal places** (`0.001` is now rejected, which also stops “accepted but printed as $0.00”). Storage is `amount_cents INTEGER`, not `REAL` dollars. Sums and display use `Decimal`. `test_decimal_sum_has_no_float_drift` adds `0.10 + 0.20` and asserts `$0.30`.

7. **Export overwrite protection and atomic write.** If the target file exists, export exits 1 with `Refusing to overwrite existing file: … (use --force)` and leaves the file untouched. `--force` overwrites. Writes go to a temp file in the same directory and are published with `os.replace`. Export of an empty database still writes nothing. A missing parent directory fails with a clear error instead of creating it.

## Behavior and compatibility changes

These are intentional and documented in the README:

- **Storage schema.** New databases use `amount_cents INTEGER` (integer cents). Existing `expenses.db` files with `amount REAL` (dollars) are **migrated in place on the first command**: the table is rewritten, dollars × 100, rounded with SQLite `ROUND()` (half away from zero). Please back up `expenses.db` before that first run if you care about the old file. A regression test builds a legacy REAL database and checks that `10.10 + 0.20` becomes 1010 + 20 cents and summarizes as `$10.30`.
- **CSV export** writes amounts as two-decimal strings (`5.00`, `5.50`) rather than a Python `float` repr (`5.0` / `15.5`).
- **`add 0.001`** (and any amount with more than two decimal places) is now rejected.
- **`list --limit 0` and `--limit=-1`** now exit 1 instead of listing nothing / everything.
- **`summary --month`** no longer silently treats invalid values as “No expenses found.” A bare year such as `2026` no longer accidentally summarizes the whole year via `LIKE '2026%'`.
- **`export`** will not overwrite an existing file without `--force`.
- **`EXPENSE_TRACKER_DB`** selects the database file (used by tests; also useful for a personal data path).

Unchanged: default `list --limit` of 20; default summary month is the current month; category names are still lowercased and stripped; delete of a missing id still exits 1; happy-path add/list/summary/delete/export output still includes the same phrases the original tests look for (`Added expense`, `$15.50`, `Grand Total`, etc.).

The `Expense` dataclass `amount` field is now `Decimal`. It is still unused by the CLI (QA noted that as a nice-to-have).

## What QA should re-verify

1. **Isolation (blocker).** Plant a sentinel `expenses.db` in the repo root, record its SHA-256, run `pytest -v` from the repo root with no `PYTHONPATH`, and confirm the checksum is unchanged and the file is not a SQLite database. Confirm no `test_export.csv` (or similar) is left in the working directory.
2. **Full suite.** 25 passed on Python 3.11 (and optionally 3.13). `pip install -r requirements.txt` has no `typer[all]` warning.
3. **Validation.** `list --limit 0`, `list --limit=-1`, and `summary --month` values `foo`, `2026-13`, `2026-9`, and `2026` all exit 1 with a clear message. A valid `--month 2026-09` still summarizes only that month.
4. **Decimal.** `add 0.10` and `add 0.20` then `summary` / `list` show `$0.30`, not a float artifact. `add 0.001` is rejected.
5. **Migration.** Open a copy of an old `amount REAL` database (or the fixture in `test_legacy_real_amounts_are_migrated`) and confirm the first CLI command rewrites it to `amount_cents` and that displayed totals are still correct. Spot-check rounding on half-cent legacy values if you have any.
6. **Export.** Writing over an existing file without `--force` exits 1 and preserves the original bytes; `--force` replaces the file; the CSV amount column is two-decimal text; an empty database does not create a file.
7. **Docs.** README states Python 3.11+, the `--limit` / `--month` rules (including that 0 is not allowed), the Decimal/cents storage and migration, `--force`, and test isolation.

CI polish (pip cache, read-only permissions, `pytest -v` in the workflow) was **not** part of this change; QA already noted CI exists and is green. This branch does not add ruff or wire up the unused `Expense` dataclass.

# Step 01 Database Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the stub in `database/db.py` with a working SQLite layer (`get_db`, `init_db`, `seed_db`) and initialise it on app startup.

**Architecture:** One module, `database/db.py`, using raw `sqlite3`. The DB path is a module-level constant `DB_PATH` (project root `spendly.db`) so tests can point it at a temporary file. `app.py` calls `init_db()` and `seed_db()` inside `app.app_context()` at import time, so the DB is ready before any route is served.

**Tech Stack:** Python 3, Flask 3.1.3, `sqlite3` (stdlib), `werkzeug.security`, pytest.

**Spec:** `.claude/specs/01-database-setup.md`

## Global Constraints

- No ORM, no SQLAlchemy; raw `sqlite3` only.
- Parameterised queries only; never string-format values into SQL.
- `PRAGMA foreign_keys = ON` on every connection; `row_factory = sqlite3.Row`.
- `amount` is REAL; `expenses.date` is zero-padded `YYYY-MM-DD`; `created_at` uses `CURRENT_TIMESTAMP`.
- Categories (exact): Food, Transport, Bills, Health, Entertainment, Shopping, Other.
- Passwords hashed with `generate_password_hash`.
- `init_db()` and `seed_db()` are idempotent.
- No new pip packages. Existing placeholder routes in `app.py` stay unchanged.

## Review Focus

- Date `2026-3-5` or `2026-13-45` must be rejected by the CHECK (padding alone is not enough): the test inserts both. (Task 1)
- Seeding when today's day-of-month is below the listed days (for example the 2nd): no row may be dated after today. (Task 2)
- `seed_db()` called with existing users (not only the demo user): no changes. (Task 2)
- Running `init_db()` on an already populated database must not lose data. (Task 1)
- Deleting a user who has expenses is blocked by the foreign key. (Task 1)

## File Structure

- Modify: `database/db.py` (all DB logic)
- Modify: `app.py` (startup initialisation only)
- Create: `tests/test_database_setup.py` (the spec lists "Files to create: None"; this test file is an addition so the Definition of Done can be verified. It does not touch the spec's file list otherwise.)
- Create: `tests/conftest.py` (temp-DB fixture)

---

### Task 1: Connection helper and schema

**Files:**
- Modify: `database/db.py`
- Create: `tests/conftest.py`, `tests/test_database_setup.py`

**Interfaces:**
- Produces: `DB_PATH: str`, `get_db() -> sqlite3.Connection`, `init_db() -> None`, `CATEGORIES: tuple[str, ...]`
- Fixture `db_path` (conftest): monkeypatches `database.db.DB_PATH` to a `tmp_path` file and returns it.

- [ ] **Step 1: Write failing tests** in `tests/test_database_setup.py` (import `sqlite3`, `pytest`, `from database import db`):
  - `test_get_db_row_factory_and_fk`: `get_db()` rows support `row["name"]`; `PRAGMA foreign_keys` returns 1.
  - `test_init_db_creates_tables_and_is_idempotent`: call `init_db()` twice; `sqlite_master` contains `users` and `expenses`.
  - `test_init_db_keeps_existing_data`: insert a user, call `init_db()` again, user still present.
  - `test_duplicate_email_rejected`: second insert with same email raises `sqlite3.IntegrityError`.
  - `test_expense_fk_rejected`: insert expense with `user_id=999` raises `sqlite3.IntegrityError`.
  - `test_user_with_expenses_cannot_be_deleted`: deleting the parent user raises `sqlite3.IntegrityError`.
  - `test_invalid_category_rejected`: category `"Travel"` raises `sqlite3.IntegrityError`; each of the 7 valid categories inserts fine.
  - `test_invalid_date_rejected` (parametrised): `"2026-3-5"`, `"2026-13-45"`, `"05-03-2026"`, `""` raise `sqlite3.IntegrityError`; `"2026-03-05"` succeeds.
  - `test_created_at_default`: inserted rows have non-null `created_at`.
  - `test_not_null_columns`: NULL `name`/`email`/`password_hash`, and NULL `amount`/`category`/`date`, raise `sqlite3.IntegrityError`.
- [ ] **Step 2: Run** `python -m pytest tests/test_database_setup.py -v`. Expected: FAIL (import/attribute errors).
- [ ] **Step 3: Implement** in `database/db.py`: `DB_PATH` = `spendly.db` in the project root (parent of the `database` package); `get_db()` opens `DB_PATH` (read at call time), sets `row_factory`, runs `PRAGMA foreign_keys = ON`; `init_db()` runs `CREATE TABLE IF NOT EXISTS` for both tables exactly as in spec Section 4. Category CHECK is `category IN (...)` over the seven names. Date CHECK combines `date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'` with `date(date) = date` so unreal dates such as `2026-13-45` fail. Close the connection in `finally`.
- [ ] **Step 4: Run** the same command. Expected: all PASS.
- [ ] **Step 5: Commit** `feat: add db connection helper and schema`

### Task 2: Seed data

**Files:**
- Modify: `database/db.py`, `tests/test_database_setup.py`

**Interfaces:**
- Consumes: `get_db()`, `init_db()`, `CATEGORIES`
- Produces: `seed_db(today: datetime.date | None = None) -> None`. The optional `today` argument exists only so tests can pin the date; the app calls `seed_db()`.

- [ ] **Step 1: Write failing tests:**
  - `test_seed_creates_demo_user`: one user, name `Demo User`, email `demo@spendly.com`; `check_password_hash(row["password_hash"], "demo123")` is true and the hash is not `demo123`.
  - `test_seed_expenses`: 8 rows, all for the demo user; all 7 categories present; `round(sum(amount), 2) == 346.24`; Bills total `120.00` is the highest category total.
  - `test_seed_dates_not_in_future` (parametrised `today` = day 2, day 9, day 16, day 28 of a month): every date matches `YYYY-MM-DD`, is in the same month, and is `<= today`.
  - `test_seed_uses_pinned_days_when_today_is_late`: with `today` on the 28th, dates' days are `01,03,05,08,10,12,14,16` and amounts per the spec table.
  - `test_seed_idempotent`: calling twice leaves 1 user and 8 expenses.
  - `test_seed_skips_when_users_exist`: insert a different user first, then `seed_db()`; still exactly 1 user and 0 expenses.
- [ ] **Step 2: Run** `python -m pytest tests/test_database_setup.py -v`. Expected: new tests FAIL.
- [ ] **Step 3: Implement** `seed_db`: `SELECT COUNT(*) FROM users`; return if > 0. Otherwise insert the demo user, then the 8 rows from spec Section 5 (Food 45.50 d1 Groceries; Transport 28.00 d3 Metro card top-up; Bills 120.00 d5 Electricity bill; Health 35.99 d8 Pharmacy; Entertainment 25.00 d10 Movie tickets; Shopping 49.00 d12 Clothing; Other 10.00 d14 Miscellaneous; Food 32.75 d16 Dinner out) with `executemany`, using `min(day, today.day)` and `date(today.year, today.month, day).isoformat()`. One commit for the user and expenses together.
- [ ] **Step 4: Run** the same command. Expected: all PASS.
- [ ] **Step 5: Commit** `feat: add idempotent seed data`

### Task 3: App startup wiring

**Files:**
- Modify: `app.py`, `tests/test_database_setup.py`

**Interfaces:**
- Consumes: `init_db()`, `seed_db()` from `database.db`

- [ ] **Step 1: Write failing test** `test_app_startup_creates_database`: with `DB_PATH` monkeypatched to a temp file, `importlib.reload(app)` leaves the file existing with both tables and 1 demo user; `app.app.test_client().get("/")` returns 200.
- [ ] **Step 2: Run** the test. Expected: FAIL (file not created).
- [ ] **Step 3: Implement** in `app.py`: `from database.db import get_db, init_db, seed_db` and, after `app = Flask(__name__)`, `with app.app_context(): init_db(); seed_db()`. Routes untouched. `get_db` is imported as the spec requires even though no route uses it yet.
- [ ] **Step 4: Run** `python -m pytest -v`. Expected: all PASS. Then run `python -c "import app"` in the project root and confirm `spendly.db` is created; delete it afterwards unless it is gitignored.
- [ ] **Step 5: Commit** `feat: initialise database on app startup`

## Self-Review

- Spec coverage: Sections 4, 5, 6, 10, 11, 12, 13 and all 11 Definition of Done items map to Tasks 1-3 (parameterised SQL and the no-ORM rule are verified by inspection).
- Signatures are consistent across tasks (`seed_db(today=None)`, `DB_PATH`, `CATEGORIES`).
- Known spec deviation: the two test files are additions to the spec's "Files to create: None".

# Spec: Step 1 — Database Setup

## 1. Overview

This step replaces the stub in `database/db.py` with a working SQLite implementation for Spendly. It defines the two core tables (`users`, `expenses`), a connection helper, schema initialization, and idempotent demo seed data.

This is the foundational step of the project. Authentication (register/login), the user profile, and all expense tracking features read from and write to this database, so none of them can be built until it exists and behaves correctly.

## 2. Depends on

- None. This is the first step and has no prerequisites.

## 3. Routes

- No new routes.
- Existing placeholder routes in `app.py` remain unchanged.

## 4. Database Schema

### Table A: `users`

| Column | SQLite Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| name | TEXT | NOT NULL |
| email | TEXT | NOT NULL, UNIQUE |
| password_hash | TEXT | NOT NULL |
| created_at | TEXT | NOT NULL, DEFAULT CURRENT_TIMESTAMP |

### Table B: `expenses`

| Column | SQLite Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| user_id | INTEGER | NOT NULL, FOREIGN KEY → users(id) |
| amount | REAL | NOT NULL |
| category | TEXT | NOT NULL, CHECK (value must be one of the fixed categories in Section 10) |
| date | TEXT | NOT NULL, CHECK (value must match the zero-padded YYYY-MM-DD pattern); must be in YYYY-MM-DD format |
| description | TEXT | NULL allowed |
| created_at | TEXT | NOT NULL, DEFAULT CURRENT_TIMESTAMP |

## 5. Functions to Implement (database/db.py)

| Function | Responsibilities |
|---|---|
| `get_db()` | Opens `spendly.db` located in the project root; sets `row_factory = sqlite3.Row`; enables `PRAGMA foreign_keys = ON`; returns the connection |
| `init_db()` | Creates both tables using `CREATE TABLE IF NOT EXISTS`; safe to call multiple times |
| `seed_db()` | Checks whether the `users` table already has rows — if yes, returns early; otherwise inserts one demo user and 8 sample expenses (details below) |

### seed_db() data requirements

| Item | Requirement |
|---|---|
| Demo user name | Demo User |
| Demo user email | demo@spendly.com |
| Demo user password | demo123, stored hashed via werkzeug |
| Expense count | 8, all linked to the demo user |
| Category coverage | All 7 categories appear at least once |
| Date range | Spread across the current month, in YYYY-MM-DD format; no date may be later than today (see the day-of-month rule below) |
| Amounts | Fixed values from the table below, so the total is exactly 346.24 |
| Top category | Bills has the highest category total |

### seed_db() expense rows

| # | Category | Amount | Day of month | Description |
|---|---|---|---|---|
| 1 | Food | 45.50 | 1 | Groceries |
| 2 | Transport | 28.00 | 3 | Metro card top-up |
| 3 | Bills | 120.00 | 5 | Electricity bill |
| 4 | Health | 35.99 | 8 | Pharmacy |
| 5 | Entertainment | 25.00 | 10 | Movie tickets |
| 6 | Shopping | 49.00 | 12 | Clothing |
| 7 | Other | 10.00 | 14 | Miscellaneous |
| 8 | Food | 32.75 | 16 | Dinner out |

- Sum of all 8 amounts: 346.24.
- Category totals: Bills 120.00, Food 78.25, Shopping 49.00, Health 35.99, Transport 28.00, Entertainment 25.00, Other 10.00.
- Day of month is applied to the current month and year, and formatted as YYYY-MM-DD.
- If a listed day is later than today's day of month, use today's date instead, so no seeded expense is dated in the future.

## 6. Changes to app.py

- Import `get_db`, `init_db`, `seed_db` from `database.db`.
- Call `init_db()` and `seed_db()` inside `app.app_context()` on startup.
- The database must be ready before any route is served.

## 7. Files to Change

- `database/db.py`
- `app.py`

## 8. Files to Create

- None.

## 9. Dependencies

- No new pip packages.
- Use `sqlite3` (standard library).
- Use `werkzeug.security` (already installed and listed in `requirements.txt`).

## 10. Categories (Fixed List)

These are the only valid values for `expenses.category`:

- Food
- Transport
- Bills
- Health
- Entertainment
- Shopping
- Other

## 11. Rules for Implementation

- No ORM, no SQLAlchemy.
- Parameterized queries only — never string formatting in SQL.
- `PRAGMA foreign_keys = ON` on every connection.
- Store `amount` as REAL, not INTEGER.
- Hash passwords with `generate_password_hash` from `werkzeug.security`.
- `seed_db()` must be idempotent (safe to call multiple times).
- Dates must always be YYYY-MM-DD.
- The YYYY-MM-DD rule applies to `expenses.date`. The `created_at` columns use SQLite's `CURRENT_TIMESTAMP` format (YYYY-MM-DD HH:MM:SS, UTC).

## 12. Expected Behavior

### Function behavior

| Function | When called correctly |
|---|---|
| `get_db()` | Returns an open connection to `spendly.db` in the project root; rows are accessible by column name; foreign key enforcement is active |
| `init_db()` | Creates `spendly.db` if missing and ensures both tables exist; repeated calls change nothing and raise no errors |
| `seed_db()` | On an empty `users` table, inserts the demo user and 8 expenses; on a non-empty `users` table, makes no changes |

### Database-level constraints

| Constraint | Enforced behavior |
|---|---|
| users.email UNIQUE | Two users cannot share the same email |
| users NOT NULL columns | name, email, password_hash cannot be NULL |
| expenses.user_id FOREIGN KEY | An expense cannot reference a non-existent user |
| expenses NOT NULL columns | user_id, amount, category, date cannot be NULL |
| expenses.category CHECK | Only the 7 fixed categories can be stored |
| expenses.date CHECK | Only zero-padded YYYY-MM-DD values can be stored (for example 2026-03-05, not 2026-3-5) |
| id AUTOINCREMENT | Primary keys are generated automatically and never reused |
| created_at DEFAULT | Populated automatically when not supplied |

## 13. Error Handling Expectations

| Scenario | Expected outcome |
|---|---|
| Insert a user with a duplicate email | UNIQUE constraint failure is raised |
| Insert an expense with an invalid `user_id` | Foreign key constraint failure is raised |
| Insert an expense with a category outside the fixed list | CHECK constraint failure is raised |
| Insert an expense with a date not in zero-padded YYYY-MM-DD form | CHECK constraint failure is raised |
| Invalid or malformed query | A clear error is raised (not silently swallowed) so the cause can be debugged |

## 14. Definition of Done

- [ ] Database file created on app startup
- [ ] Both tables exist with correct schema and constraints
- [ ] Demo user exists with hashed password
- [ ] 8 sample expenses exist across all 7 categories
- [ ] Seed expense amounts total exactly 346.24, with Bills as the highest-total category
- [ ] No seeded expense is dated later than today
- [ ] Category and date CHECK constraints reject invalid values
- [ ] No duplicate seed data on repeated runs
- [ ] App starts without errors
- [ ] Foreign key enforcement works
- [ ] All queries use parameterized SQL

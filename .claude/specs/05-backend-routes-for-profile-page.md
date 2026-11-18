# Spec: Step 05 — Backend Routes for Profile Page

## Overview

- Step 05 replaces all hardcoded data in the `/profile` route with live queries against the SQLite database.
- The profile page currently renders a static demo user, fixed summary stats, a hand-typed transaction list, and a hardcoded category breakdown.
- This step wires those four sections to real data so every logged-in user sees their own expenses.
- Three parallel subagents handle the three independent data concerns — transaction history, summary stats, and category breakdown — before being integrated into the single `/profile` route.

## Depends on

- Step 01 — Database setup (tables and `get_db()` exist; the seed data is the fixed 8-expense set totalling 346.24, with Bills as the highest category total)
- Step 02 — Registration (users are stored in the database)
- Step 03 — Login / Logout (`session["user_id"]` is set on login)
- Step 04 — Profile page static UI (template already renders all four sections)

## Routes

- No new routes.
- The existing `GET /profile` route is modified in place.

## Database changes

- No database changes.
- The `users` and `expenses` tables already have all required columns: `user_id`, `amount`, `category`, `date`, `description`, `created_at`.

## Templates

- Modify: `templates/profile.html`
  - Amounts must be rendered with the ₹ symbol (Indian Rupee) — never £ or $
  - All four dynamic sections are already present in the template — no structural changes needed, only the Jinja variables they consume are now real

## Files to change

- `app.py` — replace hardcoded data in the `profile()` view with calls to the new query helpers in `database/queries.py`
- `templates/profile.html` — confirm ₹ symbol is used for all currency display

## Files to create

- `database/queries.py` — pure query helpers with no Flask imports; one function per data concern:
  - `get_user_by_id(user_id)`
    - Returns a dict with `name`, `email`, `member_since`
  - `get_summary_stats(user_id)`
    - Returns a dict with `total_spent`, `transaction_count`, `top_category`
  - `get_recent_transactions(user_id, limit=10)`
    - Returns a list of dicts, each with `date`, `description`, `category`, `amount`
    - Ordered newest-first
  - `get_category_breakdown(user_id)`
    - Returns a list of dicts, each with `name`, `amount`, `pct`
    - `pct` is the percentage of total rounded to the nearest int
    - Ordered by amount descending
- `tests/test_backend_connection.py` — see Tests to write

## New dependencies

- None

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- `PRAGMA foreign_keys = ON` must be enabled on every connection (already handled in `get_db()`)
- Currency must always display as ₹ — never £ or $
- `member_since` must be derived from `users.created_at` and formatted as "Month YYYY" (e.g. "January 2026")
- `pct` values in category breakdown must sum to 100; use integer rounding and adjust the largest category to absorb any rounding remainder
- `top_category` is the category with the highest summed `amount` (not the single largest expense)
- Helpers return plain numbers (for example `0`); the template formats currency with the ₹ symbol and two decimal places (for example ₹0.00, ₹346.24)
- If `session["user_id"]` refers to a user that no longer exists (`get_user_by_id` returns `None`), the `/profile` view clears the session and redirects to `/login`
- If a user has no expenses, all helpers must return zeros and empty lists — never raise exceptions
- All helpers in `database/queries.py` must call `get_db()` internally and close the connection before returning
- Use CSS variables — never hardcode hex values
- No inline styles
- All templates extend `base.html`

## Tests to write

- File: `tests/test_backend_connection.py`
- Test setup:
  - Tests must use a temporary database created per test run (for example in a temp directory), never the real `spendly.db`
  - The temporary database is initialised with `init_db()` and `seed_db()` so the seed user exists
  - A second user with no expenses is created for the empty-state cases
- Unit tests:

| Function | Input | Expected output |
|---|---|---|
| `get_user_by_id` | Valid `user_id` | Dict with correct `name`, `email`, `member_since` |
| `get_user_by_id` | Non-existent id | `None` |
| `get_summary_stats` | `user_id` with expenses | Correct `total_spent`, `transaction_count`, `top_category` |
| `get_summary_stats` | `user_id` with no expenses | `{"total_spent": 0, "transaction_count": 0, "top_category": "—"}` |
| `get_recent_transactions` | `user_id` with expenses | List ordered newest-first; each item has `date`, `description`, `category`, `amount` |
| `get_recent_transactions` | `user_id` with no expenses | Empty list |
| `get_category_breakdown` | `user_id` with expenses | List ordered by amount descending; `pct` values are integers summing to 100 |
| `get_category_breakdown` | `user_id` with no expenses | Empty list |
| `get_category_breakdown` | `user_id` with three categories of equal total (each rounds to 33) | `pct` values sum to 100; the remainder is added to the largest category (34, 33, 33) |
| `get_summary_stats` | `user_id` with expenses in two categories where the single largest expense is in the category with the lower total | `top_category` is the category with the higher summed total |
| `get_user_by_id` | Seed user id | `member_since` is formatted "Month YYYY" (for example "November 2026") |

- Route tests:
  - `GET /profile` unauthenticated → redirects to `/login` (302)
  - `GET /profile` authenticated as seed user:
    - Returns 200
    - Response contains "Demo User"
    - Response contains "demo@spendly.com"
    - Response contains ₹ symbol
    - `total_spent` matches sum of all seed expenses (346.24)
    - `transaction_count` is 8
    - `top_category` is "Bills" (highest single-category total)
    - Transaction list appears in newest-first order
    - Category breakdown contains all 7 categories
  - `GET /profile` authenticated as a newly registered user with no expenses:
    - Returns 200
    - Response shows ₹0.00 total spent and 0 transactions
    - Category breakdown is empty
  - `GET /profile` authenticated with a `session["user_id"]` that does not exist in `users` → redirects to `/login` (302)

## Definition of done

- [ ] Logging in as `demo@spendly.com` / `demo123` shows "Demo User" and "demo@spendly.com" on the profile page — not the hardcoded strings
- [ ] Total spent displayed on the profile page equals ₹346.24
- [ ] Transaction count displayed is 8
- [ ] Top category displayed is "Bills"
- [ ] Transaction list shows 8 rows ordered newest date first
- [ ] Category breakdown shows 7 categories with percentages that add up to 100%
- [ ] All amounts on the page display the ₹ symbol
- [ ] Registering a brand-new user and visiting `/profile` shows ₹0.00 total spent, 0 transactions, and an empty category breakdown — no errors

# Step 05 Backend Routes for Profile Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded data in `/profile` with live per-user queries from SQLite.

**Architecture:** A new Flask-free module `database/queries.py` holds four helpers, each opening and closing its own `get_db()` connection. `profile()` calls them and passes the results to the existing template, which formats currency. A session pointing at a missing user is cleared and sent to `/login`.

**Tech Stack:** Flask 3.1.3, `sqlite3`, Jinja2, pytest.

**Spec:** `.claude/specs/05-backend-routes-for-profile-page.md`

## State of the project (from `spendly.db` and the code)

- `spendly.db`: one user (Demo User, created 2026-11-18, so `member_since` is "November 2026"); 8 expenses totalling 346.24; category totals Bills 120.00, Food 78.25, Shopping 49.00, Health 35.99, Transport 28.00, Entertainment 25.00, Other 10.00.
- `app.py` has `PROFILE_USER`, `PROFILE_STATS`, `PROFILE_EXPENSES`, `PROFILE_CATEGORIES` constants and a `profile()` view that passes them.
- `profile.html` expects `user.initials`, string amounts, and `cat.percent`. The spec's helper keys differ (`pct`, numeric amounts, no initials), so the template and view change.
- `tests/test_profile.py::test_profile_data_matches_seed` reads the `PROFILE_*` constants and becomes obsolete.
- The spec describes three parallel subagents; this plan builds the four helpers directly, since they are small and independent files of the same module.

## Global Constraints

- Raw `sqlite3` via `get_db()`; parameterised queries only; every helper closes its connection.
- Helpers return plain numbers (e.g. `0`); the template formats ₹ with two decimals (₹0.00, ₹346.24).
- `member_since` is "Month YYYY" from `users.created_at`.
- `pct` values are ints that sum to 100; the remainder goes to the largest category.
- `top_category` is the highest summed category (not the largest single expense); "—" when no expenses.
- Empty user: zeros and empty lists, never an exception.
- Missing session user: clear the session, redirect to `/login`.
- ₹ only; CSS variables only; no inline styles; templates extend `base.html`.

## Review Focus

- Two expenses on the same date must still sort deterministically (newest id first). (Task 1)
- An expense with a NULL description must render as "—", not the text "None". (Task 2)
- Amounts such as 0.1 + 0.2 must be rounded to two decimals so totals never show 0.30000000000000004. (Task 1)
- Another user's expenses must never appear in a user's totals, list or breakdown. (Task 1)
- A description containing HTML must be escaped on the profile page. (Task 2)

## File Structure

- Create: `database/queries.py`, `tests/test_backend_connection.py`
- Modify: `app.py` (drop the `PROFILE_*` constants, rewrite `profile()`), `templates/profile.html`, `tests/test_profile.py` (remove the obsolete seed-constants test)

---

### Task 1: Query helpers

**Files:** Create `database/queries.py`, `tests/test_backend_connection.py`

**Interfaces:**
- Produces:
  - `get_user_by_id(user_id: int) -> dict | None` with `name`, `email`, `member_since`
  - `get_summary_stats(user_id: int) -> dict` with `total_spent: float`, `transaction_count: int`, `top_category: str`
  - `get_recent_transactions(user_id: int, limit: int = 10) -> list[dict]` with `date`, `description`, `category`, `amount`
  - `get_category_breakdown(user_id: int) -> list[dict]` with `name`, `amount: float`, `pct: int`

- [ ] **Step 1: Write failing tests** in `tests/test_backend_connection.py` (use `db_path`, `db.init_db()`, `db.seed_db()`; a helper `add_expense(user_id, category, amount, date, description=None)`; a second user from `db.create_user` with no expenses):
  - `test_get_user_by_id_valid`: seed user gives `name == "Demo User"`, `email == "demo@spendly.com"`, and `member_since` matching `^[A-Z][a-z]+ \d{4}$`.
  - `test_get_user_by_id_missing`: `None` for 999.
  - `test_member_since_format`: insert a user with `created_at = '2026-01-15 09:00:00'`; result is "January 2026".
  - `test_summary_stats_seed`: `total_spent == 346.24`, `transaction_count == 8`, `top_category == "Bills"`.
  - `test_summary_stats_empty`: equals `{"total_spent": 0, "transaction_count": 0, "top_category": "—"}`.
  - `test_top_category_uses_sum_not_single_expense`: user with Food 100 (one expense) and Bills 60 + 60 gives "Bills".
  - `test_amounts_rounded_to_two_decimals`: expenses 0.1 and 0.2 give `total_spent == 0.3` exactly.
  - `test_recent_transactions_order_and_keys`: seed user gives 8 items newest first (first is "Dinner out"); each has exactly `date`, `description`, `category`, `amount`.
  - `test_recent_transactions_same_date_newest_id_first`: two expenses on one date; the later insert comes first.
  - `test_recent_transactions_limit`: `limit=3` returns 3; default limit is 10 (add 12 expenses, get 10).
  - `test_recent_transactions_empty`: `[]`.
  - `test_category_breakdown_seed`: 7 items ordered by amount descending (Bills first); `pct` are ints summing to 100.
  - `test_category_breakdown_empty`: `[]`.
  - `test_category_breakdown_equal_thirds`: three categories of 10.00 give pcts `[34, 33, 33]`.
  - `test_helpers_scope_to_user`: another user's expenses never change the seed user's stats, list or breakdown, and the second user's own data is separate.
- [ ] **Step 2: Run** `python -m pytest tests/test_backend_connection.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement** the four helpers in `database/queries.py` (imports `get_db` from `database.db`; no Flask imports). Approach: `SELECT ... WHERE user_id = ?`; totals via `SUM(amount)` grouped by category, rounded with `round(x, 2)`; ordering `ORDER BY date DESC, id DESC` for transactions and `total DESC, category ASC` for the breakdown; `pct = round(amount / total * 100)` then add `100 - sum(pcts)` to the first (largest) item; `member_since` via `datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%B %Y")`.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: add profile query helpers`

### Task 2: Wire the profile view and template

**Files:** Modify `app.py`, `templates/profile.html`, `tests/test_backend_connection.py`, `tests/test_profile.py`

**Interfaces:**
- Consumes: the four helpers
- Produces: `profile()` passing `user` (helper dict plus `initials` computed in the view from the name: first letters of the first two words, upper-cased), `stats`, `expenses`, `categories`.

- [ ] **Step 1: Write failing route tests** (`client` fixture; `login_session` sets `session["user_id"]`):
  - `test_profile_unauthenticated_redirects`: 302 to `/login`.
  - `test_profile_seed_user_live_data`: 200; contains "Demo User", "demo@spendly.com", `₹346.24`, ">8<" in the Transactions tile, "Bills" in the Top category tile; the table body has 8 rows with "Dinner out" before "Groceries"; the breakdown lists all 7 categories and the `<progress>` values sum to 100.
  - `test_profile_new_user_empty_state`: register a user through `db.create_user`, set the session to that id; 200; contains `₹0.00`, a Transactions tile of 0, "—" as top category, no `<progress` element, and no exception.
  - `test_profile_unknown_session_user`: `session["user_id"] = 999` gives 302 to `/login`, and the session no longer has `user_id`.
  - `test_profile_shows_only_own_data`: add an expense for another user; the seed user's page total is unchanged.
  - `test_profile_null_description_and_html_escaped`: expenses with `description=None` and `"<b>x</b>"`; the page shows "—" and `&lt;b&gt;`, never "None" or `<b>x`.
  - `test_profile_initials`: new user "Asha Rao" shows "AR"; single-word name "Asha" shows "A".
  - Update the Step 04 tests in `tests/test_profile.py` that still apply (user card, stats, transactions, breakdown, currency, no inline styles); delete `test_profile_data_matches_seed`.
- [ ] **Step 2: Run** `python -m pytest -v`. Expected: new route tests FAIL.
- [ ] **Step 3: Implement.**
  - `app.py`: remove the four `PROFILE_*` constants; import the helpers from `database.queries`; `profile()`: guard on `session.get("user_id")`; `user = get_user_by_id(...)`; if `None`, `session.clear()` and redirect to `url_for("login")`; add `initials`; pass the other three helper results.
  - `templates/profile.html`: currency as `₹{{ "%.2f"|format(value) }}` for the total, each transaction and each category; `cat.pct` in place of `cat.percent`; `tx.description or "—"`; wrap the breakdown list in `{% if categories %}` with a short empty message when there are none; show the raw `YYYY-MM-DD` date.
- [ ] **Step 4: Run** `python -m pytest -v`. Expected: all PASS.
- [ ] **Step 5: Manual check:** run `python app.py` (set `SECRET_KEY`), sign in as the demo user and check the page, then register a new user and check the empty state.
- [ ] **Step 6: Commit** `feat: wire profile page to live data`

## Self-Review

- Spec coverage: four helpers, view rewiring, ₹ formatting, `member_since`, pct remainder rule, top-category rule, empty state, missing-user handling, temporary test database, and all 8 Definition of Done items map to Tasks 1-2.
- Names consistent: `pct` (not `percent`), `member_since`, `initials` added in the view only.
- Spec deviations: the three-subagent instruction is not followed (done inline); `initials` is derived in the view because the template needs it and the spec's helper dict has no such key; the dates shown are the raw stored `YYYY-MM-DD`, not "16 Nov 2026".

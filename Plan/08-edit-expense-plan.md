# Step 08 Edit Expense Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a logged-in user edit one of their own expenses at `/expenses/<id>/edit`, with an "Edit" link on each profile row.

**Architecture:** `get_expense_by_id` and `update_expense` join `database/queries.py`, both scoped to `id = ? AND user_id = ?`. `get_recent_transactions` also returns `id`. The Step 07 validation moves into one shared helper in `app.py` so add and edit cannot drift apart. The edit view checks ownership first (404), then validates, updates, and redirects to `/profile`.

**Tech Stack:** Flask 3.1.3, Jinja2, `sqlite3`, pytest.

**Spec:** `.claude/specs/08-edit-expense.md`

## State of the project (from `spendly.db` and the code)

- `spendly.db`: the demo user with 8 expenses (ids 1 to 8, newest id 8 "Dinner out"); there is no second user, so ownership tests create one in the temp database.
- `/expenses/<int:id>/edit` is a GET-only stub. The Step 07 validation is inline inside `add_expense()`.
- `get_recent_transactions(user_id, limit=10)` returns `date`, `description`, `category`, `amount` only. `profile.html` has no "Actions" column.
- **Step 06 is not built.** The spec says to keep the Step 06 signature `get_recent_transactions(user_id, limit=10, date_from=None, date_to=None)`. That signature does not exist yet, so this plan keeps the current signature and skips the Step 06 test row and Definition of Done item. Adding the date parameters belongs to Step 06.
- `tests/test_backend_connection.py::test_recent_transactions_order_and_keys` asserts the exact key set and must be updated to include `id`.

## Global Constraints

- Raw `sqlite3` via `get_db()`; parameterised queries only.
- `get_expense_by_id` and `update_expense` both scope to `id = ? AND user_id = ?`.
- Unauthenticated GET and POST redirect to `/login`, checked before any lookup.
- A missing expense or another user's expense returns 404 (also for POST, before validation).
- Validation is identical to Step 07: finite amount > 0 and <= 9999999.99 rounded to two decimals; one of the 7 categories; valid `YYYY-MM-DD` saved zero-padded; description stripped, `None` if blank, at most 200 characters.
- On error, re-render (200) with the submitted values; on success redirect to `url_for("profile")` (unfiltered).
- `update_expense` returns the rows changed; 0 means 404.
- ₹ only; CSS variables only; no inline styles; templates extend `base.html`; `url_for()` for all links.

## Review Focus

- A POST to another user's expense with invalid data must return 404, not a validation error that confirms the id exists. (Task 2)
- A failed validation or another user's POST must leave the row's amount, category, date and description unchanged. (Task 2)
- A huge id (`/expenses/99999999999999999999/edit`) must not cause a 500. (Task 2)
- Editing must not create a second row or change `user_id`/`created_at`. (Task 1)
- Clearing the description must store NULL, and the edit form for a NULL description must show an empty field, not "None". (Task 2)

## File Structure

- Modify: `database/queries.py` (`get_expense_by_id`, `update_expense`, `id` in `get_recent_transactions`)
- Modify: `app.py` (shared validator, `add_expense` uses it, new `edit_expense`)
- Create: `templates/edit_expense.html`
- Modify: `templates/profile.html` ("Actions" column and "Edit" link)
- Modify: `tests/test_backend_connection.py` (key set now includes `id`)
- Create: `tests/test_edit_expense.py`

---

### Task 1: Query helpers

**Files:** Modify `database/queries.py`, `tests/test_backend_connection.py`; Create `tests/test_edit_expense.py`

**Interfaces:**
- Produces:
  - `get_expense_by_id(expense_id: int, user_id: int) -> dict | None` with `id`, `user_id`, `amount`, `category`, `date`, `description`
  - `update_expense(expense_id: int, user_id: int, amount: float, category: str, date: str, description: str | None) -> int` (rows changed, 0 or 1)
  - `get_recent_transactions(...)` items now also include `id`

- [ ] **Step 1: Write failing tests** (`db_path`; `init_db()`, `seed_db()`; a second user from `db.create_user` with one expense via `queries.insert_expense`):
  - `test_get_expense_by_id_owner`: expense 1 for user 1 returns a dict with the seed values (Food, 45.5, "2026-11-01", "Groceries").
  - `test_get_expense_by_id_wrong_user`: `None`.
  - `test_get_expense_by_id_missing`: `None` for 999.
  - `test_update_expense_updates_row`: `update_expense(1, 1, 99.0, "Bills", "2026-02-02", None)` changes the row (amount 99.0, category Bills, date, description NULL) and returns 1; `user_id` and `created_at` unchanged; row count unchanged.
  - `test_update_expense_wrong_user`: returns 0 and the row is unchanged.
  - `test_update_expense_missing`: returns 0, no error.
  - `test_recent_transactions_include_id`: each item has `id` alongside `date`, `description`, `category`, `amount`; update the existing exact-key test to expect `id` too.
- [ ] **Step 2: Run** `python -m pytest tests/test_edit_expense.py tests/test_backend_connection.py -v`. Expected: new tests FAIL.
- [ ] **Step 3: Implement** the two helpers (`?` placeholders, WHERE `id = ? AND user_id = ?`, commit, close in `finally`; `update_expense` returns `cursor.rowcount`) and add `id` to the SELECT and returned dicts of `get_recent_transactions`.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: add expense lookup and update helpers`

### Task 2: Edit route, template and profile link

**Files:** Modify `app.py`, `templates/profile.html`, `tests/test_edit_expense.py`; Create `templates/edit_expense.html`

**Interfaces:**
- Consumes: `get_expense_by_id`, `update_expense`, `db.CATEGORIES`
- Produces: `_validate_expense_form(form: dict) -> tuple[str | None, float | None, str | None]` returning `(error, amount, iso_date)`; `edit_expense(id)` for `GET`, `POST`; template context `form`, `categories`, `expense_id`.

- [ ] **Step 1: Write failing tests** (`client`; helpers `login_session(client, uid)`, `row(id)` reading the DB, `post(client, id, **overrides)` with defaults `amount="99.0"`, `category="Bills"`, `date="2026-02-02"`, `description="Updated"`; other user created with `db.create_user` and one expense):
  - `test_get_unauthenticated_redirects` and `test_post_unauthenticated_redirects`: 302 to `/login`; the POST changes nothing (also for a non-existent id).
  - `test_get_own_expense_prefilled`: 200; the body contains `value="45.50"`, `value="2026-11-01"`, `value="Groceries"`, `<option value="Food" selected`, `action="/expenses/1/edit"`, "Save Changes", and a cancel link to `/profile`.
  - `test_get_other_users_expense_404`, `test_get_missing_expense_404`, `test_post_other_users_expense_404`, `test_post_missing_expense_404`.
  - `test_post_other_users_expense_unchanged`: after a 404 POST, the other user's row has its original amount, category, date and description.
  - `test_post_other_user_invalid_data_still_404`: invalid amount on another user's expense gives 404, not 200.
  - `test_valid_post_updates_and_redirects`: 302 to `/profile`; the row has the new values; `GET /profile` shows "Updated" and amounts with ₹.
  - `test_no_description_stores_null`; `test_whitespace_description_stores_null`.
  - `test_error_cases` (parametrised, same list as Step 07: missing/zero/negative/non-numeric/`inf`/`nan`/`1e999`/too large amount, bad and lower-case category, bad and blank date, 201-character description): 200, `class="auth-error"` in the body, and the row unchanged.
  - `test_failure_repopulates_submitted_values`: an invalid amount `abc` with category Health, date `2026-04-01`, description "Doctor" shows those submitted values, not the originals.
  - `test_date_zero_padded_and_amount_rounded`: `"2026-3-5"` stores `2026-03-05`; `"12.345"` stores 12.35.
  - `test_update_returning_zero_gives_404`: monkeypatch `app.update_expense` to return 0; the POST returns 404.
  - `test_null_description_shows_empty_field`: an expense with a NULL description renders `value=""` and never "None".
  - `test_huge_id_does_not_500`: `GET /expenses/99999999999999999999/edit` while logged in returns 404.
  - `test_html_escaped_on_edit_form`: description `<script>x</script>` with an invalid amount shows `&lt;script&gt;`.
  - `test_unsupported_method_405`: `DELETE /expenses/1/edit` returns 405.
  - `test_profile_has_edit_links_and_actions_header`: `GET /profile` has an "Actions" header and, for each of the 8 rows, a link `href="/expenses/<id>/edit"` with the text "Edit".
  - `test_add_expense_still_validates`: a quick regression that `POST /expenses/add` with amount `inf` still returns 200 with an error (the shared validator).
- [ ] **Step 2: Run** `python -m pytest tests/test_edit_expense.py -v`. Expected: new tests FAIL.
- [ ] **Step 3: Implement.**
  - `app.py`: move the Step 07 validation into `_validate_expense_form(form)` (same messages and order) and make `add_expense` call it. `edit_expense(id)` with `methods=["GET", "POST"]`: no session user → redirect to `/login`; `get_expense_by_id(id, user_id)` is `None` → `abort(404)`; GET renders `edit_expense.html` with `form` built from the row (amount as `"%.2f"`, description `or ""`); POST builds `form` like Step 07, validates, flashes the error and re-renders on failure, otherwise calls `update_expense`, `abort(404)` if it returns 0, and redirects to `url_for("profile")`.
  - `templates/edit_expense.html`: same layout and fields as `add_expense.html`; the form action is `url_for('edit_expense', id=expense_id)`; "Save Changes" button; cancel link to `url_for('profile')`.
  - `templates/profile.html`: add an "Actions" `<th>` and, per row, an `<td>` with an "Edit" link to `url_for('edit_expense', id=tx.id)`.
- [ ] **Step 4: Run** `python -m pytest -v`. Expected: all PASS (Steps 01 to 07 included).
- [ ] **Step 5: Manual check:** run `python app.py` (set `SECRET_KEY`), sign in as the demo user, click "Edit" on a row, change a value and save, then try an invalid amount; restore the original values afterwards.
- [ ] **Step 6: Commit** `feat: implement edit expense`

## Self-Review

- Spec coverage: routes, both helpers, the `id` column, templates, ownership 404s, validation parity, update row-count rule, redirect rule, reachability note (only rows on the profile list have links), temporary test database, and the Definition of Done items map to Tasks 1-2, except the Step 06 items.
- Names consistent: `get_expense_by_id`, `update_expense`, `_validate_expense_form`, `expense_id`.
- Spec deviations: Step 06's `date_from`/`date_to` parameters and their test and Definition of Done item are skipped because Step 06 is not built. The Step 07 validation is refactored into one helper (the spec says "identical", so sharing it is the safest way to keep them so).
- Not done (outside the spec): no pagination for expenses beyond the 10 newest, no CSRF protection.

# Step 09 Delete Expense Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a logged-in user permanently delete one of their own expenses from the profile table, with a browser confirmation, a POST-only route and a success flash.

**Architecture:** `delete_expense(expense_id, user_id)` joins `database/queries.py` and deletes with `WHERE id = ? AND user_id = ?`, returning the rows deleted. The existing `/expenses/<id>/delete` stub becomes a POST-only view: guard, ownership lookup (404), delete (404 if 0 rows), flash, redirect. Each profile row gets a small delete form next to the Edit link.

**Tech Stack:** Flask 3.1.3, Jinja2, `sqlite3`, pytest.

**Spec:** `.claude/specs/09-delete-expense.md`

## State of the project (from the code and `spendly.db`)

- `spendly.db` holds the demo user and 8 expenses (ids 1 to 8, total 346.24); it is not touched. Tests build their own temporary databases.
- `/expenses/<int:id>/delete` is a GET-only stub. The Actions column and the Edit link exist (Step 08), `get_expense_by_id` exists, and the flash block on `profile.html` exists (Step 06).
- `style.css` already defines `--danger` and `--danger-light`, so no new colour variable is needed.
- **Name clash:** the spec asks `app.py` to import `delete_expense` from `database.queries`, but the Flask view function is also called `delete_expense` (and its endpoint name is used by `url_for`). The helper is therefore imported under an alias, `delete_expense_record`, and the view keeps the name `delete_expense`. The helper keeps its spec name in `queries.py`.

## Global Constraints

- Raw `sqlite3`; parameterised queries only; connection closed before returning.
- `delete_expense` scopes to `id = ? AND user_id = ?` and returns the rows deleted (0 or 1).
- The route accepts POST only; a GET (and any other method) returns 405.
- Logged out redirects to `/login` (302), checked before any lookup; a missing or foreign expense returns 404; a delete affecting 0 rows returns 404.
- On success flash "Expense deleted." (category `success`) and redirect to `url_for("profile")` (unfiltered); never render a template.
- No inline `style` attributes anywhere in `profile.html`; the form uses the `inline-form` class.
- The delete button uses `btn-delete` with a danger CSS variable, defined in `style.css`.
- The confirmation is client-side only (`onsubmit="return confirm('Delete this expense?')"`); with JavaScript off it submits without a dialog, which is accepted.
- ₹ only; CSS variables only; templates extend `base.html`; `url_for()` for all links.

## Review Focus

- A second POST to the same id after a successful delete must return 404 and must not flash a second success. (Task 2)
- Deleting must not touch the user's other rows or any other user's rows, even with the same dates and amounts. (Task 1)
- `PUT`, `PATCH` and `DELETE` on the URL must return 405, and a logged-out GET must also not run a delete. (Task 2)
- A huge id (`/expenses/99999999999999999999/delete`) must give 404 for a logged-in user, never a 500. (Task 2)
- The page must contain one delete form per row, each pointing at its own row's id, so a click cannot delete the neighbouring row. (Task 2)

## File Structure

- Modify: `database/queries.py` (add `delete_expense`)
- Modify: `app.py` (import alias, POST-only view)
- Modify: `templates/profile.html` (delete form in the Actions cell)
- Modify: `static/css/style.css` (`.btn-delete`, `.inline-form`)
- Create: `tests/test_delete_expense.py`

---

### Task 1: `delete_expense` helper

**Files:** Modify `database/queries.py`; Create `tests/test_delete_expense.py`

**Interfaces:**
- Produces: `delete_expense(expense_id: int, user_id: int) -> int` (rows deleted, 0 or 1)

- [ ] **Step 1: Write failing tests** (`db_path`; `init_db()`, `seed_db()`; a second user with one expense):
  - `test_delete_own_row_removed_returns_1`: `delete_expense(1, 1)` returns 1 and the row no longer exists.
  - `test_delete_leaves_other_rows`: after deleting expense 1, the user's other 7 rows and the other user's row remain.
  - `test_delete_wrong_user_returns_0`: the other user's expense id with user 1 returns 0 and the row remains.
  - `test_delete_missing_returns_0`: id 999 returns 0 with no error and the row count is unchanged.
- [ ] **Step 2: Run** `python -m pytest tests/test_delete_expense.py -v`. Expected: FAIL (`AttributeError`).
- [ ] **Step 3: Implement** `delete_expense` with a `?`-parameterised `DELETE`, commit, return `cursor.rowcount`, close in `finally`.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: add delete_expense helper`

### Task 2: Delete route, form and styles

**Files:** Modify `app.py`, `templates/profile.html`, `static/css/style.css`, `tests/test_delete_expense.py`

**Interfaces:**
- Consumes: `get_expense_by_id`, `delete_expense` (imported into `app.py` as `delete_expense_record`)
- Produces: view `delete_expense(id)` for `POST` only

- [ ] **Step 1: Write failing route tests** (`client`; a second user with one expense; login by setting the session):
  - `test_post_unauthenticated_redirects`: 302 to `/login` (for an existing and a non-existent id); nothing is deleted.
  - `test_post_own_expense_deletes_and_redirects`: 302 to `/profile`; the row is gone from the database.
  - `test_flash_shown_after_redirect`: posting with `follow_redirects=True` shows "Expense deleted." and the profile has 7 rows.
  - `test_post_other_users_expense_404_row_remains`.
  - `test_post_missing_expense_404`; `test_huge_id_404`.
  - `test_get_returns_405`: logged in and logged out both get 405, and the row remains.
  - `test_other_methods_405`: `PUT`, `PATCH` and `DELETE` return 405.
  - `test_double_delete_second_404_no_second_flash`: after one delete, the same POST returns 404; a following `GET /profile` has no "Expense deleted." text (the flash was consumed).
  - `test_zero_rows_deleted_returns_404`: monkeypatch `app.delete_expense_record` to return 0; the POST returns 404 and no success flash is queued (a later `GET /profile` has no "Expense deleted.").
  - `test_profile_has_delete_form_per_row`: for each of the 8 expense ids the page has a `<form` with `method="POST"`, `action="/expenses/<id>/delete"`, class `inline-form`, an `onsubmit` containing `confirm(`, and a button with class `btn-delete` and the text "Delete"; the "Edit" links are still present (8).
  - `test_profile_no_style_attributes`: no `style=` in the profile page.
  - `test_css_defines_btn_delete_and_inline_form_with_variable`: `static/css/style.css` contains `.btn-delete` using `var(--danger` and contains `.inline-form`; the `--danger` variable is defined in `:root`.
  - `test_delete_keeps_other_users_rows`: after a delete, the other user's expense still exists and the user's other expenses are unchanged.
- [ ] **Step 2: Run** `python -m pytest tests/test_delete_expense.py -v`. Expected: new tests FAIL.
- [ ] **Step 3: Implement.**
  - `app.py`: import `delete_expense as delete_expense_record`; replace the stub with `@app.route("/expenses/<int:id>/delete", methods=["POST"])` and `def delete_expense(id)`: no session user → redirect to `/login`; `get_expense_by_id(id, user_id)` is `None` → `abort(404)`; `delete_expense_record(id, user_id) == 0` → `abort(404)`; `flash("Expense deleted.", "success")`; `redirect(url_for("profile"))`.
  - `templates/profile.html`: inside the Actions cell, after the Edit link, a `<form method="POST" action="{{ url_for('delete_expense', id=tx.id) }}" class="inline-form" onsubmit="return confirm('Delete this expense?')">` with `<button type="submit" class="btn-delete">Delete</button>`.
  - `static/css/style.css`: `.inline-form { display: inline; }` and a `.btn-delete` rule (no border, transparent background, `var(--danger)` text, pointer cursor, `var(--font-body)`; hover uses `var(--danger-light)` background).
- [ ] **Step 4: Run** `python -m pytest -v`. Expected: all PASS (Steps 01 to 08 included).
- [ ] **Step 5: Manual check (cannot be automated without a browser):** run `python app.py` (set `SECRET_KEY`), add a throwaway expense, click "Delete", cancel the dialog (nothing happens), click again and confirm (row removed, "Expense deleted." shown).
- [ ] **Step 6: Commit** `feat: implement delete expense`

## Self-Review

- Spec coverage: POST-only route and 405, ownership guard and 404s, 0-row 404, flash and redirect, delete form with the `inline-form` class and confirm, `btn-delete` with a danger variable, no inline styles, unit and route tests, temporary test database, and all 11 Definition of Done items map to Tasks 1-2 (the confirm-dialog items are covered by the manual step).
- Names consistent: `delete_expense` (helper in `queries.py`, view in `app.py`), alias `delete_expense_record` in `app.py`.
- Spec deviation: the helper is imported under an alias because the view function has the same name; the spec's "Import `delete_expense`" is met in substance.
- Not done (outside the spec): no CSRF protection on this destructive POST, no undo, the filter is lost after deleting, and with JavaScript disabled there is no confirmation.

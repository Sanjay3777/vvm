# Spec: Step 08 — Edit Expense

## Overview

- Step 08 lets a logged-in user edit any of their own expenses via a pre-populated form at `/expenses/<id>/edit`.
- The GET handler loads the existing expense from the database and renders the form with its current values.
- The POST handler validates the submission and updates the row in place.
- Ownership is enforced: a user can only edit expenses that belong to them.
- Two new query helpers are added to `database/queries.py`: `get_expense_by_id` and `update_expense`.
- The transactions table in `profile.html` gains an "Edit" action link per row, which requires `get_recent_transactions` to also return the expense id.

## Depends on

- Step 01 — Database setup (`expenses` table exists with all required columns)
- Step 03 — Login / Logout (`session["user_id"]` is set and enforced)
- Step 05 — Profile page renders transactions (the edit link lives there)
- Step 06 — Date-range filter (`get_recent_transactions` now takes `date_from` and `date_to`; this step must not break that)
- Step 07 — Add Expense (establishes the form pattern this step follows)

## Routes

- `GET /expenses/<int:id>/edit` — render edit form pre-populated with existing expense values — logged-in only
- `POST /expenses/<int:id>/edit` — validate and save updated expense — logged-in only

## Database changes

- No new tables or columns.
- All required columns already exist in `expenses`: `id`, `user_id`, `amount`, `category`, `date`, `description`.

## Templates

- Create: `templates/edit_expense.html`
  - Extends `base.html`
  - Form with `method="POST"` and its action generated with `url_for()` for the edit route using the expense id
  - Fields (identical to `add_expense.html`, all pre-filled with current values):
    - `amount` — number input, `step="0.01"`, `min="0.01"`, required, pre-filled
    - `category` — `<select>` with exactly 7 fixed options, pre-selected to current value
    - `date` — `<input type="date">`, required, pre-filled to current value
    - `description` — text input, optional, max 200 chars, pre-filled
  - Submit button labelled "Save Changes" and a cancel link back to the profile page (via `url_for`)
  - Error message block that re-populates submitted (not original) values on validation failure
- Modify: `templates/profile.html`
  - Add an "Actions" column header to the transactions table `<thead>`
  - Add an "Edit" link cell per row pointing to the edit route for that transaction's id (via `url_for`)

## Files to change

- `database/queries.py`
  - Add `get_expense_by_id(expense_id, user_id)`
    - Fetches a single expense row only if it belongs to the given user
    - Returns `None` if not found or if `user_id` does not match
    - Query must scope to `id = ? AND user_id = ?`
  - Add `update_expense(expense_id, user_id, amount, category, date, description)`
    - Issues a parameterised UPDATE scoped to `id = ? AND user_id = ?` for ownership safety
    - Returns the number of rows changed (0 or 1)
  - Modify `get_recent_transactions`
    - Add `id` to the SELECT column list so templates can build edit links
    - Keep the Step 06 signature `get_recent_transactions(user_id, limit=10, date_from=None, date_to=None)` and its filtering, ordering and limit behaviour unchanged
- `app.py`
  - Import `get_expense_by_id` and `update_expense` from `database.queries`
  - Replace the GET-only placeholder at `/expenses/<int:id>/edit` with a full GET + POST handler:
    - GET: call `get_expense_by_id`; return 404 if not found or not owned; render `edit_expense.html` with `expense` and categories list
    - POST: read form fields, validate (same rules as Step 07), call `update_expense`, redirect to `url_for("profile")` on success; re-render form with errors otherwise
    - The route must accept both GET and POST methods
- `templates/profile.html`
  - Add an "Actions" `<th>` to the table header
  - Add an "Edit" link cell per transaction row

## Files to create

- `templates/edit_expense.html`
- `tests/test_edit_expense.py` — see Tests to write

## New dependencies

- None

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- `PRAGMA foreign_keys = ON` must be enabled on every connection (already handled in `get_db()`)
- `get_expense_by_id` must scope its query to `id = ? AND user_id = ?` — return `None` if not found or if ownership check fails
- `update_expense` must also include `user_id = ?` in its WHERE clause as a second ownership guard
- Unauthenticated access to both GET and POST must redirect to `/login` (checked before any expense lookup)
- If the expense does not exist or belongs to another user, return 404
- Validation rules for POST (identical to Step 07 add expense):
  - 1. `amount`: required; strip whitespace; parse with `float()`, catch `ValueError`; must be finite (reject `inf` and `nan`), greater than 0 and at most 9999999.99; round to two decimal places before saving
  - 2. `category`: required; must be one of the 7 fixed categories (exact match); reject anything else
  - 3. `date`: required; must be a valid `YYYY-MM-DD` date; parse with `datetime.strptime`, then store the parsed date re-formatted as zero-padded `YYYY-MM-DD`
  - 4. `description`: optional; strip whitespace; store `None` if blank; reject with an error if longer than 200 characters (enforced on the server)
- On any validation error, re-render the form with the error message and the submitted (not original) values pre-filled
- If `update_expense` returns 0 rows changed (for example the expense was deleted after the ownership check), return 404 instead of redirecting as if it succeeded
- After a successful update, redirect to `url_for("profile")` — do NOT render the form again
  - The redirect goes to the unfiltered `/profile`; any active Step 06 filter is not preserved
- Reachability: the "Edit" link appears only on rows shown in the profile list (the 10 newest within the active filter). Older expenses are reached by narrowing the Step 06 date filter; no pagination is added in this step.
- Currency must always display as ₹ — never £ or $
- Use CSS variables — never hardcode hex values
- No inline styles
- All templates extend `base.html`
- Use `url_for()` for every internal link — never hardcode paths

## Tests to write

- File: `tests/test_edit_expense.py`
- Test setup: use a temporary database per test run (never the real `spendly.db`), initialised with `init_db()` and `seed_db()`; create a second user with their own expense for the ownership cases
- Unit tests:

| Function | Input | Expected output |
|---|---|---|
| `get_expense_by_id` | Valid `expense_id` and correct `user_id` | Returns the matching row as a dict-like object |
| `get_expense_by_id` | Valid `expense_id` and wrong `user_id` | Returns `None` |
| `get_expense_by_id` | Non-existent `expense_id` | Returns `None` |
| `update_expense` | Valid `expense_id`, correct `user_id`, new `amount=99.0` | Row in DB reflects updated amount |
| `update_expense` | Valid `expense_id`, wrong `user_id` | Row in DB unchanged (0 rows affected, no error raised) |
| `update_expense` | Valid `expense_id`, correct `user_id` | Returns 1 |
| `update_expense` | Valid `expense_id`, wrong `user_id` | Returns 0 |
| `get_recent_transactions` | `user_id` with expenses | Each item includes `id` alongside `date`, `description`, `category`, `amount` |
| `get_recent_transactions` | `user_id`, with `date_from` and `date_to` | Still filters, orders newest-first and applies the limit as in Step 06 |

- Route tests:
  - `GET /expenses/<id>/edit` unauthenticated → redirects to `/login` (302)
  - `GET /expenses/<id>/edit` authenticated, own expense → returns 200; response contains form pre-filled with current values; `<select>` has correct category pre-selected
  - `GET /expenses/<id>/edit` authenticated, other user's expense → returns 404
  - `GET /expenses/<id>/edit` authenticated, non-existent id → returns 404
  - `POST /expenses/<id>/edit` unauthenticated → redirects to `/login` (302)
  - `POST /expenses/<id>/edit` authenticated, valid data → redirects to `/profile` (302); updated values reflected in the database
  - `POST /expenses/<id>/edit` authenticated, other user's expense → returns 404
  - `POST /expenses/<id>/edit` authenticated, missing amount → returns 200; response contains an error message
  - `POST /expenses/<id>/edit` authenticated, `amount = 0` → returns 200; response contains an error message
  - `POST /expenses/<id>/edit` authenticated, non-numeric amount → returns 200; response contains an error message
  - `POST /expenses/<id>/edit` authenticated, invalid category → returns 200; response contains an error message
  - `POST /expenses/<id>/edit` authenticated, invalid date string → returns 200; response contains an error message
  - `POST /expenses/<id>/edit` authenticated, no description → redirects to `/profile` (302); row updated with `description = NULL`
  - `POST /expenses/<id>/edit` authenticated, other user's expense → returns 404; that row's amount, category, date and description are unchanged
  - `POST /expenses/<id>/edit` authenticated, validation failure → response re-populates the submitted (not original) amount, category, date and description
  - `POST /expenses/<id>/edit` authenticated, `amount = inf`, amount above 9999999.99, or description over 200 characters → returns 200; response contains an error message; row unchanged
  - `POST /expenses/<id>/edit` authenticated, `date = 2026-3-5` → redirects to `/profile` (302); stored date is `2026-03-05`
  - `POST /expenses/<id>/edit` where the expense is deleted after the ownership check (update affects 0 rows) → returns 404
  - `GET /profile` authenticated → each transaction row contains an "Edit" link whose URL matches that expense's edit route; the page contains an "Actions" column header
  - `GET /profile` after an edit → amounts display with the ₹ symbol

## Definition of done

- [ ] Visiting `/expenses/<id>/edit` while logged out redirects to `/login`
- [ ] Visiting `/expenses/<id>/edit` for a non-existent or other user's expense returns 404
- [ ] Visiting `/expenses/<id>/edit` while logged in shows a form pre-filled with the expense's current values
- [ ] The category dropdown has the correct category pre-selected
- [ ] Submitting valid changes redirects to `/profile` and the updated values appear in the transaction list
- [ ] Submitting with a missing or zero amount re-renders the form with an error and the submitted values retained
- [ ] Submitting with an invalid category re-renders the form with an error
- [ ] Submitting with an invalid date re-renders the form with an error
- [ ] Submitting without a description saves the expense with no error
- [ ] Each row in the profile transaction table has an "Edit" link pointing to the correct URL
- [ ] `get_recent_transactions` still supports the Step 06 date filter after `id` is added
- [ ] A POST to another user's expense returns 404 and leaves that row unchanged
- [ ] An update that affects 0 rows returns 404 instead of redirecting
- [ ] The validation limits from Step 07 (finite amount, maximum, two decimals, padded date, 200-character description) apply to edits

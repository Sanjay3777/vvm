# Spec: Step 09 — Delete Expense

## Overview

- Step 09 lets a logged-in user permanently delete one of their own expenses directly from the profile transaction table.
- A "Delete" button per row submits a POST request to `/expenses/<id>/delete`.
- The handler verifies ownership, removes the row from the database, and redirects back to `/profile`.
- There is no separate confirmation page — a browser-side `confirm()` dialog is used to prevent accidental deletions.
- The existing `get_expense_by_id` helper from Step 08 is reused for ownership verification — no new query lookup functions are needed.
- Only one new mutation helper is added: `delete_expense` in `database/queries.py`.

## Depends on

- Step 01 — Database setup (`expenses` table exists)
- Step 03 — Login / Logout (`session["user_id"]` is set and enforced)
- Step 05 — Profile page renders transactions (the delete button lives there)
- Step 06 — Date-range filter (the profile page now has a flash block; the redirect after deleting goes to the unfiltered `/profile`)
- Step 08 — Edit Expense (`get_expense_by_id` is available; the Actions column already exists in the profile transactions table)

## Routes

- `POST /expenses/<int:id>/delete` — verify ownership, delete the expense row, redirect to `/profile` — logged-in only
- No GET handler — a bare GET to this URL must return 405

## Database changes

- No new tables or columns.
- The `expenses` table already has all required columns.

## Templates

- Modify: `templates/profile.html`
  - Inside the existing "Actions" `<td>` per transaction row, add a delete form:
    - `<form>` with `method="POST"` and its action generated with `url_for()` for the delete route using the transaction id
    - A CSS class (for example `inline-form`) on the `<form>` tag keeps the form on the same line as the Edit link — no `style` attribute is used, so the no-inline-styles rule has no exceptions
    - `onsubmit="return confirm('Delete this expense?')"` on the `<form>` tag to provide browser-side confirmation before submission
    - A `<button type="submit">` with `class="btn-delete"` and label "Delete"
  - The "Edit" link from Step 08 remains alongside the new "Delete" button

## Files to change

- `database/queries.py`
  - Add `delete_expense(expense_id, user_id)`
    - Issues a parameterised `DELETE FROM expenses WHERE id = ? AND user_id = ?`
    - The dual-column WHERE clause is the ownership guard
    - Commits and closes the connection before returning
    - Returns the number of rows deleted (0 or 1)
- `app.py`
  - Import `delete_expense` from `database.queries`
  - Replace the GET-only placeholder at `/expenses/<int:id>/delete` with a POST-only handler:
    - Guard: redirect to `/login` if not authenticated
    - Call `get_expense_by_id(id, session["user_id"])`; if `None`, `abort(404)`
    - Call `delete_expense(id, session["user_id"])`; if it returns 0 (for example the row was deleted in between), `abort(404)`
    - Flash a success message "Expense deleted."
    - Redirect to `url_for("profile")`
  - The route must be registered with `methods=["POST"]` only
- `templates/profile.html` — add the delete form inside the existing Actions `<td>`
- `static/css/style.css`
  - Add a `.btn-delete` style using a danger-colour CSS variable — never hardcode hex values; if no danger variable exists in the root variable block of `style.css`, define one there (for example `--color-danger`)
  - Add the `.inline-form` class (display inline) used by the delete form

## Files to create

- `tests/test_delete_expense.py` — see Tests to write

## New dependencies

- None

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- `PRAGMA foreign_keys = ON` must be enabled on every connection (already handled in `get_db()`)
- `delete_expense` must scope its DELETE to `id = ? AND user_id = ?` — this is the ownership guard that prevents one user deleting another's expense
- The route must only accept POST — a bare GET to the URL must return 405
- Unauthenticated access must redirect to `/login` (302)
- If the expense does not exist or belongs to another user, return 404
- After successful deletion, flash "Expense deleted." and redirect to `url_for("profile")` — do not render a template
  - The redirect goes to the unfiltered `/profile`; any active Step 06 filter is not preserved
  - Deleting a row can pull an older expense into the 10-row list (Step 05 cap); this is expected
- No inline `style` attributes anywhere — layout comes from CSS classes
- The confirmation is client-side only: with JavaScript disabled the form submits without a confirm dialog. This is accepted for this step.
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Currency must always display as ₹ — never £ or $
- Use `url_for()` for every internal link — never hardcode paths

## Tests to write

- File: `tests/test_delete_expense.py`
- Test setup: use a temporary database per test run (never the real `spendly.db`), initialised with `init_db()` and `seed_db()`; create a second user with their own expense for the ownership cases
- Unit tests:

| Function | Input | Expected output |
|---|---|---|
| `delete_expense` | Valid `expense_id` and correct `user_id` | Row removed from DB |
| `delete_expense` | Valid `expense_id` and wrong `user_id` | Row remains in DB (0 rows deleted, no error raised) |
| `delete_expense` | Non-existent `expense_id` | No error raised, DB unchanged |
| `delete_expense` | Valid `expense_id` and correct `user_id` | Returns 1 |
| `delete_expense` | Valid `expense_id` and wrong `user_id`, or non-existent `expense_id` | Returns 0 |
| `delete_expense` | Valid `expense_id` and correct `user_id`, with other expenses present | Only that row is removed; other users' and the same user's other expenses remain |

- Route tests:
  - `POST /expenses/<id>/delete` unauthenticated → redirects to `/login` (302)
  - `POST /expenses/<id>/delete` authenticated, own expense → redirects to `/profile` (302); row no longer exists in the database
  - `POST /expenses/<id>/delete` authenticated, other user's expense → returns 404; row still exists in the database
  - `POST /expenses/<id>/delete` authenticated, non-existent id → returns 404
  - `GET /expenses/<id>/delete` any user → returns 405 (Method Not Allowed)
  - `POST /expenses/<id>/delete` authenticated, own expense → following the redirect shows the flash message "Expense deleted."
  - `POST /expenses/<id>/delete` where the row is deleted after the ownership check (delete affects 0 rows) → returns 404
  - `GET /profile` authenticated → each transaction row contains a delete form with method POST, an action pointing at that expense's delete route, the `inline-form` class, and a "Delete" button with the `btn-delete` class, alongside the "Edit" link
  - `GET /profile` authenticated → the page source contains no `style=` attributes
- Manual check (cannot be automated without a browser): clicking "Delete" shows the browser confirm dialog; cancelling leaves the expense in place; confirming deletes it

## Definition of done

- [ ] `POST /expenses/<id>/delete` while logged out redirects to `/login`
- [ ] POSTing to `/expenses/<id>/delete` for a non-existent or other user's expense returns 404
- [ ] `GET /expenses/<id>/delete` returns 405
- [ ] Clicking "Delete" on a transaction row and confirming in the browser dialog removes that expense from the database
- [ ] After deletion, the user is redirected to `/profile` and the deleted expense no longer appears in the transaction list
- [ ] Cancelling the browser `confirm()` dialog does not submit the form and leaves the expense intact
- [ ] Each transaction row in the profile table now shows both "Edit" and "Delete" actions
- [ ] After a successful delete the profile page shows "Expense deleted."
- [ ] A delete that affects 0 rows returns 404 instead of redirecting
- [ ] No inline `style` attributes appear in `profile.html`
- [ ] `.btn-delete` uses a danger-colour CSS variable that is defined in `style.css`

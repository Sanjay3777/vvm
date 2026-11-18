# Step 07 Add Expense Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a logged-in user add an expense through `/expenses/add`, with server-side validation, and link to the form from the profile page and navbar.

**Architecture:** `insert_expense()` goes into `database/queries.py`. The `add_expense()` view guards the session, validates the POST in the spec's order, flashes one error and re-renders with the submitted values, or inserts and redirects to `/profile`. A new `add_expense.html` renders the form and flashes.

**Tech Stack:** Flask 3.1.3, Jinja2, `sqlite3`, `datetime`, `math`, pytest.

**Spec:** `.claude/specs/07-add-expense.md`

## State of the project (from `spendly.db` and the code)

- `spendly.db` has one user (the demo user) and 8 expenses totalling 346.24; the CHECK constraints from Step 01 are in place.
- `/expenses/add` is a GET-only stub returning a string. `database/queries.py` (Step 05) has read helpers only; `db.CATEGORIES` holds the 7 categories.
- Step 06 (date filter) is not implemented yet. This step does not need it: the redirect target is the unfiltered `/profile`, and the add form has its own flash block.
- `base.html` navbar already branches on `session.user_id`; `profile.html` has the "Transaction history" panel title.

## Global Constraints

- Raw `sqlite3` via `get_db()`; parameterised queries only.
- Unauthenticated GET and POST redirect to `/login`; a session user that no longer exists is cleared and redirected to `/login` before any insert.
- Validation: (1) `amount` required, stripped, `float()`, finite, > 0, <= 9999999.99, rounded to 2 decimals; (2) `category` exactly one of the 7; (3) `date` valid `YYYY-MM-DD` parsed with `strptime`, saved zero-padded; (4) `description` optional, stripped, `None` if blank, error if longer than 200 characters.
- Errors go through `flash()`; on failure re-render (200) with the submitted values; on success redirect to `url_for("profile")` (unfiltered).
- The server fills the default date with its local `date.today()`.
- ₹ only; CSS variables only; no inline styles; templates extend `base.html`; `url_for()` for all internal links.

## Review Focus

- `nan`, `inf` and `1e999` (which parses to infinity) amounts must be rejected without a 500. (Task 2)
- A whitespace-only description must be stored as NULL, and exactly 200 characters must be accepted while 201 is rejected. (Task 2)
- A lower-case category (`food`) and a blank date must be rejected, with the form's other values kept. (Task 2)
- Script or HTML in the description must be escaped when the form is re-rendered. (Task 2)
- An unsupported method (`PUT`) on `/expenses/add` must return 405, and a failed validation must leave the row count unchanged. (Task 2)

## File Structure

- Modify: `database/queries.py` (add `insert_expense`, adjust the module docstring)
- Modify: `app.py` (`add_expense` view, imports)
- Create: `templates/add_expense.html`
- Modify: `templates/profile.html` ("Add Expense" button), `templates/base.html` (navbar link), `static/css/profile.css` and `static/css/style.css` only if a small style is needed, using existing variables
- Create: `tests/test_add_expense.py`

---

### Task 1: `insert_expense` helper

**Files:** Modify `database/queries.py`; Create `tests/test_add_expense.py`

**Interfaces:**
- Produces: `insert_expense(user_id: int, amount: float, category: str, date: str, description: str | None) -> int` (the new row id)

- [ ] **Step 1: Write failing tests** (`db_path`; `db.init_db()`, `db.seed_db()`):
  - `test_insert_expense_row_inserted`: `insert_expense(1, 50.0, "Food", "2026-03-20", "Lunch")` returns an id; the row has those exact values and `user_id == 1`.
  - `test_insert_expense_null_description`: with `description=None` the stored value is NULL.
- [ ] **Step 2: Run** `python -m pytest tests/test_add_expense.py -v`. Expected: FAIL (`AttributeError`).
- [ ] **Step 3: Implement** `insert_expense` with a `?`-parameterised INSERT, commit, `cursor.lastrowid`, connection closed in `finally`.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: add insert_expense helper`

### Task 2: Add-expense route, template and links

**Files:** Modify `app.py`, `templates/profile.html`, `templates/base.html`, `tests/test_add_expense.py`; Create `templates/add_expense.html`

**Interfaces:**
- Consumes: `insert_expense(...)`, `get_user_by_id(user_id)`, `db.CATEGORIES`, the `client` fixture
- Produces: `add_expense()` for `GET` and `POST`; template context `categories` (the 7 names) and `form` (dict with `amount`, `category`, `date`, `description`)

- [ ] **Step 1: Write failing route tests** (helper `post(client, **overrides)` with defaults `amount="50.0"`, `category="Food"`, `date="2026-03-20"`, `description="Lunch"`; helper `expense_count()`; login by setting `session["user_id"] = 1`):
  - `test_get_unauthenticated_redirects`, `test_post_unauthenticated_redirects`: 302 to `/login`; the POST inserts nothing.
  - `test_get_form`: 200; contains `method="POST"`, `action="/expenses/add"`, `name="amount"`, `name="description"`, a `<select name="category">` with exactly the 7 options in order, a "Save Expense" button, and a cancel link to `/profile`; the date input is pre-filled with `date.today().isoformat()`.
  - `test_valid_post_redirects_and_inserts`: 302 to `/profile`; the row exists for user 1 with amount 50.0, "Food", "2026-03-20", "Lunch"; `GET /profile` then lists "Lunch".
  - `test_error_cases` (parametrised over: missing amount, `"0"`, `"-5"`, `"abc"`, `"inf"`, `"nan"`, `"1e999"`, `"10000000"`, invalid category `"Travel"`, lower-case `"food"`, missing category, invalid date `"2026-13-45"`, `"not-a-date"`, blank date, 201-character description): 200, an error message in the page, and the expense count unchanged.
  - `test_no_description_stores_null`: omitted description gives 302 and NULL.
  - `test_whitespace_description_stores_null`: `"   "` gives NULL.
  - `test_description_length_boundary`: exactly 200 characters is accepted; 201 is rejected.
  - `test_amount_rounded`: `"12.345"` stores 12.35; `"  50  "` (spaces) stores 50.0; `"9999999.99"` is accepted.
  - `test_date_zero_padded`: `"2026-3-5"` stores `"2026-03-05"`.
  - `test_failure_repopulates_values`: a bad category with amount, date and description set; the body contains all submitted values and the chosen valid category stays selected.
  - `test_html_in_description_escaped`: description `<script>x</script>` with an invalid amount; the body has `&lt;script&gt;` and not `<script>x`.
  - `test_unsupported_method_405`: `PUT /expenses/add` gives 405.
  - `test_missing_session_user`: `session["user_id"] = 999`, `POST` gives 302 to `/login`, the session is cleared, and no row is inserted (also check `GET`).
  - `test_profile_has_add_expense_link`: `GET /profile` has a link to `/expenses/add` with the text "Add Expense".
  - `test_navbar_add_expense_link`: logged in, `GET /` contains `href="/expenses/add"`; logged out it does not.
- [ ] **Step 2: Run** `python -m pytest tests/test_add_expense.py -v`. Expected: new tests FAIL.
- [ ] **Step 3: Implement.**
  - `app.py`: `add_expense()` with `methods=["GET", "POST"]`. Order: no `session["user_id"]` → redirect to `/login`; `get_user_by_id` is `None` → `session.clear()` and redirect to `/login`; GET renders with `form` defaults (today's date, empty others); other methods `abort(405)` (Flask handles this automatically for non-listed methods); POST validates in spec order, using `math.isfinite`, `datetime.strptime(value, "%Y-%m-%d")` and `.date().isoformat()`, and the 200-character check after stripping. On the first error `flash(msg, "error")` and re-render with the submitted values. Messages: "Amount is required.", "Amount must be a number.", "Amount must be greater than 0 and at most 9999999.99.", "Choose a valid category.", "Enter a valid date.", "Description must be 200 characters or fewer." On success insert and redirect to `url_for("profile")`.
  - `templates/add_expense.html`: extends `base.html`; reuses the `auth-section` form look from the other forms; flash loop (same markup as `register.html`); fields as in the spec with `step="0.01"`, `min="0.01"`, `maxlength="200"`, `required` on amount, category and date; selected option driven by `form.category`; "Save Expense" button; cancel link to `url_for('profile')`.
  - `profile.html`: an "Add Expense" link (button-style class) in the transaction panel header. `base.html`: an "Add Expense" link in the logged-in navbar. Any new CSS uses existing variables only.
- [ ] **Step 4: Run** `python -m pytest -v`. Expected: all PASS (Steps 01 to 05 included).
- [ ] **Step 5: Manual check:** run `python app.py` (set `SECRET_KEY`), sign in as the demo user, add an expense through the form, confirm it appears on `/profile`, then try a bad amount and check the form keeps your input; remove the test expense afterwards.
- [ ] **Step 6: Commit** `feat: implement add expense`

## Self-Review

- Spec coverage: routes, helper, template fields, navbar and profile links, all four validation rules, flash and re-population, redirect, missing-user handling, temporary test database, and all 13 Definition of Done items map to Tasks 1-2.
- Names consistent: `insert_expense`, `categories`, `form`, flash category `error`.
- Spec deviations: none in file lists beyond the test file the spec already lists. Step 06 is a listed dependency but is not built yet; the redirect already goes to the unfiltered `/profile`, so nothing here depends on it.
- Not done (outside the spec): no future-date limit, no CSRF protection, no duplicate detection.

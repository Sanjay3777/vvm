# Step 02 User Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/register` a working GET + POST route that validates input, creates a user with a hashed password, and redirects to `/login`.

**Architecture:** A `create_user()` helper in `database/db.py` does the insert and lets `sqlite3.IntegrityError` propagate. The `register()` view in `app.py` applies input hygiene, validates in the spec's order, flashes errors with category `error` and re-renders, or flashes success with category `success` and redirects. Templates render flashes by category.

**Tech Stack:** Flask 3.1.3 (`flash`, `redirect`, `url_for`, `abort`), werkzeug `generate_password_hash`, `sqlite3`, pytest.

**Spec:** `.claude/specs/02-registration.md`

## State of the project (from reading `spendly.db` and the code)

- `spendly.db` has the Step 01 schema; `users` holds only the seeded demo user (`demo@spendly.com`), so it is the existing-email case for tests.
- `templates/register.html` has no `confirm_password` field, a hard-coded `action="/register"`, and an `{% if error %}` block instead of flashes.
- `templates/login.html` has no flash display, so a success flash redirected there would never be seen.
- `static/css/style.css` has `--danger`/`--danger-light` and `.auth-error`, but no success style.
- `app.py` has no `secret_key` and the `/register` route is GET-only.

## Global Constraints

- No ORM; parameterised queries only; never f-strings in SQL.
- Hash with `werkzeug.security.generate_password_hash`; never store plaintext.
- `app.secret_key` hard-coded dev string for now (must come from the environment before deployment).
- Input hygiene before validation: strip and lower-case `email`; strip `name`; never alter `password` or `confirm_password`.
- Validation order: (1) non-empty, (2) passwords match, (3) email not registered (catch `sqlite3.IntegrityError`).
- On failure re-render (no redirect), keep `name` and `email` filled, never re-populate passwords.
- On success flash a message and redirect to `url_for('login')`.
- `abort(405)` for any unsupported method; templates extend `base.html`; CSS variables only (no new hex); `url_for()` for all internal links.

## Review Focus

- Email in different case or with spaces (`  Demo@Spendly.com `) must be treated as `demo@spendly.com`. (Task 2)
- Whitespace-only name or email must count as empty and insert nothing. (Task 2)
- A password with leading or trailing spaces must be stored unaltered (login later compares the exact string). (Task 2)
- A name or email containing `<script>` must be shown escaped when the form is re-rendered. (Task 2)
- Repeated valid submissions with the same email must leave exactly one user. (Task 2)

## File Structure

- Modify: `database/db.py` (add `create_user`)
- Modify: `app.py` (secret key, imports, `register` view)
- Modify: `templates/register.html` (action, `confirm_password`, flash block, retained values)
- Modify: `templates/login.html` (flash block so the success message is visible; small addition beyond the spec's file list)
- Modify: `static/css/style.css` (`.auth-success` using existing variables)
- Modify: `tests/conftest.py` (add `client` fixture)
- Create: `tests/test_registration.py` (the spec lists "Files to create: None"; added to verify the Definition of Done)

---

### Task 1: `create_user` helper

**Files:** Modify `database/db.py`; Create `tests/test_registration.py`

**Interfaces:**
- Produces: `create_user(name: str, email: str, password: str) -> int` (new user id; raises `sqlite3.IntegrityError` on a duplicate email)

- [ ] **Step 1: Write failing tests** in `tests/test_registration.py` (use `db_path` fixture, call `db.init_db()` first):
  - `test_create_user_returns_id_and_hashes_password`: returned id matches the row; `password_hash != "secret123"`; `check_password_hash(hash, "secret123")` is true.
  - `test_create_user_duplicate_email_raises`: a second call with the same email raises `sqlite3.IntegrityError`; still one row.
- [ ] **Step 2: Run** `python -m pytest tests/test_registration.py -v`. Expected: FAIL (`AttributeError`).
- [ ] **Step 3: Implement** `create_user` in `database/db.py`: hash, insert with `?` placeholders, commit, return `cursor.lastrowid`, close the connection in `finally`.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: add create_user helper`

### Task 2: Register route and templates

**Files:** Modify `app.py`, `templates/register.html`, `templates/login.html`, `static/css/style.css`, `tests/conftest.py`, `tests/test_registration.py`

**Interfaces:**
- Consumes: `create_user(name, email, password) -> int`
- Fixture `client` (conftest): patches `DB_PATH` via `db_path`, runs `init_db()` and `seed_db()`, returns `app.app.test_client()`.
- Produces: `register()` handling `GET` and `POST`; flash categories `error` and `success`.

- [ ] **Step 1: Write failing route tests** (helper `post(client, **overrides)` with valid defaults `name="Asha"`, `email="asha@example.com"`, `password="secret123"`, `confirm_password="secret123"`; helper `count_users()`):
  - `test_get_register_renders_form`: 200; response contains `name="confirm_password"`, `action="/register"` and `method="POST"`.
  - `test_valid_registration_redirects_to_login`: 302 to `/login`; user row exists with a hashed password; following the redirect shows the success message "Account created".
  - `test_mismatched_passwords`: 200; "Passwords do not match"; user count unchanged (1).
  - `test_each_empty_field` (parametrised over the four fields, value `""`): 200; error shown; count unchanged.
  - `test_whitespace_only_name_and_email` (parametrised): `"   "` is treated as empty; count unchanged.
  - `test_duplicate_email`: registering `demo@spendly.com` gives 200 and "Email already registered".
  - `test_duplicate_email_case_and_spaces`: `"  Demo@Spendly.com "` gives "Email already registered"; count unchanged.
  - `test_email_stored_lowercase_and_name_stripped`: post `"  Asha@Example.COM "` and `"  Asha  "`; the row has `asha@example.com` and `Asha`.
  - `test_failure_keeps_name_and_email_not_passwords`: on mismatch the body contains `value="Asha"` and `value="asha@example.com"`, and does not contain the submitted password string.
  - `test_password_with_spaces_stored_unaltered`: post `password=confirm_password=" pass word "`; `check_password_hash(hash, " pass word ")` is true.
  - `test_repeat_submission_creates_one_user`: two identical valid posts give count 2 in total (demo plus one), and the second post returns 200 with "Email already registered".
  - `test_html_in_name_is_escaped`: name `<script>x</script>` with mismatched passwords; the body contains `&lt;script&gt;` and not `<script>x`.
  - `test_unsupported_method_405`: `client.put("/register")` returns 405.
- [ ] **Step 2: Run** `python -m pytest tests/test_registration.py -v`. Expected: new tests FAIL.
- [ ] **Step 3: Implement.**
  - `app.py`: `app.secret_key` = a hard-coded dev string with a comment that it must come from the environment before deployment; import `flash, redirect, request, url_for, abort, sqlite3, create_user`; `register()` with `methods=["GET", "POST"]`: GET renders `register.html`; POST applies hygiene, validates in spec order with messages "All fields are required.", "Passwords do not match.", "Email already registered."; on failure `flash(msg, "error")` and `render_template("register.html", name=..., email=...)`; on success `flash("Account created. Please sign in.", "success")` and `redirect(url_for("login"))`; any other method `abort(405)`.
  - `templates/register.html`: form `action="{{ url_for('register') }}"`; replace the `error` block with a loop over `get_flashed_messages(with_categories=true)` showing `auth-error` for `error` and `auth-success` for `success`; pre-fill `value="{{ name or '' }}"` and `value="{{ email or '' }}"`; add a `confirm_password` password field (label "Confirm password", `required`) after the password field. Visual style otherwise unchanged.
  - `templates/login.html`: the same flash loop, replacing the `error` block's position only by adding the loop above it (keep `error` for Step 03).
  - `static/css/style.css`: `.auth-success` mirroring `.auth-error` but with `--accent-light` background, `--accent` text and `--border` border; no new hex values.
- [ ] **Step 4: Run** `python -m pytest -v`. Expected: all PASS (Step 01 tests included).
- [ ] **Step 5: Manual check:** start `python app.py`, register a new user, confirm the redirect to `/login` with the success banner and the hash (not the plaintext) in `spendly.db`; delete that test user afterwards.
- [ ] **Step 6: Commit** `feat: implement user registration`

## Self-Review

- Spec coverage: Routes, DB helper, template changes, validation order, hygiene rules, retained values, secret key, `abort(405)`, and all 10 Definition of Done items map to Tasks 1-2 (the stored-hash item is checked by tests and the manual step).
- Names consistent: `create_user`, flash categories `error` / `success`, fixture `client`.
- Spec deviations: (1) test files added; (2) `login.html` and `style.css` touched so the required success flash is visible. No password-length rule is added because the spec has none, even though the placeholder says "Min. 8 characters".

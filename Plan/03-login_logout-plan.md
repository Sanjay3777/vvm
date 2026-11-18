# Step 03 Login and Logout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/login` a working GET + POST route that sets `session["user_id"]`, and make `/logout` clear the session, so the app can tell users from guests.

**Architecture:** A `get_user_by_email()` helper in `database/db.py` does the lookup. The `login()` view normalises the email, checks the password hash, then clears and sets the session. Failures flash a generic error and re-render the form. `logout()` clears the session and redirects.

**Tech Stack:** Flask 3.1.3 (`session`, `flash`, `redirect`, `url_for`), werkzeug `check_password_hash`, `sqlite3`, pytest.

**Spec:** `.claude/specs/03-login_logout.md`

## State of the project (from `spendly.db` and the code)

- `spendly.db` has one user, `demo@spendly.com` (password `demo123`), which is the login case for tests.
- Step 02 left `app.secret_key` set and a flash loop in `login.html`, so flashes already display there.
- `login.html` still has the hard-coded `action="/login"`, no retained email, and an `{% if error %}` block that is now unused.
- `/login` is GET-only and `/logout` returns a stub string.

## Global Constraints

- No ORM; raw `sqlite3` via `get_db()`; parameterised queries only.
- Strip and lower-case `email` before lookup; never alter `password`.
- Verify with `werkzeug.security.check_password_hash`.
- On success: `session.clear()` then `session["user_id"] = <int>`; redirect to `url_for("landing")`.
- No `next` or other redirect parameter.
- Failure flash is exactly "Invalid email or password." for both wrong password and unknown email.
- `logout()`: `session.clear()` then redirect to `url_for("landing")`; no login required.
- Templates extend `base.html`; CSS variables only; `url_for()` for all links.

## Review Focus

- A POST with a missing `email` or `password` field must give the same generic error, not a 400 or 500. (Task 2)
- A `?next=https://evil.example` parameter, on the URL or in the form, must be ignored. (Task 2)
- Stale session data (for example `{"foo": "bar"}` plus an old `user_id`) must be gone after login. (Task 2)
- A session pointing at no one must not crash `/logout`; logout with no session still redirects. (Task 2)
- An email with HTML must be escaped when the form is re-rendered. (Task 2)

## File Structure

- Modify: `database/db.py` (add `get_user_by_email`)
- Modify: `app.py` (`login`, `logout`, `session` import)
- Modify: `templates/login.html` (action via `url_for`, retained email, remove dead `error` block)
- Modify: `tests/test_registration.py` is untouched; Create: `tests/test_login_logout.py` (the spec lists "Files to create: None"; added to verify the Definition of Done)

---

### Task 1: `get_user_by_email` helper

**Files:** Modify `database/db.py`; Create `tests/test_login_logout.py`

**Interfaces:**
- Produces: `get_user_by_email(email: str) -> sqlite3.Row | None`

- [ ] **Step 1: Write failing tests** (`db_path` fixture, `db.init_db()` first):
  - `test_get_user_by_email_found`: after `create_user("A", "a@x.com", "pw")`, returns a row with `name == "A"`, `email == "a@x.com"` and an `id` and `password_hash`.
  - `test_get_user_by_email_missing_returns_none`: unknown email returns `None`.
- [ ] **Step 2: Run** `python -m pytest tests/test_login_logout.py -v`. Expected: FAIL (`AttributeError`).
- [ ] **Step 3: Implement** `get_user_by_email` in `database/db.py` with one `?` placeholder; close the connection in `finally`. It does no normalisation itself (the route does that).
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: add get_user_by_email helper`

### Task 2: Login and logout routes

**Files:** Modify `app.py`, `templates/login.html`, `tests/test_login_logout.py`

**Interfaces:**
- Consumes: `get_user_by_email(email)`; the `client` fixture from `tests/conftest.py`
- Produces: `login()` (GET, POST), `logout()` (GET)

- [ ] **Step 1: Write failing tests** (helper `login(client, email, password, **extra)` posting to `/login`):
  - `test_get_login_renders_form`: 200; contains `name="email"`, `name="password"`, `action="/login"`, and a link to `/register`.
  - `test_valid_login_sets_session_and_redirects`: demo credentials give 302 to `/`; `session["user_id"] == 1` (use `with client.session_transaction()`), and it is an `int`.
  - `test_login_normalises_email`: `"Demo@Spendly.com "` with `demo123` gives 302 and `session["user_id"] == 1`.
  - `test_wrong_password`: 200; "Invalid email or password."; no `user_id` in session.
  - `test_unknown_email`: 200; the same message; no `user_id`.
  - `test_missing_fields_give_generic_error`: posting `{}` and `{"email": "demo@spendly.com"}` both give 200 and the same message.
  - `test_password_not_stripped`: `" demo123"` with the demo email fails.
  - `test_next_parameter_ignored`: POST to `/login?next=https://evil.example` with extra form field `next=https://evil.example` and valid credentials; `Location` ends with `/` and does not contain `evil`.
  - `test_login_clears_previous_session`: set `session["foo"] = "bar"` and `session["user_id"] = 999` via `session_transaction`; after a valid login the session has `user_id == 1` and no `foo`.
  - `test_failed_login_keeps_email_only`: after a wrong password the body contains `value="demo@spendly.com"` and not `demo123`.
  - `test_html_in_email_is_escaped`: email `<b>x</b>` posted; the body contains `&lt;b&gt;` and not `<b>x`.
  - `test_logout_clears_session`: log in, `GET /logout` gives 302 to `/`; `user_id` no longer in the session; the body is not the stub text.
  - `test_logout_without_session_redirects`: `GET /logout` as a guest gives 302 to `/`.
- [ ] **Step 2: Run** `python -m pytest tests/test_login_logout.py -v`. Expected: new tests FAIL.
- [ ] **Step 3: Implement.**
  - `app.py`: import `session` and `check_password_hash`, plus `get_user_by_email`. `login()` with `methods=["GET", "POST"]`: GET renders; POST reads `email` (strip, lower) and `password` (raw) with `.get(..., "")`; looks up the user; if there is none or the hash check fails, `flash("Invalid email or password.", "error")` and re-render with `email=` retained; otherwise `session.clear()`, `session["user_id"] = user["id"]`, redirect to `url_for("landing")`. The `next` value is never read. `logout()`: `session.clear()`, redirect to `url_for("landing")`.
  - `templates/login.html`: form `action="{{ url_for('login') }}"`; email input gets `value="{{ email or '' }}"`; remove the unused `{% if error %}` block (the flash loop from Step 02 stays).
- [ ] **Step 4: Run** `python -m pytest -v`. Expected: all PASS (Steps 01 and 02 included).
- [ ] **Step 5: Commit** `feat: implement login and logout`

## Self-Review

- Spec coverage: routes, helper, template, normalisation, `session.clear()`, no `next`, generic error, fixed redirects and all 8 Definition of Done items map to Tasks 1-2.
- Names consistent: `get_user_by_email`, `session["user_id"]`.
- Spec deviation: test file added to "Files to create: None".
- Not addressed (the spec doesn't ask): timing difference between unknown email and wrong password, no rate limiting, no navbar change for logged-in users, no CSRF protection, and logout stays a GET request.

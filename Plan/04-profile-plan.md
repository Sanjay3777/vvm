# Step 04 Profile Page (Hardcoded UI) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `/profile` stub with a protected, fully designed profile page driven by hardcoded data, and give the navbar a logged-in state.

**Architecture:** The `profile()` view checks `session.get("user_id")`, then passes four hardcoded Python structures (`user`, `stats`, `expenses`, `categories`) to `profile.html`. `base.html` branches on `session.user_id`. Styles live in a new `static/css/profile.css`, loaded through the existing `head` block. No DB queries.

**Tech Stack:** Flask 3.1.3, Jinja2, plain CSS variables, pytest.

**Spec:** `.claude/specs/04-profile.md`

## State of the project (from `spendly.db` and the code)

- `spendly.db` holds the demo user (`Demo User`, `demo@spendly.com`, created 2026-11-18) and 8 expenses totalling 346.24. The hardcoded data mirrors them.
- `base.html` has a `head` block and always shows the guest links; `profile()` is a stub returning a string.
- `style.css` defines the variables (`--accent`, `--accent-light`, `--accent-2`, `--accent-2-light`, `--danger`, `--danger-light`, `--ink*`, `--paper*`, `--border*`, radii and fonts). No new hex values may be added.

## Global Constraints

- No DB queries; all data is hardcoded Python dicts and lists in `app.py`.
- Guard: `session.get("user_id")`; if absent, `redirect(url_for("login"))`.
- Currency shown as ₹ only, never £ or $.
- Hardcoded values mirror the Step 01 seed: user "Demo User", `demo@spendly.com`, initials "DU"; total ₹346.24, 8 transactions, top category "Bills"; the 8 seed rows and 7 category totals.
- CSS variables only, no hex values; no inline styles in `profile.html`; badges use CSS classes.
- Templates extend `base.html`; `url_for()` for every internal link.
- Navbar when `session.user_id` is set: the name from the `user` dict (or a "Profile" link on pages without one) plus a logout link; guests see the old links.

## Review Focus

- Guard order: an unauthenticated request must redirect and never render any profile data. (Task 2)
- The page source must contain no `style=` attribute and no hex colour, in `profile.html` output and in `profile.css`. (Task 2)
- No `£` or `$` anywhere in the rendered profile page. (Task 2)
- A logged-in user on a non-profile page (`/`) must see a "Profile" link and a logout link, not "Get started". (Task 1)
- The breakdown percentages must add up to 100 and every bar must have a label, so the bars are not decorative only. (Task 2)

## File Structure

- Modify: `templates/base.html` (navbar states)
- Modify: `app.py` (`profile` view and hardcoded data)
- Create: `templates/profile.html`, `static/css/profile.css`
- Create: `tests/test_profile.py` (the spec lists only the two files above; the test file is an addition)

---

### Task 1: Navbar logged-in state

**Files:** Modify `templates/base.html`; Create `tests/test_profile.py`

**Interfaces:**
- Consumes: Jinja `session` and an optional template variable `user` (dict with `name`)
- Produces: navbar markup used by every page

- [ ] **Step 1: Write failing tests** (`client` fixture; helper `login_session(client)` sets `session["user_id"] = 1` via `session_transaction`):
  - `test_navbar_guest_links`: `GET /` shows "Sign in" and "Get started", and no `/logout` link.
  - `test_navbar_logged_in_on_landing`: after `login_session`, `GET /` shows a link to `/logout` and a "Profile" link to `/profile`, and does not show "Get started".
- [ ] **Step 2: Run** `python -m pytest tests/test_profile.py -v`. Expected: logged-in test FAILS.
- [ ] **Step 3: Implement** in `base.html`: inside `.nav-links`, `{% if session.user_id %}` show a link to `url_for('profile')` whose text is `user.name` when a `user` variable is defined, else "Profile", plus a "Logout" link to `url_for('logout')`; `{% else %}` keep the existing guest links.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: add logged-in navbar state`

### Task 2: Profile view and page

**Files:** Modify `app.py`, `tests/test_profile.py`; Create `templates/profile.html`, `static/css/profile.css`

**Interfaces:**
- Produces: `profile()` passing `user: {name, email, initials, member_since}`, `stats: {total_spent, transaction_count, top_category}`, `expenses: list of {date, description, category, amount}` (the 8 seed rows, newest first), `categories: list of {name, amount, percent}` (7 rows, largest first; percents 35, 23, 14, 10, 8, 7, 3). Amounts are preformatted strings such as `"346.24"`.

- [ ] **Step 1: Write failing tests:**
  - `test_profile_requires_login`: `GET /profile` gives 302 to `/login`, and the body has no "Demo User".
  - `test_profile_logged_in_200`: 200.
  - `test_profile_user_card`: contains "Demo User", `demo@spendly.com`, "DU", and "Member since".
  - `test_profile_stats`: contains `₹346.24`, "8", and "Bills" in the stats row.
  - `test_profile_transactions`: 8 rows in the table body (count `<tr` in `<tbody>`), each with a `badge` class; contains "Electricity bill" and "₹120.00".
  - `test_profile_category_breakdown`: all 7 category names appear in the breakdown section; 7 `<progress` elements; their `value` attributes sum to 100.
  - `test_profile_currency`: body contains `₹` and contains neither `£` nor `$`.
  - `test_profile_no_inline_styles_or_hex`: the page contains no `style=` and no match for `#[0-9a-fA-F]{3,8}\b` in the rendered body; the same hex check on `static/css/profile.css` finds none.
  - `test_profile_css_linked`: body contains `css/profile.css`; the file exists and is non-empty.
  - `test_profile_navbar_shows_name_and_logout`: body contains a link to `/logout` and the name "Demo User" in the navbar.
  - `test_profile_data_matches_seed`: compare the view's context to the seeded DB, reading `spendly.db` rows from the test database: total, count, top category, and each category total equal the hardcoded values.
- [ ] **Step 2: Run** `python -m pytest tests/test_profile.py -v`. Expected: new tests FAIL.
- [ ] **Step 3: Implement.**
  - `app.py`: replace the stub with `profile()`; guard first; then render `profile.html` with the four hardcoded structures (module-level constants are fine). `member_since` is "November 2026".
  - `templates/profile.html`: extends `base.html`; title block; `head` block links `css/profile.css` via `url_for('static', ...)`; four sections with headings: user info card (avatar with initials, name, email, member since), stats row (three stat tiles with labels "Total spent", "Transactions", "Top category"), transactions table (Date, Description, Category badge `<span class="badge badge-{{ category|lower }}">`, Amount with `₹`), category breakdown (name, `<progress class="breakdown-bar" max="100" value="{{ percent }}">`, amount with `₹`, percent label).
  - `static/css/profile.css`: styles for card, avatar, stats row, table, badges (one class per category using only existing variables, for example accent, accent-2, danger and ink tones with their `-light` pairs), breakdown rows and the `progress` element (WebKit and Firefox pseudo-elements); responsive stacking under the existing mobile breakpoint style.
- [ ] **Step 4: Run** `python -m pytest -v`. Expected: all PASS (Steps 01 to 03 included).
- [ ] **Step 5: Manual check:** start `python app.py`, sign in as `demo@spendly.com`, open `/profile`, confirm the four sections and the navbar look right at desktop and phone width.
- [ ] **Step 6: Commit** `feat: add hardcoded profile page`

## Self-Review

- Spec coverage: route guard, four sections, navbar states, `profile.css`, hardcoded seed mirror, ₹ rule, no inline styles or hex, and all 11 Definition of Done items map to Tasks 1-2.
- Names consistent: `user`, `stats`, `expenses`, `categories`.
- Spec deviations: test file added. The progress bars use `<progress>` instead of a width style, because inline styles are forbidden. The hardcoded dates are fixed text, so they will not follow the real month the way the seed does; Step 05 replaces them.

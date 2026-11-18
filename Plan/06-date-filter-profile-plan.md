# Step 06 Date Filter on Profile Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users narrow the profile page's stats, transaction list and category breakdown to a date range, using `date_from` and `date_to` query parameters, preset links and a custom range form.

**Architecture:** The three query helpers in `database/queries.py` gain optional `date_from`/`date_to` arguments (`AND date BETWEEN ? AND ?` when both are given). `profile()` validates the parameters, computes preset ranges and which filter is active, flashes the invalid-range error, and passes everything to `profile.html`, which gets a filter bar and a flash block.

**Tech Stack:** Flask 3.1.3, Jinja2, `sqlite3`, `datetime`, `calendar`, pytest.

**Spec:** `.claude/specs/06-date-filter-profile.md`

## State of the project (from the code and `spendly.db`)

- `spendly.db` holds the demo user with 8 expenses (dates in November 2026); it is not touched.
- Steps 05 (helpers), 07 (add) and 08 (edit) are built. `get_recent_transactions(user_id, limit=10)` returns `id`; the Step 08 spec expects `get_recent_transactions(user_id, limit=10, date_from=None, date_to=None)`, which this step provides.
- `profile()` calls the three helpers with `user_id` only, and `profile.html` has no flash block and no filter bar.
- Step 09 (delete) will reuse the flash block this step adds; its prompt comes separately and is not part of this plan.

## Global Constraints

- Raw `sqlite3`; dates only as `?` placeholders, never formatted into SQL.
- With no dates, all three helpers behave exactly as in Step 05.
- Validation in `app.py` with `datetime.strptime(value, "%Y-%m-%d")`; bad or empty values count as absent (no message). One valid date alone means unfiltered. `date_from` after `date_to` means both absent plus the flash "Start date must not be after end date."; equal dates are valid.
- Presets are computed in `app.py` (stdlib only), `date_to` always today: "This Month" starts on the 1st; "Last 3 Months" and "Last 6 Months" go back 3 or 6 calendar months, clamped to the last day of the target month (31 May goes back to 28/29 February). "All Time" has no parameters.
- A preset is active only when the validated range equals its computed range exactly; any other valid range shows as custom (fields pre-filled, no preset active); no parameters means "All Time" is active.
- Preset links via `url_for("profile", date_from=..., date_to=...)`; no hardcoded paths.
- CSS variables only; no inline styles; ₹ only; templates extend `base.html`.

## Review Focus

- `date_from=2026-3-5` (unpadded but parseable) must be normalised to `2026-03-05`, so highlighting and the SQL string comparison still work. (Task 2)
- Leap years: 31 May 2024 minus 3 months is 29 Feb 2024, and 31 Aug 2026 minus 6 months is 28 Feb 2026. (Task 2)
- Boundary expenses dated exactly `date_from` or `date_to` must be included. (Task 1)
- Hostile values (`date_from=<script>`, a 10 000-character string, `date_from[]=x`, `date_from=2026-02-30`) must give 200, never a 500, and must not echo unescaped. (Task 2)
- The invalid-range flash must show once and not reappear on the next page load or on another page. (Task 2)

## File Structure

- Modify: `database/queries.py` (three helpers, shared WHERE builder)
- Modify: `app.py` (`profile()`, preset helpers)
- Modify: `templates/profile.html` (flash block and filter bar), `static/css/profile.css`
- Create: `tests/test_date_filter.py`

---

### Task 1: Date-aware query helpers

**Files:** Modify `database/queries.py`; Create `tests/test_date_filter.py`

**Interfaces:**
- Produces: `get_summary_stats(user_id, date_from=None, date_to=None)`, `get_recent_transactions(user_id, limit=10, date_from=None, date_to=None)`, `get_category_breakdown(user_id, date_from=None, date_to=None)`. The range applies only when both dates are given.

- [ ] **Step 1: Write failing tests** (`db_path`; a new user `u` with Food 10.00 on 2026-01-10, Bills 20.00 on 2026-02-15, Food 30.00 on 2026-03-20, Health 5.00 on 2026-03-20, Other 40.00 on 2026-04-01):
  - `test_stats_inclusive_bounds`: range 2026-01-10 to 2026-04-01 includes both boundary expenses (count 5, total 105.0).
  - `test_stats_range_inside`: 2026-02-01 to 2026-03-31 gives total 55.0, count 3, top category "Food".
  - `test_stats_empty_range`: 2026-05-01 to 2026-05-31 equals `{"total_spent": 0, "transaction_count": 0, "top_category": "—"}`.
  - `test_stats_no_dates_unfiltered`: equals the result with both dates `None` (count 5).
  - `test_stats_single_date_ignored`: only `date_from` given behaves as unfiltered.
  - `test_transactions_range_newest_first_limit`: 2026-02-01 to 2026-03-31 returns 3 rows, newest first; `limit=2` returns 2.
  - `test_breakdown_range`: 2026-02-01 to 2026-03-31 returns only Food, Bills, Health with `pct` summing to 100; empty range returns `[]`.
  - `test_other_users_not_included_in_range`: another user's expense inside the range changes nothing.
- [ ] **Step 2: Run** `python -m pytest tests/test_date_filter.py -v`. Expected: FAIL (unexpected keyword argument).
- [ ] **Step 3: Implement** in `database/queries.py`: a private `_range_clause(date_from, date_to)` returning `("AND date BETWEEN ? AND ?", [from, to])` when both are set and `("", [])` otherwise; use it in `get_summary_stats`, `_category_totals`, `get_recent_transactions`, and `get_category_breakdown` (which passes the dates to `_category_totals`). Placeholders only.
- [ ] **Step 4: Run** the same command and the full suite. Expected: PASS.
- [ ] **Step 5: Commit** `feat: add date range to profile query helpers`

### Task 2: Profile view, filter bar and flash block

**Files:** Modify `app.py`, `templates/profile.html`, `static/css/profile.css`, `tests/test_date_filter.py`

**Interfaces:**
- Consumes: the date-aware helpers
- Produces:
  - `_months_back(d: date, months: int) -> date` (clamped)
  - `_preset_ranges(today: date) -> list[dict]` of `{"label", "date_from", "date_to"}` for This Month, Last 3 Months, Last 6 Months, All Time (`None` bounds)
  - `profile()` template context `presets` (each with `active: bool`), `date_from`, `date_to` (validated ISO strings or `None`), `custom_active: bool`

- [ ] **Step 1: Write failing tests:**
  - Unit: `test_months_back_clamps` (`date(2024,5,31)`, 3 gives `2024-02-29`; `date(2026,8,31)`, 6 gives `2026-02-28`; `date(2026,3,15)`, 3 gives `2025-12-15`); `test_preset_ranges` (for `date(2026,5,31)`: This Month 2026-05-01 to 2026-05-31; Last 3 Months from 2026-02-28; Last 6 Months from 2025-11-30; All Time has `None` bounds).
  - Route (user `u` data above, logged in via session):
    - `test_no_params_all_shown`: 200; all 5 expenses in the list; total ₹105.00; "All Time" link is `href="/profile"` and marked active.
    - `test_valid_range_filters_all_sections`: stats total ₹55.00, 3 table rows, breakdown has 3 categories, no "Other".
    - `test_equal_dates_single_day`: 2026-03-20 to 2026-03-20 shows 2 rows, no error.
    - `test_reversed_range_flashes_and_unfiltered`: 200; contains "Start date must not be after end date."; all 5 rows shown.
    - `test_flash_shown_once`: the next `GET /profile` and `GET /expenses/add` do not contain the message.
    - `test_malformed_no_error_unfiltered` (parametrised: `date_from=not-a-date`, `date_from=2026-02-30`, `date_from=&date_to=`, only `date_from=2026-02-01`, only `date_to=2026-02-01`): 200, 5 rows, no "must not be after".
    - `test_hostile_values_safe`: `date_from=<script>x</script>&date_to=2026-01-01`, a 10 000-character value, and `date_from[]=x` all give 200; the body has no `<script>x`.
    - `test_unpadded_date_normalised`: `date_from=2026-2-1&date_to=2026-3-31` filters like the padded range and pre-fills `value="2026-02-01"`.
    - `test_preset_links_present`: all four labels are links; "All Time" is exactly `/profile`; the others contain `date_from=` and `date_to=`.
    - `test_active_state_for_preset`: requesting a preset's exact URL (computed with `app._preset_ranges(date.today())`) marks only that preset active.
    - `test_custom_range_prefilled_no_preset_active`: 2026-02-01 to 2026-03-31 pre-fills both inputs and no `filter-active` appears on a preset link.
    - `test_empty_range_shows_zeros`: 2026-05-01 to 2026-05-31 shows ₹0.00, a Transactions tile of 0, and no `<progress`.
    - `test_currency_kept_when_filtered`: ₹ present, no `£` or `$`.
    - `test_no_inline_styles_with_filter_bar`: no `style=` in the page.
- [ ] **Step 2: Run** `python -m pytest tests/test_date_filter.py -v`. Expected: new tests FAIL.
- [ ] **Step 3: Implement.**
  - `app.py`: add `_months_back` (using `calendar.monthrange` to clamp) and `_preset_ranges`; a `_parse_iso_date(value) -> str | None` (strip, empty is `None`, `strptime`, return `isoformat()`; non-string input is `None`). In `profile()` read `request.args.get(...)` (single value), validate; if both valid and `from > to`, `flash("Start date must not be after end date.", "error")` and use no filter; if only one valid, no filter. Compute `presets` with `active` set where the validated range equals the preset; the All Time preset is active when there is no filter; `custom_active` is true when a filter is set and no preset matches. Pass the dates to the three helpers.
  - `templates/profile.html`: a flash loop (same markup as the auth pages: `auth-error` for errors) above the cards; a filter bar above the stats row with the preset links (`url_for('profile', date_from=p.date_from, date_to=p.date_to)`, class `filter-btn`, plus `filter-active` when active) and a GET form (`action="{{ url_for('profile') }}"`) with `date_from`/`date_to` date inputs (values from the validated dates, auto-escaped) and an "Apply" button; the form block gets `filter-active` styling when `custom_active`.
  - `static/css/profile.css`: `.filter-bar`, `.filter-btn`, `.filter-active`, custom form layout and a small responsive rule, using only existing variables.
- [ ] **Step 4: Run** `python -m pytest -v`. Expected: all PASS (Steps 01 to 08 included).
- [ ] **Step 5: Manual check:** run `python app.py` (set `SECRET_KEY`), sign in as the demo user, click each preset and apply a custom range, then a reversed range.
- [ ] **Step 6: Commit** `feat: add date filter to profile page`

## Self-Review

- Spec coverage: query parameters, validation and fallback rules, flash, presets and clamping, active states, all three sections filtered, ₹ and no-inline-style rules, and all 14 Definition of Done items map to Tasks 1-2.
- Names consistent: `_months_back`, `_preset_ranges`, `presets`, `custom_active`, `filter-btn`, `filter-active`.
- Spec deviation: unpadded but parseable dates (`2026-2-1`) are accepted and normalised to padded form; the spec only says malformed values are ignored.
- Not changed: edits, adds and deletes still redirect to the unfiltered `/profile` (as the Step 07 to 09 specs say). The 10-row cap still applies inside a filter.

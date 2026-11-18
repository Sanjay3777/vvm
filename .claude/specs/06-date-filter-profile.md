# Spec: Step 06 — Date Filter on Profile Page

## Overview

- Step 06 adds a date-range filter to the existing `/profile` route so users can narrow the transaction list, summary stats, and category breakdown to a specific period.
- The filter is driven entirely by query-string parameters (`date_from` and `date_to`) on `GET /profile` — no new routes required.
- A compact filter bar with four quick-select preset buttons ("This Month", "Last 3 Months", "Last 6 Months", "All Time") and two `<input type="date">` fields lets users pick any custom range.
- All three data sections (summary stats, recent transactions, category breakdown) must respect the active date filter.

## Depends on

- Step 01 — Database setup (`expenses` table with `date` column must exist)
- Step 04 — Profile page UI (template with all four sections must exist)
- Step 05 — Backend connection (`get_summary_stats`, `get_recent_transactions`, `get_category_breakdown` in `database/queries.py` must exist and be wired to the `/profile` route)

## Routes

- No new routes.
- The existing `GET /profile` route is modified to read two optional query parameters:
  - `date_from` — ISO date string `YYYY-MM-DD`, inclusive lower bound
  - `date_to` — ISO date string `YYYY-MM-DD`, inclusive upper bound
- If either parameter is absent or malformed, the route falls back to an unfiltered "All Time" view — never errors out.

## Database changes

- No database changes.
- The `expenses.date` column (TEXT, `YYYY-MM-DD`) already supports `BETWEEN` comparison in SQLite.

## Templates

- Modify: `templates/profile.html`
  - Add a filter bar section above the summary stats row containing:
    - Four quick-select preset buttons: "This Month", "Last 3 Months", "Last 6 Months", "All Time"
      - Each is a link to `/profile` with the appropriate `date_from`/`date_to` query params computed in `app.py`
      - "All Time" passes no query params (clean `/profile` URL)
    - A custom range sub-form with two `<input type="date">` fields (`date_from`, `date_to`) and an "Apply" submit button
    - The currently active preset or custom range must be visually highlighted with an active state on the button
  - Add a block near the top of the page that displays flashed messages (needed for the invalid-range error; `profile.html` has no flash block from earlier steps)
  - No structural changes to any existing section — only the Jinja variables fed into them change when a filter is active

## Files to change

- `app.py`
  - In the `profile()` view: read `date_from` and `date_to` from `request.args`
  - Validate both values are well-formed ISO dates using `datetime.strptime(value, "%Y-%m-%d")`; on `ValueError` treat as absent
  - Treat an empty-string value (for example `date_from=` from a blank form field) as absent, with no message
  - If `date_from` > `date_to` after validation: treat both as absent, flash "Start date must not be after end date." (equal dates are valid — a single-day range)
  - Compute preset date ranges (e.g. first day of current month for "This Month") in `app.py` — never in the template
  - Pass validated `date_from`, `date_to`, and preset URL params back to the template so the filter bar can reflect the active state
  - Pass `date_from` and `date_to` to each of the three query helpers
- `database/queries.py`
  - `get_summary_stats(user_id, date_from=None, date_to=None)`
    - When both params are provided, add `AND date BETWEEN ? AND ?` to the expenses queries
    - When absent, behave identically to Step 05 (unfiltered)
  - `get_recent_transactions(user_id, limit=10, date_from=None, date_to=None)`
    - Same pattern; ordering newest-first and limit remain unchanged
  - `get_category_breakdown(user_id, date_from=None, date_to=None)`
    - Same pattern; percentage recalculation logic remains unchanged
- `templates/profile.html` — add filter bar (see Templates section above)
- `static/css/profile.css` — add styles for filter bar and active-preset button state using CSS variables only

## Files to create

- `tests/test_date_filter.py` — see Tests to write

## New dependencies

- None

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format dates into SQL; use `?` placeholders even for date-range bounds
- Date validation in `app.py`: use `datetime.strptime(value, "%Y-%m-%d")`; on `ValueError` treat the param as absent (fall back to no filter)
- Preset links must be generated with `url_for("profile", date_from=..., date_to=...)` — never hardcoded URL strings in the template
- When `date_from` and `date_to` are both absent, all three query helpers must behave identically to their Step 05 behaviour (unfiltered)
- If `date_from` > `date_to` after validation, treat both as absent and flash: "Start date must not be after end date." Equal dates are valid.
- Empty-string parameters count as absent and show no message
- If only one of the two dates is present and valid, fall back to the unfiltered view (a filter needs both bounds)
- Preset windows are computed in `app.py` with the standard library only (no new dependencies); `date_to` is always today:
  - "This Month": `date_from` is the first day of the current month
  - "Last 3 Months": `date_from` is the same day of the month, 3 calendar months back, clamped to the last day of that month when the day does not exist (for example 31 May goes back to 28/29 February)
  - "Last 6 Months": same rule, 6 calendar months back
- A preset button is shown as active only when the validated `date_from` and `date_to` exactly equal that preset's computed range; any other valid range is shown as a custom range (custom fields pre-filled, no preset active); no params means "All Time" is active
- "All Time" preset must pass no query params (clean `/profile` URL)
- Preset date calculations must be computed in `app.py`, not in the template
- Use CSS variables — never hardcode hex values
- No inline styles
- All templates extend `base.html`
- Use `url_for()` for every internal link — never hardcode paths

## Tests to write

- File: `tests/test_date_filter.py`
- Test setup: use a temporary database per test run (never the real `spendly.db`), initialised with `init_db()`; insert expenses with known dates for a test user
- Unit tests:

| Function | Input | Expected output |
|---|---|---|
| `get_summary_stats` | `date_from` and `date_to` equal to the first and last expense dates | Includes both boundary expenses (inclusive bounds) |
| `get_summary_stats` | Range containing no expenses | `{"total_spent": 0, "transaction_count": 0, "top_category": "—"}` |
| `get_summary_stats` | No date params | Same result as Step 05 (all expenses) |
| `get_recent_transactions` | Range covering part of the data | Only rows inside the range, newest-first, limit unchanged |
| `get_category_breakdown` | Range covering part of the data | Only categories inside the range; `pct` values sum to 100 |
| `get_category_breakdown` | Range containing no expenses | Empty list |

- Route tests:
  - `GET /profile` with no params → 200; all expenses shown
  - `GET /profile?date_from=<d1>&date_to=<d2>` valid range → 200; only expenses inside the range shown in all three sections
  - `GET /profile` with `date_from` equal to `date_to` → 200; only that day's expenses shown, no error
  - `GET /profile` with `date_from` after `date_to` → 200; unfiltered view; response contains "Start date must not be after end date."
  - `GET /profile?date_from=not-a-date` → 200; unfiltered view; no error message
  - `GET /profile?date_from=&date_to=` (blank fields) → 200; unfiltered view; no error message
  - `GET /profile` with only one valid date → 200; unfiltered view
  - Preset links: the four preset links are present; "All Time" link is a clean `/profile` URL
  - Active state: with no params "All Time" is marked active; with a preset's exact range that preset is marked active; with any other range no preset is marked active and the custom fields are pre-filled
  - 3- and 6-month preset window computation: a day-of-month that does not exist in the target month (for example 31 May) is clamped to the last day of that month

## Definition of done

- [ ] Visiting `/profile` with no query params returns the same data as Step 05 (unfiltered, all expenses)
- [ ] Clicking "This Month" filters all three sections to the current calendar month only
- [ ] Clicking "Last 3 Months" filters to expenses in the 3-month window ending today
- [ ] Clicking "Last 6 Months" filters to expenses in the 6-month window ending today
- [ ] Clicking "All Time" removes any active filter and shows all expenses
- [ ] Submitting a custom date range with valid `date_from` and `date_to` shows only expenses within that range in all three sections
- [ ] Submitting a range where `date_from` > `date_to` shows a flash error and falls back to the unfiltered view
- [ ] Submitting a range where `date_from` equals `date_to` shows that single day's expenses with no error
- [ ] Submitting the custom form with blank date fields shows the unfiltered view with no error
- [ ] The flash error is visible on the profile page and does not appear again on later pages
- [ ] Submitting a malformed date string (e.g. `date_from=not-a-date`) does not crash the app — it silently falls back to the unfiltered view
- [ ] The active preset button or custom-range fields visually indicate which filter is currently applied
- [ ] All amounts continue to display the ₹ symbol regardless of active filter
- [ ] A user with no expenses in the selected range sees ₹0.00 total spent, 0 transactions, and an empty category breakdown — no errors

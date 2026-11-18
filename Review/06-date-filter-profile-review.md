# Review: Spec_06-date-filter-profile_prompt.md vs 06-date-filter-profile.md

**Verdict:** The spec follows the prompt. All 9 required sections are present and in order, and every bullet, signature, rule and checkbox is carried over. Nothing was added or omitted. The prompt itself has several gaps that the spec inherits, and one of them is a real bug risk.

## Format rules

| Rule from prompt | Result |
|---|---|
| Output only the Markdown spec | Pass. The file is just the spec, plus a `# Spec: Step 06` title line. |
| No code, no prose outside sections | Pass. |
| Bullet lists throughout | Pass. |
| Checkbox list for Definition of Done | Pass. |
| Exact section names, no numbers | Pass. |

## Section-by-section

| Section | Result | Notes |
|---|---|---|
| Overview | Match | All four points. |
| Depends on | Match | |
| Routes | Match | Both parameters and the fallback rule. |
| Database changes | Match | |
| Templates | Match | Four presets, custom form, active state, no structural change. |
| Files to change | Match | All three helper signatures, the `app.py` steps, template and CSS. |
| Files to create | Match | None. |
| New dependencies | Match | |
| Rules for implementation | Match | All 11 rules. |
| Definition of done | Match | All 11 checkboxes. |

## Findings

1. **The flash message may never show, and may appear on a later page.** The spec flashes "Start date must be before end date." on `/profile`, but Step 04's template has no flash block. A flashed message stays in the session until a template reads it, so it could surface on the next page that renders flashes (login, add expense) at the wrong time. Add a flash block to `profile.html` and list it under "Templates".
2. **Half-supplied filters fall back silently.** If only "from" is filled, the user gets all expenses with no message. The prompt's wording ("either parameter") makes this intended, but it drops a valid input.
3. **Empty form fields count as malformed.** Submitting the custom form with an empty date sends `date_from=`, which fails `strptime` and falls back quietly. "Clear the filter" and "bad input" look the same.
4. **Same-day ranges are allowed, but the message says otherwise.** Only `date_from > date_to` is rejected, so a single-day range works, yet the text says "must be before end date".
5. **"3-month window ending today" is ambiguous.** It could mean 90 days or three calendar months back. Calendar-month arithmetic without `dateutil` (no new dependencies) needs care at month ends, for example 31 May minus 3 months.
6. **How the active preset is detected is unspecified.** The page must compare the current range with each preset's computed range. It is unclear what happens when a custom range equals a preset, or when "This Month" changes at midnight on the first.
7. **Transaction list is capped, stats are not.** `get_recent_transactions` keeps `limit=10`, while stats count every matching expense. A filtered view can show "25 transactions" next to 10 rows, with no "showing 10 of 25" text.
8. **The prompt repeats itself.** Validation, the flash rule, the "All Time" rule and preset calculation each appear in two or three sections. The spec copies this, so edits can desynchronise.
9. **Presets can look identical on seed data.** The seed expenses sit in the current month, so all date presets show the same data in a manual test.
10. **No tests are specified.** Unlike Step 05, there is no "Tests to write" section, though the Definition of done lists eleven behaviours. Date-boundary cases (inclusive bounds, empty range, malformed input) would make good unit tests.
11. **The filter is not preserved across later actions.** Add, edit and delete (Steps 07-09) redirect to a plain `/profile`, so an active filter is lost after each action.
12. **Location mismatch.** The specs are in the outer `.claude/specs/` folder, while the prompt files and app code are in the nested `Expense_Tracker_Basic-main/` folder.

## Suggested changes (optional)

- Add a flash block to `profile.html` and list it under "Templates".
- Define the 3- and 6-month windows (for example, the same day-of-month back, clamped to month end).
- Treat empty strings as absent without a message, and reword the error to "Start date must not be after end date."
- Add a "Tests to write" section covering inclusive bounds, empty and malformed input, and the unfiltered default.

## Resolution

- Finding 1 (flash not rendered, may leak to later pages): fixed. A flash block was added to the `profile.html` changes, and a Definition of Done item checks the message does not reappear later.
- Finding 3 (empty fields counted as malformed): fixed. Empty strings count as absent with no message.
- Finding 4 (same-day ranges vs error text): fixed. Equal dates are valid and the message is now "Start date must not be after end date."
- Finding 5 (3/6-month windows ambiguous): fixed. Windows are defined as calendar months back from today, clamped to month end, standard library only.
- Finding 6 (active preset detection): fixed. A preset is active only on an exact range match; other ranges show as custom.
- Finding 10 (no tests): fixed. A "Tests to write" section and `tests/test_date_filter.py` were added.
- Finding 2 (half-supplied filters): kept as a documented rule (fall back to unfiltered, no message).
- Findings 7, 8, 9, 11 and 12: not changed. The 10-row cap versus full count (7) and the filter being lost after add/edit/delete (11) need a product decision.

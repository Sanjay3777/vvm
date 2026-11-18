# Review: Spec_08-edit-expense_prompt.md vs 08-edit-expense.md

**Verdict:** The spec follows the prompt. All 11 required sections are present and in order, and every field, helper, rule, test case and checkbox is carried over. Six small deviations were made (listed below). The main gap is reachability: only the ten most recent expenses show an "Edit" link, so older expenses cannot be edited from the UI.

## Format rules

| Rule from prompt | Result |
|---|---|
| Output only the Markdown spec | Pass. The file is just the spec, plus a `# Spec: Step 08` title line. |
| No code, no prose outside sections | Pass. |
| Bullet lists throughout | Pass. |
| Table for unit test cases | Pass. Columns Function, Input, Expected output; 5 rows. |
| Checkbox list for Definition of Done | Pass. |
| Exact section names, no numbers | Pass. |

## Section-by-section

| Section | Result | Notes |
|---|---|---|
| Overview | Match | All six points. |
| Depends on | Match | |
| Routes | Match | |
| Database changes | Match | |
| Templates | Match, with deviations | See deviations 1-3. |
| Files to change | Match, with one deviation | See deviation 4. |
| Files to create | Match, with one addition | See deviation 5. |
| New dependencies | Match | |
| Rules for implementation | Match, with one addition | See deviation 6. |
| Tests to write | Match | All 5 unit rows and all 13 route cases. |
| Definition of done | Match | All 10 checkboxes. |

## Deliberate deviations from the prompt

1. **Form action:** the prompt had the literal `action="/expenses/{{ expense.id }}/edit"`. The spec says the action is generated with `url_for()`.
2. **Edit link:** the prompt had a literal `/expenses/{{ tx.id }}/edit`. The spec says it points to the edit route via `url_for`.
3. **Cancel link:** the prompt said "back to /profile". The spec says the profile page via `url_for`.
4. **Route decorator:** the prompt quoted the `@app.route(...)` line. The spec says "the route must accept both GET and POST methods", because the spec rules say no code.
5. **Test file in "Files to create":** the prompt lists `tests/test_edit_expense.py` only under "Tests to write". It was added to "Files to create" too.
6. **Auth-order note:** added "(checked before any expense lookup)" to the unauthenticated-access rule, so a logged-out user gets a redirect instead of a 404.

## Findings

1. **Older expenses cannot be reached.** The "Edit" link lives in the transactions table, which Step 05 caps at 10 rows (newest-first). An expense outside the 10 newest, or outside an active Step 06 filter, has no link. The URL still works if typed. There is no pagination or "show all" option.
2. **Step 06 changed the helper this step modifies.** `get_recent_transactions` now takes `date_from` and `date_to`. The prompt only says "add `id` to the SELECT"; it should also say the Step 06 parameters and behaviour stay intact. "Depends on" does not list Step 06.
3. **The prompt contradicts itself on paths.** It uses literal paths in the form action and Edit link, and also says never to hardcode paths. The spec follows the rule.
4. **Step 07's validation flaws carry over.** The rules are "identical to Step 07", so unpadded dates such as `2026-3-5` pass `strptime`, `inf` passes the amount check, and the 200-character limit is browser-only.
5. **Silent success when the row disappears.** The handler checks ownership, then calls `update_expense`. If the row is deleted in between, the update affects 0 rows and the user is still redirected as if it worked. `update_expense` does not report rows changed.
6. **Legacy category values.** If a stored category is not one of the 7, the dropdown has nothing to pre-select.
7. **Editing loses the profile filter.** After saving, the redirect goes to a plain `/profile`, so an active Step 06 filter resets.
8. **Test gaps.** No test checks "submitted values retained" on errors, that `get_recent_transactions` returns `id`, that each row has an Edit link, that a POST to another user's expense leaves the row unchanged, or that ₹ appears. There is no rule for isolating the test database.
9. **404 for other users' expenses is a good choice.** It avoids revealing which ids exist. No change needed.
10. **No CSRF protection.** The edit form is open to cross-site request forgery, like the add form. This is a project-wide gap.
11. **Location mismatch.** The specs are in the outer `.claude/specs/` folder, while the prompt files and app code are in the nested `Expense_Tracker_Basic-main/` folder.

## Suggested changes (optional)

- Note that the Step 06 parameters on `get_recent_transactions` must be preserved, and add Step 06 to "Depends on".
- Decide how users reach older expenses (a "show all" link, or pagination).
- Make `update_expense` return the number of rows changed, and return 404 when it is 0.
- Add tests for retained values, the Edit link per row, and "other user's POST leaves the row unchanged".

## Resolution

- Finding 1 (older expenses unreachable): decided and documented. Edit links appear only on rows in the profile list (10 newest within the active filter); older expenses are reached by narrowing the Step 06 date filter. No pagination is added in this step.
- Finding 2 (Step 06 helper signature): fixed. The spec states the Step 06 signature and behaviour must be preserved, and "Depends on" now lists Step 06, with a unit test and a Definition of Done item.
- Finding 4 (Step 07 validation flaws carry over): fixed. The validation rules now match the updated Step 07 rules (finite amount, maximum, two decimals, padded date, 200-character description), with tests.
- Finding 5 (silent success when the row disappears): fixed. `update_expense` returns the rows changed, and the route returns 404 when it is 0.
- Finding 6 (legacy categories): resolved upstream by the Step 01 CHECK constraint on `category`.
- Finding 7 (filter lost after editing): decided. The redirect goes to the unfiltered `/profile`, stated as a rule.
- Finding 8 (test gaps): fixed. Added tests for retained values, `id` in `get_recent_transactions`, the Edit link per row, other-user POST leaving the row unchanged, and ₹; plus a temporary-database rule.
- Findings 3, 9, 10 and 11: not changed. The path contradiction (3) was already resolved with `url_for`, CSRF (10) is project-wide, and the location mismatch (11) is open.

# Review: Spec_07-add-expense_prompt.md vs 07-add-expense.md

**Verdict:** The spec follows the prompt. All 11 required sections are present and in order, and every field, rule, test and checkbox is carried over. Four small deviations were made on purpose (listed below). The prompt has a few contradictions and validation gaps that the spec inherits.

## Format rules

| Rule from prompt | Result |
|---|---|
| Output only the Markdown spec | Pass. The file is just the spec, plus a `# Spec: Step 07` title line. |
| No code, no prose outside sections | Pass. |
| Bullet lists throughout | Pass. |
| Table for unit test cases | Pass. Columns Function, Input, Expected output; 2 rows. |
| Checkbox list for Definition of Done | Pass. |
| Exact section names, no numbers | Pass. |

## Section-by-section

| Section | Result | Notes |
|---|---|---|
| Overview | Match | All five points. |
| Depends on | Match | |
| Routes | Match | |
| Database changes | Match | |
| Templates | Match, with deviations | See deviations 1-3. |
| Files to change | Match | |
| Files to create | Match, with one addition | See deviation 4. |
| New dependencies | Match | |
| Rules for implementation | Match | All 4 validation rules and the other 10 rules. |
| Tests to write | Match | 2 unit rows and all 10 route cases. |
| Definition of done | Match | All 10 checkboxes. |

## Deliberate deviations from the prompt

1. **Form action:** the prompt had the literal `action="/expenses/add"`. The spec says the action is generated with `url_for()`, following the "never hardcode paths" rule.
2. **Cancel link:** the prompt said "back to /profile". The spec says the profile page via `url_for`.
3. **Profile button:** the prompt said "pointing to /expenses/add". The spec says it points to the add-expense route.
4. **Test file in "Files to create":** the prompt lists `tests/test_add_expense.py` only under "Tests to write". It was added to "Files to create" too.

The second unit-test row was reworded as "same as above with `description=None`"; the meaning is unchanged.

## Findings

1. **The prompt contradicts itself on paths.** It specifies a literal form action and cancel link, and also says never to hardcode paths. The spec follows the rule.
2. **Dates like `2026-3-5` pass validation.** `strptime` with `%m` and `%d` accepts unpadded values. The row would be stored as `2026-3-5`, breaking the `YYYY-MM-DD` rule from Step 01 and the date-range filter, which compares dates as text.
3. **`inf` passes amount validation.** `float("inf")` is greater than 0, so it is accepted and stored. There is also no upper limit and no two-decimal rounding on the server (`step="0.01"` is client-side only).
4. **The 200-character limit is client-side only.** No validation rule enforces it, so a crafted POST can store a longer description.
5. **Minor input hygiene is not discussed.** Whitespace-only amounts and surrounding spaces are not covered.
6. **"Defaults to today's date" is unspecified.** It does not say whether the server or the browser fills it, or which timezone counts as "today".
7. **Backdated expenses may not appear.** The Definition of done says a new expense "appears in the transaction list". The list is newest-first and capped at 10 rows (Step 05), so an old-dated expense may not show.
8. **An active filter is lost after saving.** Redirecting to a plain `/profile` drops any Step 06 filter, so a new expense outside the chosen range seems to vanish.
9. **Error display mechanism is vague.** The template has a "flash/error message block" but does not say whether errors use `flash()` or a template variable. Combined with the unresolved flash-block issue on `profile.html`, this is easy to get wrong.
10. **Test coverage is thin on three points.** The Definition of done requires "previously entered values retained", but no test checks that. No test covers the navbar link, the profile button, or `inf` and overlong inputs. The unit table covers only `insert_expense`, not validation.
11. **Test isolation is unspecified.** As in Step 05, there is no rule about a temporary test database.
12. **Session user missing from the database.** If `session["user_id"]` points at a deleted user, the insert hits the foreign key constraint and the route returns a 500.
13. **"Depends on" skips Step 06.** The profile page now has the filter, and it is the redirect target.
14. **No CSRF protection.** Both POST forms (this one and the later edit and delete forms) are open to cross-site request forgery. This is a project-wide gap.
15. **Location mismatch.** The specs are in the outer `.claude/specs/` folder, while the prompt files and app code are in the nested `Expense_Tracker_Basic-main/` folder.

## Suggested changes (optional)

- Require the saved date to be zero-padded `YYYY-MM-DD`, for example by re-formatting after parsing.
- Reject non-finite amounts, set a maximum, and round to two decimals on the server.
- Enforce the 200-character description limit on the server.
- Add tests for retained form values, the navbar link, the profile button and the new validation cases.
- Add Step 06 to "Depends on", and decide whether the redirect should keep the filter.

## Resolution

- Finding 2 (unpadded dates): fixed. The saved date is re-formatted to zero-padded `YYYY-MM-DD`; a test and a Definition of Done item were added.
- Finding 3 (`inf`, no maximum, no rounding): fixed. Amounts must be finite, at most 9999999.99, and are rounded to two decimals.
- Finding 4 (200-character limit client-side only): fixed. The server rejects descriptions over 200 characters.
- Finding 6 ("today's date" unspecified): fixed. The server fills in the default using its local date.
- Finding 7 (backdated expenses may not appear): documented. The Definition of Done item now says "when it is among the 10 newest".
- Finding 8 (filter lost after saving): decided. The redirect goes to the unfiltered `/profile`, stated as a rule.
- Finding 9 (error display mechanism): fixed. Errors use `flash()`, as in registration.
- Finding 10 (test gaps): fixed. Tests were added for retained values, the navbar link, the profile button and the new validation cases.
- Finding 11 (test isolation): fixed. A temporary database per test run is required.
- Finding 12 (session user missing): fixed. The session is cleared and the user is redirected to `/login`.
- Finding 13 ("Depends on" skips Step 06): fixed.
- Findings 1, 5, 14 and 15: not changed. The path contradiction (1) was already resolved with `url_for`, CSRF (14) is project-wide, and the location mismatch (15) is open.

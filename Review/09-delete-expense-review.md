# Review: Spec_09-delete-expense_prompt.md vs 09-delete-expense.md

**Verdict:** The spec follows the prompt. All 11 required sections are present and in order, and every helper, route rule, test and checkbox is carried over. There are four small deliberate deviations (listed below). The prompt contradicts itself about where the confirm dialog is wired, and its inline-style exception conflicts with the rule in Step 04.

## Format rules

| Rule from prompt | Result |
|---|---|
| Output only the Markdown spec | Pass. The file is the spec plus a `# Spec: Step 09` title line the prompt did not ask for. |
| No code, no prose outside sections | Pass. |
| Bullet lists throughout | Pass. |
| Table for unit test cases | Pass. Columns Function, Input, Expected output; 3 rows. |
| Checkbox list for Definition of Done | Pass. |
| Exact section names, no numbers | Pass. |

## Section-by-section

| Section | Result | Notes |
|---|---|---|
| Overview | Match, with one deviation | See deviation 1. |
| Depends on | Match | |
| Routes | Match | POST-only, 405 for GET. |
| Database changes | Match | |
| Templates | Match, with one deviation | See deviation 2. |
| Files to change | Match, with one deviation | See deviation 3. |
| Files to create | Different by one item | See deviation 4. |
| New dependencies | Match | |
| Rules for implementation | Match | All 13 rules. |
| Tests to write | Match | 3 unit rows and all 5 route cases. |
| Definition of done | Match | All 7 checkboxes. |

## Deliberate deviations from the prompt

1. **Overview wording:** the prompt says the `confirm()` dialog is "in the button's onclick handler". The spec says only "a browser-side `confirm()` dialog". The prompt's Templates section puts it on the form's `onsubmit`, so the contradicting phrase was dropped.
2. **Form action:** the prompt had the literal `action="/expenses/{{ tx.id }}/delete"`. The spec says the action is generated with `url_for()`, following the "never hardcode paths" rule.
3. **Route decorator:** the prompt quoted the `@app.route(...)` line. The spec says the route is "registered with `methods=["POST"]` only", because the spec rules say no code.
4. **"Files to create":** the prompt says "None". The spec lists `tests/test_delete_expense.py`, as in earlier steps.

`style="display:inline"` and the `onsubmit` confirm are kept exactly as the prompt wrote them.

## Findings

1. **The prompt contradicts itself on the confirm handler.** Overview says "onclick handler" on the button. Templates and Rules put `onsubmit` on the form. `onsubmit` is the better choice (it also covers Enter-key and other submit paths), and the spec now matches Templates.
2. **The inline-style exception conflicts with Step 04.** Step 04 requires "no inline styles anywhere in `profile.html`", and Steps 06–08 repeat "no inline styles". This step adds `style="display:inline"` to `profile.html`. If a test or lint check enforces the earlier rule, it will fail. A CSS class would avoid the exception.
3. **The prompt contradicts itself on paths.** It uses a literal form action and also says never to hardcode paths. The spec follows the rule. If you want the literal path, the Templates section needs changing back.
4. **The confirmation depends on JavaScript.** With JavaScript disabled or blocked, the form submits with no confirm dialog, so deletion is immediate and permanent. The prompt accepts a client-only confirmation by design.
5. **No CSRF protection on a destructive POST.** A page on another site could submit a hidden form and delete expenses if the browser sends the session cookie. Modern browsers default to `SameSite=Lax`, which blocks most cross-site POSTs, but the app neither sets the flag nor uses a token. This is a project-wide gap.
6. **No success feedback.** The route redirects to `/profile` without a flash message, and `profile.html` still has no flash block (raised in Steps 04 and 06).
7. **Two queries where one would do.** The route calls `get_expense_by_id` and then `delete_expense`. If `delete_expense` returned the number of deleted rows, the route could return 404 when it is 0. The two-step flow also has a small race: a row deleted between the calls gives a silent success. The prompt asks for the two-step flow explicitly.
8. **The danger colour variable may not exist.** The spec says to use "a red-toned CSS variable" and never a hex value. If none is defined, the implementer must add one, and the spec does not say where. `.btn-delete` goes in `style.css`, while the other profile styles are in `profile.css`.
9. **Filter lost and list shifts after delete.** The redirect goes to a plain `/profile`, so an active Step 06 filter resets. With the 10-row cap, deleting a row pulls an older expense into view.
10. **"Depends on" skips Step 06.** Step 06 changed the page and helper behaviour this step builds on.
11. **Test gaps.** No test checks that each row has a Delete form and button with the right action. The confirm-dialog checkbox cannot be tested without a browser, and the spec does not mark it as manual. Nothing checks that a successful delete leaves other users' and other expenses untouched. There is no rule for isolating the test database.
12. **Location mismatch.** The specs are in the outer `.claude/specs/` folder, while the prompt files and app code are in the nested `Expense_Tracker_Basic-main/` folder.

## Suggested changes (optional)

- Replace the inline `display:inline` style with a CSS class, so the "no inline styles" rule holds everywhere.
- Make `delete_expense` return the number of rows deleted, and return 404 when it is 0.
- Add a flash block to `profile.html` and a success message after delete.
- Add a test for the Delete form on each row, and mark the confirm dialog as a manual check.
- Add Step 06 to "Depends on".

## Resolution

- Finding 2 (inline-style exception conflicts with Step 04): fixed. The `style="display:inline"` exception was removed; the form uses an `inline-form` CSS class, and the rules now say no inline `style` attributes anywhere. A test checks the page source for `style=`.
- Finding 4 (confirmation depends on JavaScript): documented as an accepted limitation.
- Finding 6 (no success feedback): fixed. The route flashes "Expense deleted." (the flash block exists since Step 06), with a test and a Definition of Done item.
- Finding 7 (two queries, small race): fixed. `delete_expense` returns the rows deleted and the route returns 404 when it is 0.
- Finding 8 (danger colour variable may not exist): fixed. The spec says to define one in the root variable block of `style.css` if missing.
- Finding 9 (filter lost, list shifts): documented. The redirect goes to the unfiltered `/profile`, and a shifted list is expected.
- Finding 10 ("Depends on" skips Step 06): fixed.
- Finding 11 (test gaps): fixed. Added a test for the delete form on each row, a test that other rows stay untouched, a temporary-database rule, and a manual-check note for the confirm dialog.
- Findings 1, 3, 5 and 12: not changed. The `onclick`/`onsubmit` contradiction (1) and the path contradiction (3) were already resolved in the spec; CSRF (5) is project-wide; the location mismatch (12) is open.

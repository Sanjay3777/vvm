# Review: Spec_04_Profilepage_prompt.md vs 04-profile.md

**Verdict:** The spec follows the prompt. All 10 required sections are present and in order, and every bullet from the prompt is covered. There are no omissions and no content added beyond the prompt. One gap is still open: the navbar requirement has no matching file change.

## Format rules

| Rule from prompt | Result |
|---|---|
| Output only the Markdown spec | Pass. The file is just the spec, plus a `# Spec: Step 04` title line. |
| No code, no prose outside sections | Pass. |
| Bullet lists throughout | Pass. |
| Numbered list for the four template sections | Pass. Items 1-4 under "Must contain four sections". |
| Checkbox list for Definition of Done | Pass. |
| Exact section names, no numbers | Pass. |

## Section-by-section

| Section | Result | Notes |
|---|---|---|
| Overview | Match | All four points. |
| Depends on | Match | |
| Routes | Match | |
| Database changes | Match | |
| Templates | Match | All four sections, same detail and minimum counts. |
| Files to change | Match | Only `app.py`, as in the prompt. |
| Files to create | Match | |
| New dependencies | Match | |
| Rules for implementation | Match | All 9 rules. |
| Definition of done | Match | All 8 checkboxes. |

## Findings

1. **The navbar requirement has no owner.** The Definition of done says the navbar shows the logged-in state (username and logout link). That lives in `base.html`, which the prompt does not list under "Files to change". Add `base.html` there, with a line saying the navbar shows the username and a logout link when `session.user_id` is set.
2. **No CSS file is named.** The rules require CSS variables, a badge class and no inline styles, but no stylesheet is listed to hold the styles. Step 05's structure later shows `static/css/profile.css`. Add it to "Files to create".
3. **"Username" has no source.** The navbar and info card need a name, but the hardcoded user dict comes from `app.py`, not the session. The hardcoded name will not match the logged-in user until Step 05.
4. **Hardcoded data is not tied to the seed.** Step 05 expects the seed user ("Demo User", 8 expenses, ₹346.24). Nothing here requires the hardcoded values to resemble it, so the switch to live data would show a visible change.
5. **Currency is not specified.** Amounts appear in the table, stats and breakdown, but no currency symbol is named. Step 05 later requires ₹.
6. **No tests.** The Definition of done lists route behaviours (302 redirect, 200 when logged in), and this step has no test file. Step 05 is the first with tests.
7. **Location mismatch.** The specs are in the outer `.claude/specs/` folder, while the prompt files and app code are in the nested `Expense_Tracker_Basic-main/` folder.

## Suggested changes (optional)

- Add `templates/base.html` to "Files to change" for the navbar, and name the stylesheet in "Files to create".
- Add a rule that amounts use the ₹ symbol, and that hardcoded values mirror the seed data.
- Add a rule for where the navbar username comes from.

## Resolution

- Finding 1 (navbar has no owner): fixed. `base.html` added to "Templates" and "Files to change".
- Finding 2 (no CSS file named): fixed. `static/css/profile.css` added to "Templates", "Files to create" and the Definition of Done.
- Finding 3 (username has no source): fixed. The navbar uses the name from the hardcoded user dict on `/profile`, and a "Profile" link on other pages, until Step 05.
- Finding 4 (hardcoded data not tied to the seed): fixed. A rule and a Definition of Done item require the values to mirror the Step 01 seed data.
- Finding 5 (currency not specified): fixed. A ₹ rule and a Definition of Done item were added.
- Finding 6 (no tests): not changed. It was not in the suggested changes.
- Finding 7 (location mismatch): not changed.

# Review: Spec_02_Registration.prompt.md vs 02-registration.md

**Verdict:** The spec follows the prompt. All 10 required sections are present and in order, and no item from the prompt is missing. The only difference is cosmetic formatting.

## Format rules

| Rule from prompt | Result |
|---|---|
| Output only the Markdown spec | Pass. The file is just the spec, plus a `# Spec: Step 02` title line. |
| No code, no prose outside sections | Pass. |
| Bullet lists throughout, no tables | Pass. No tables. |
| Checkbox list for Definition of Done | Pass. |
| Section names exactly as listed, no numbers | Pass. The prompt's mixed-case names ("Files to change", "Definition of done") are kept. |

## Section-by-section

| Section | Result | Notes |
|---|---|---|
| Overview | Match | All four points. |
| Depends on | Match | |
| Routes | Match | Both GET and POST, same wording. |
| Database changes | Match | `create_user` has all four behaviours: hash, insert, return id, raise `IntegrityError`. |
| Templates | Match | All four modifications, including keeping the visual design unchanged. |
| Files to change | Match | |
| Files to create | Match | |
| New dependencies | Match | |
| Rules for implementation | Match | All 10 rules. The three-step validation order is a nested numbered list. |
| Definition of done | Match | All 7 checkboxes, same wording. |

## Findings

1. **No required content is missing and nothing was added.** Wording is nearly verbatim; code identifiers are in backticks.
2. **Validation order and the duplicate-email check.** The email is only checked at insert time (catching `IntegrityError`). This avoids a check-then-insert race, but the first two checks must run before any insert. The spec states this order.
3. **`abort(405)` is redundant.** Flask already returns 405 for methods not listed on a route. It only matters if the route accepts more methods than GET and POST.
4. **Whitespace and email format are not specified.** "Non-empty" does not say whether a whitespace-only name counts. There is no email-format or password-length rule, and no email normalisation, so `Demo@Spendly.com` and `demo@spendly.com` could register as two users.
5. **Form values are lost on error.** Nothing says to keep the typed name and email when the form re-renders (Steps 07 and 08 do require it).
6. **Hardcoded secret key.** Fine for now per the prompt, but it should come from an environment value before deployment.
7. **Location mismatch.** The specs are in the outer `.claude/specs/` folder, while the prompt files and app code are in the nested `Expense_Tracker_Basic-main/` folder.

## Suggested changes (optional)

- Add an input-hygiene rule: trim the name and email, lower-case the email, and treat whitespace-only values as empty.
- Add a rule to keep the submitted name and email when the form re-renders.

## Resolution

- Finding 4 (whitespace and email normalisation): fixed. An input-hygiene rule (strip name and email, lower-case email, whitespace-only counts as empty, passwords untouched) and two Definition of Done items were added.
- Finding 5 (form values lost on error): fixed. The spec now keeps name and email pre-filled and never re-populates passwords; a Definition of Done item was added.
- Finding 6 (hardcoded secret key): fixed. The rule now says the dev string must be replaced from the environment before deployment.
- Finding 3 (`abort(405)` redundant): left as the prompt wrote it.
- Finding 7 (location mismatch): not changed. It affects all specs and needs your decision.
- Follow-up: Step 03 login must also strip and lower-case the email, or registered users will not match at login.

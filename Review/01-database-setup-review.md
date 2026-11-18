# Review: Spec_01_database_setup_prompt.md vs 01-database-setup.md

**Verdict:** The spec follows the prompt. All 14 sections are present, numbered and in order, and nothing the prompt required is missing. The only deviations are small additions.

## Format rules

| Rule from prompt | Result |
|---|---|
| Output only the Markdown spec | Pass. The file is just the spec, plus a `# Spec: Step 1` title line. |
| No code, no prose outside sections | Pass. Function names and SQL keywords appear only as inline identifiers. |
| Tables for schema definitions | Pass. Both `users` and `expenses` use tables. |
| Checkbox lists for Definition of Done | Pass. |
| Number all sections exactly as listed | Pass. Sections 1-14 use the prompt's names. |

## Section-by-section

| # | Section | Result | Notes |
|---|---|---|---|
| 1 | Overview | Match | Covers the foundational role; names auth, profile and expense tracking as dependents. |
| 2 | Depends on | Match | |
| 3 | Routes | Match | |
| 4 | Database Schema | Match, with additions | Every column has a type and constraints; `YYYY-MM-DD` note is on `expenses.date`. Added `NOT NULL DEFAULT CURRENT_TIMESTAMP` to `created_at`, `NULL allowed` to `description`, and a pointer from `category` to Section 10. |
| 5 | Functions to Implement | Match, different format | All three functions match. A table replaces bullets, plus a `seed_db()` data table. |
| 6 | Changes to app.py | Match | |
| 7 | Files to Change | Match | |
| 8 | Files to Create | Match | |
| 9 | Dependencies | Match | |
| 10 | Categories | Match | Seven values as a bullet list. |
| 11 | Rules for Implementation | Match | All seven rules, same wording. |
| 12 | Expected Behavior | Match, with additions | Both required topics covered. Added three constraint rows (AUTOINCREMENT, `created_at` default, NOT NULL columns). |
| 13 | Error Handling | Match | All three scenarios. |
| 14 | Definition of Done | Match | All eight checkboxes, same wording. |

## Findings

1. **No required content is missing.** The additions in Sections 4, 5 and 12 expand on the prompt without contradicting it.
2. **Category is not enforced by the database.** Section 10 says the seven values are the only valid ones, but nothing in the schema or Section 12 enforces that (no CHECK constraint). The prompt did not ask for one.
3. **Seed amounts and dates are unspecified.** The prompt says "dates spread across the current month" and gives no amounts. Dates could land after today. The Step 05 spec expects a total of 346.24 and "Bills" as top category, which this spec does not guarantee.
4. **`CURRENT_TIMESTAMP` format.** It gives `YYYY-MM-DD HH:MM:SS`, which suits Step 05's "Month YYYY" parsing, but conflicts with "Dates must always be YYYY-MM-DD" if that rule is read as covering `created_at`. The spec limits that rule to `expenses.date`.
5. **Location mismatch.** The specs are in the outer `.claude/specs/` folder, while the prompt files and app code are in the nested `Expense_Tracker_Basic-main/` folder.

## Suggested changes (optional)

- Pin the seed amounts, and keep the dates on or before today, so the Step 05 expectations hold.
- Optionally add a CHECK constraint for `category` and date format.

## Resolution

- Finding 2 (category/date not enforced): fixed. CHECK constraints added to the schema, Section 12, Section 13 and the Definition of Done.
- Finding 3 (seed amounts and dates): fixed. A pinned 8-row seed table (total 346.24, Bills highest, no future dates) was added to Section 5, plus a Definition of Done item.
- Finding 4 (`created_at` format): fixed. Section 11 now says the YYYY-MM-DD rule applies to `expenses.date` and `created_at` uses `CURRENT_TIMESTAMP` format.
- Finding 5 (location mismatch): not changed. It affects all specs and needs your decision.

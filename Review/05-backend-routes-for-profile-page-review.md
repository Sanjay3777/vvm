# Review: Spec_05-backend-routes-for-profile-page_prompt.md vs 05-backend-routes-for-profile-page.md

**Verdict:** The spec follows the prompt. All 11 required sections are present and in order, and every bullet, function signature, test case and checkbox is carried over. One small addition was made. Most of the risk is in the prompt itself, mainly the seed-data assumptions.

## Format rules

| Rule from prompt | Result |
|---|---|
| Output only the Markdown spec | Pass. The file is just the spec, plus a `# Spec: Step 05` title line. |
| No code, no prose outside sections | Pass. Function signatures are inline identifiers. |
| Bullet lists throughout | Pass. |
| Table for unit test cases | Pass. Columns Function, Input, Expected output; 8 rows. |
| Checkbox list for Definition of Done | Pass. |
| Exact section names, no numbers | Pass. |

## Section-by-section

| Section | Result | Notes |
|---|---|---|
| Overview | Match | All four points, including the subagents line. |
| Depends on | Match | |
| Routes | Match | |
| Database changes | Match | |
| Templates | Match | Both the ₹ rule and the "no structural changes" note. |
| Files to change | Match | |
| Files to create | Match, with one addition | All four helpers with return shapes. Also listed `tests/test_backend_connection.py` here; the prompt names it only under "Tests to write". |
| New dependencies | Match | |
| Rules for implementation | Match | All 10 rules. |
| Tests to write | Match | All 8 unit cases and all 10 route assertions. |
| Definition of done | Match | All 8 checkboxes. |

## Findings

1. **Seed amounts are not pinned.** The prompt requires a ₹346.24 total, 8 transactions and "Bills" as top category. Spec 01 only says "8 expenses covering all 7 categories" with no amounts. These assertions pass only if the seed rows happen to match. Pin exact amounts in Spec 01, or compute expected values from the database in the tests.
2. **"Highest single-category total" is ambiguous.** Eight expenses across 7 categories means one category has two. "Bills" must win by sum; the parenthetical does not say whether that means the largest single expense or the largest category total.
3. **The subagents line is not a product requirement.** "Three parallel subagents handle the three independent data concerns" describes how the work is done, and it sits in Overview. There are also four helpers, and `get_user_by_id` has no subagent.
4. **Zero versus formatted display.** Unit tests expect `total_spent` to be the number `0`, while the Definition of done expects "₹0.00". The spec does not say whether the template or the helper formats two decimals.
5. **Missing-user behaviour is undefined.** If `session["user_id"]` points at a user that no longer exists, `get_user_by_id` returns `None` and the route has no defined behaviour.
6. **Test setup is not specified.** Tests run against "the seed user" and a "user with no expenses", but nothing says how the test database is created, isolated or reset.
7. **Transaction ids are missing.** `get_recent_transactions` returns no `id`; Step 08 later modifies the helper to add it.
8. **`member_since` parsing.** `created_at` is SQLite's UTC `CURRENT_TIMESTAMP` string. "Month YYYY" works with it; a month boundary could differ by timezone, which is unlikely to matter.
9. **Rounding rule works but is untested.** The "adjust the largest category" rule is only checked indirectly. No test covers a case where rounding would give 99 or 101.
10. **Location mismatch.** The specs are in the outer `.claude/specs/` folder, while the prompt files and app code are in the nested `Expense_Tracker_Basic-main/` folder.

## Suggested changes (optional)

- Pin the exact seed amounts in Spec 01, and clarify that "top category" means the largest category sum.
- Add a rule for a missing user, for example clear the session and redirect to `/login`.
- Add a test-fixture rule, for example a temporary database per test run.
- Add a unit test for the rounding adjustment.

## Resolution

- Finding 1 (seed amounts not pinned): fixed upstream. Spec 01 now pins the 8 seed expenses (total 346.24, Bills highest); "Depends on" in this spec references them.
- Finding 2 ("highest single-category total" ambiguous): fixed. A rule defines `top_category` as the highest summed amount, with a unit test where the largest single expense is in the lower-total category.
- Finding 4 (zero versus formatted display): fixed. Helpers return plain numbers; the template formats ₹ with two decimals.
- Finding 5 (missing-user behaviour): fixed. The view clears the session and redirects to `/login`; a route test covers it.
- Finding 6 (test setup): fixed. A "Test setup" rule requires a temporary database per test run.
- Finding 9 (rounding rule untested): fixed. A unit test with three equal categories checks the remainder goes to the largest.
- Also added: a route test for the brand-new user empty state (the last Definition of Done item had no matching test), and a `member_since` format test.
- Finding 3 (subagents line in Overview): kept, as the original prompt wrote it.
- Finding 7 (no `id` in `get_recent_transactions`): not changed; Step 08 adds it.
- Findings 8 and 10: not changed.

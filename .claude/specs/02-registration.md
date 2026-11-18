# Spec: Step 02 — User Registration

## Overview

- This step upgrades the existing stub `GET /register` route into a fully functional registration route that handles both GET and POST.
- The form accepts `name`, `email`, `password`, and `confirm_password`.
- On success: flash a success message and redirect to `/login`.
- This is the entry point for all authenticated features.

## Depends on

- Step 01 — Database setup (`users` table, `get_db()`)

## Routes

- `GET /register` — render registration form — public (already exists as a stub; upgrade it)
- `POST /register` — process form, validate input, insert user, redirect to `/login` — public

## Database changes

- No new tables or columns.
- The existing `users` table covers all requirements.
- One new DB helper to add to `database/db.py`: `create_user(name, email, password)`
  - Hashes the password with werkzeug
  - Inserts a row into `users`
  - Returns the new user's id
  - Raises `sqlite3.IntegrityError` if the email is already taken (UNIQUE constraint)

## Templates

- Modify `templates/register.html`:
  - Change the form action to `url_for('register')` with `method="post"`
  - Add `name` attributes to all inputs: `name`, `email`, `password`, `confirm_password`
  - Add a block to display flashed error messages (e.g. "Email already registered", "Passwords do not match")
  - Keep all existing visual design unchanged

## Files to change

- `app.py` — upgrade `register()` to handle GET and POST; add flash + redirect logic
- `database/db.py` — add `create_user()` helper
- `templates/register.html` — wire up form action/method and flash message display

## Files to create

- None

## New dependencies

- None — uses `werkzeug.security` (already installed) and Flask's built-in `flash`, `redirect`, `url_for`

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never use f-strings in SQL
- Hash passwords with `werkzeug.security.generate_password_hash` — never store plaintext
- `app.secret_key` must be set in `app.py` for `flash()` to work (use a hardcoded dev string for now; it must be replaced by a value from the environment before any deployment)
- Input hygiene, applied before validation:
  - Strip leading and trailing whitespace from `name` and `email`
  - Lower-case `email`, so `Demo@Spendly.com` and `demo@spendly.com` are the same account
  - A value that is empty after stripping counts as empty
  - Do not strip or alter `password` and `confirm_password`
- Server-side validation must check in this order:
  - 1. All fields are non-empty (after input hygiene)
  - 2. `password` == `confirm_password`
  - 3. Email is not already registered (catch `sqlite3.IntegrityError`)
- On any validation failure: re-render the form with a flashed error — do not redirect
  - Keep the submitted `name` and `email` pre-filled in the re-rendered form
  - Never re-populate `password` or `confirm_password`
- On success: flash a success message and redirect to `url_for('login')`
- Use `abort(405)` if an unsupported HTTP method reaches the route
- All templates must extend `base.html`
- Use CSS variables — never hardcode hex values
- Use `url_for()` for every internal link — never hardcode URLs

## Definition of done

- [ ] `GET /register` renders the registration form without errors
- [ ] Submitting with all valid fields creates a new user in `users` and redirects to `/login`
- [ ] Submitting with mismatched passwords re-renders the form with an error, no DB insert
- [ ] Submitting with an already-registered email re-renders with "Email already registered"
- [ ] Submitting with any empty field re-renders with a validation error
- [ ] Submitting a whitespace-only name or email is treated as empty
- [ ] Registering `Demo@Spendly.com` when `demo@spendly.com` exists re-renders with "Email already registered"
- [ ] After a validation failure the name and email stay filled in and the password fields are empty
- [ ] Password is stored as a hash — never plaintext — verifiable by inspecting `spendly.db`
- [ ] No duplicate user is created on repeated valid submissions with the same email

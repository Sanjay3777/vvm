import calendar
import math
import os
import sqlite3
import warnings
from datetime import date, datetime

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from database.db import (
    CATEGORIES,
    create_user,
    get_db,
    get_user_by_email,
    init_db,
    seed_db,
)
from database.queries import (
    delete_expense as delete_expense_record,
    get_category_breakdown,
    get_category_totals,
    get_expense_by_id,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
    insert_expense,
    update_expense,
)

app = Flask(__name__)
# Session signing key comes from the SECRET_KEY environment variable.
app.secret_key = os.environ.get("SECRET_KEY")
if not app.secret_key:
    # No key configured: use a random one so no known key ever signs sessions.
    # Sessions will not survive a restart. Set SECRET_KEY to keep them.
    warnings.warn("SECRET_KEY is not set; using a random key for this run.")
    app.secret_key = os.urandom(32)

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    if request.method != "POST":
        abort(405)

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    error = None
    if not name or not email or not password or not confirm_password:
        error = "All fields are required."
    elif password != confirm_password:
        error = "Passwords do not match."
    else:
        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            error = "Email already registered."

    if error:
        flash(error, "error")
        return render_template("register.html", name=name, email=email)

    flash("Account created. Please sign in.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = get_user_by_email(email) if email else None
    if user is None or not check_password_hash(user["password_hash"], password):
        flash("Invalid email or password.", "error")
        return render_template("login.html", email=email)

    session.clear()
    session["user_id"] = user["id"]
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


def _months_back(d, months):
    """The date `months` calendar months before d, clamped to the end of that month."""
    total = d.year * 12 + (d.month - 1) - months
    year, month = divmod(total, 12)
    month += 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def _preset_ranges(today):
    today_iso = today.isoformat()
    return [
        {"label": "This Month", "date_from": today.replace(day=1).isoformat(), "date_to": today_iso},
        {"label": "Last 3 Months", "date_from": _months_back(today, 3).isoformat(), "date_to": today_iso},
        {"label": "Last 6 Months", "date_from": _months_back(today, 6).isoformat(), "date_to": today_iso},
        {"label": "All Time", "date_from": None, "date_to": None},
    ]


def _parse_iso_date(value):
    """Return a zero-padded ISO date string, or None if the value is absent or malformed."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    user_id = session["user_id"]
    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    user["initials"] = "".join(w[0] for w in user["name"].split()[:2]).upper() or "?"

    date_from = _parse_iso_date(request.args.get("date_from"))
    date_to = _parse_iso_date(request.args.get("date_to"))
    if date_from and date_to and date_from > date_to:
        flash("Start date must not be after end date.", "error")
        date_from = date_to = None
    elif not (date_from and date_to):
        date_from = date_to = None

    totals = get_category_totals(user_id, date_from, date_to)
    presets = _preset_ranges(date.today())
    for preset in presets:
        preset["active"] = (preset["date_from"], preset["date_to"]) == (date_from, date_to)
    custom_active = bool(date_from) and not any(p["active"] for p in presets)

    return render_template(
        "profile.html",
        user=user,
        stats=get_summary_stats(user_id, date_from, date_to, totals=totals),
        expenses=get_recent_transactions(user_id, date_from=date_from, date_to=date_to),
        categories=get_category_breakdown(user_id, date_from, date_to, totals=totals),
        presets=presets,
        date_from=date_from,
        date_to=date_to,
        custom_active=custom_active,
    )


def _expense_form_from_request():
    return {
        "amount": request.form.get("amount", "").strip(),
        "category": request.form.get("category", ""),
        "date": request.form.get("date", "").strip(),
        "description": request.form.get("description", "").strip(),
    }


def _validate_expense_form(form):
    """Shared by add and edit. Returns (error, amount, iso_date); error is None when valid."""
    if not form["amount"]:
        return "Amount is required.", None, None
    try:
        amount = float(form["amount"])
    except ValueError:
        return "Amount must be a number.", None, None
    if not math.isfinite(amount) or amount <= 0 or amount > 9999999.99:
        return "Amount must be greater than 0 and at most 9999999.99.", None, None
    amount = round(amount, 2)
    if form["category"] not in CATEGORIES:
        return "Choose a valid category.", None, None
    try:
        iso_date = datetime.strptime(form["date"], "%Y-%m-%d").date().isoformat()
    except ValueError:
        return "Enter a valid date.", None, None
    if len(form["description"]) > 200:
        return "Description must be 200 characters or fewer.", None, None
    return None, amount, iso_date


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    if get_user_by_id(user_id) is None:
        session.clear()
        return redirect(url_for("login"))

    if request.method == "GET":
        form = {
            "amount": "",
            "category": "",
            "date": date.today().isoformat(),
            "description": "",
        }
        return render_template("add_expense.html", form=form, categories=CATEGORIES)

    form = _expense_form_from_request()
    error, amount, iso_date = _validate_expense_form(form)
    if error:
        flash(error, "error")
        return render_template("add_expense.html", form=form, categories=CATEGORIES)

    insert_expense(user_id, amount, form["category"], iso_date, form["description"] or None)
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, user_id)
    if expense is None:
        abort(404)

    if request.method == "GET":
        form = {
            "amount": f"{expense['amount']:.2f}",
            "category": expense["category"],
            "date": expense["date"],
            "description": expense["description"] or "",
        }
        return render_template(
            "edit_expense.html", form=form, categories=CATEGORIES, expense_id=id
        )

    form = _expense_form_from_request()
    error, amount, iso_date = _validate_expense_form(form)
    if error:
        flash(error, "error")
        return render_template(
            "edit_expense.html", form=form, categories=CATEGORIES, expense_id=id
        )

    changed = update_expense(
        id, user_id, amount, form["category"], iso_date, form["description"] or None
    )
    if changed == 0:
        abort(404)
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    if get_expense_by_id(id, user_id) is None:
        abort(404)
    if delete_expense_record(id, user_id) == 0:
        abort(404)
    flash("Expense deleted.", "success")
    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)

import datetime

import pytest

from database import db, queries

CATS = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def expense_count():
    conn = db.get_db()
    n = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    conn.close()
    return n


def last_expense():
    conn = db.get_db()
    row = conn.execute("SELECT * FROM expenses ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return row


def login_session(client, user_id=1):
    with client.session_transaction() as s:
        s["user_id"] = user_id


def post(client, **overrides):
    data = dict(amount="50.0", category="Food", date="2026-03-20", description="Lunch")
    data.update(overrides)
    data = {k: v for k, v in data.items() if v is not None}
    return client.post("/expenses/add", data=data)


# ---------------- Task 1 ----------------

def test_insert_expense_row_inserted(db_path):
    db.init_db()
    db.seed_db()
    new_id = queries.insert_expense(1, 50.0, "Food", "2026-03-20", "Lunch")
    conn = db.get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    assert (row["user_id"], row["amount"], row["category"], row["date"], row["description"]) == (
        1, 50.0, "Food", "2026-03-20", "Lunch")


def test_insert_expense_null_description(db_path):
    db.init_db()
    db.seed_db()
    new_id = queries.insert_expense(1, 50.0, "Food", "2026-03-20", None)
    conn = db.get_db()
    row = conn.execute("SELECT description FROM expenses WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    assert row["description"] is None


# ---------------- Task 2 ----------------

def test_get_unauthenticated_redirects(client):
    r = client.get("/expenses/add")
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")


def test_post_unauthenticated_redirects(client):
    before = expense_count()
    r = post(client)
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")
    assert expense_count() == before


def test_get_form(client):
    login_session(client)
    r = client.get("/expenses/add")
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert 'method="POST"' in body and 'action="/expenses/add"' in body
    assert 'name="amount"' in body and 'name="description"' in body
    select = body.split('<select name="category"')[1].split("</select>")[0]
    options = [o.split(">")[1].split("<")[0] for o in select.split("<option")[1:]]
    assert options == CATS
    assert "Save Expense" in body
    assert 'href="/profile"' in body
    assert f'value="{datetime.date.today().isoformat()}"' in body


def test_valid_post_redirects_and_inserts(client):
    login_session(client)
    before = expense_count()
    r = post(client)
    assert r.status_code == 302 and r.headers["Location"].endswith("/profile")
    assert expense_count() == before + 1
    row = last_expense()
    assert (row["user_id"], row["amount"], row["category"], row["date"], row["description"]) == (
        1, 50.0, "Food", "2026-03-20", "Lunch")
    assert "Lunch" in client.get("/profile").get_data(as_text=True)


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": None},
        {"amount": ""},
        {"amount": "0"},
        {"amount": "-5"},
        {"amount": "abc"},
        {"amount": "inf"},
        {"amount": "nan"},
        {"amount": "1e999"},
        {"amount": "10000000"},
        {"category": "Travel"},
        {"category": "food"},
        {"category": None},
        {"date": "2026-13-45"},
        {"date": "not-a-date"},
        {"date": ""},
        {"description": "x" * 201},
    ],
)
def test_error_cases(client, overrides):
    login_session(client)
    before = expense_count()
    r = post(client, **overrides)
    assert r.status_code == 200
    assert 'class="auth-error"' in r.get_data(as_text=True)
    assert expense_count() == before


def test_no_description_stores_null(client):
    login_session(client)
    assert post(client, description=None).status_code == 302
    assert last_expense()["description"] is None


def test_whitespace_description_stores_null(client):
    login_session(client)
    assert post(client, description="   ").status_code == 302
    assert last_expense()["description"] is None


def test_description_length_boundary(client):
    login_session(client)
    assert post(client, description="x" * 200).status_code == 302
    assert len(last_expense()["description"]) == 200
    before = expense_count()
    assert post(client, description="x" * 201).status_code == 200
    assert expense_count() == before


def test_amount_rounded_and_stripped(client):
    login_session(client)
    post(client, amount="12.345")
    assert last_expense()["amount"] == 12.35
    post(client, amount="  50  ")
    assert last_expense()["amount"] == 50.0
    assert post(client, amount="9999999.99").status_code == 302
    assert last_expense()["amount"] == 9999999.99


def test_date_zero_padded(client):
    login_session(client)
    assert post(client, date="2026-3-5").status_code == 302
    assert last_expense()["date"] == "2026-03-05"


def test_failure_repopulates_values(client):
    login_session(client)
    r = post(client, amount="abc", category="Health", date="2026-04-01", description="Doctor")
    body = r.get_data(as_text=True)
    assert 'value="abc"' in body
    assert 'value="2026-04-01"' in body
    assert 'value="Doctor"' in body
    assert '<option value="Health" selected' in body


def test_html_in_description_escaped(client):
    login_session(client)
    body = post(client, amount="abc", description="<script>x</script>").get_data(as_text=True)
    assert "&lt;script&gt;" in body and "<script>x" not in body


def test_unsupported_method_405(client):
    login_session(client)
    assert client.put("/expenses/add").status_code == 405


def test_missing_session_user(client):
    login_session(client, 999)
    before = expense_count()
    r = post(client)
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")
    assert expense_count() == before
    with client.session_transaction() as s:
        assert "user_id" not in s
    login_session(client, 999)
    r = client.get("/expenses/add")
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")


def test_profile_has_add_expense_link(client):
    login_session(client)
    body = client.get("/profile").get_data(as_text=True)
    assert 'href="/expenses/add"' in body and "Add Expense" in body


def test_navbar_add_expense_link(client):
    login_session(client)
    assert 'href="/expenses/add"' in client.get("/").get_data(as_text=True)
    with client.session_transaction() as s:
        s.clear()
    assert 'href="/expenses/add"' not in client.get("/").get_data(as_text=True)

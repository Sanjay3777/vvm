import sqlite3

import pytest
from werkzeug.security import check_password_hash

from database import db


def count_users():
    conn = db.get_db()
    n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return n


def get_user(email):
    conn = db.get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row


def post(client, **overrides):
    data = dict(
        name="Asha",
        email="asha@example.com",
        password="secret123",
        confirm_password="secret123",
    )
    data.update(overrides)
    return client.post("/register", data=data)


# ---------------- Task 1: create_user ----------------

def test_create_user_returns_id_and_hashes_password(db_path):
    db.init_db()
    uid = db.create_user("A", "a@x.com", "secret123")
    row = get_user("a@x.com")
    assert row["id"] == uid
    assert row["password_hash"] != "secret123"
    assert check_password_hash(row["password_hash"], "secret123")


def test_create_user_duplicate_email_raises(db_path):
    db.init_db()
    db.create_user("A", "a@x.com", "secret123")
    with pytest.raises(sqlite3.IntegrityError):
        db.create_user("B", "a@x.com", "other")
    assert count_users() == 1


# ---------------- Task 2: route ----------------

def test_get_register_renders_form(client):
    r = client.get("/register")
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert 'name="confirm_password"' in body
    assert 'action="/register"' in body
    assert 'method="POST"' in body


def test_valid_registration_redirects_to_login(client):
    r = post(client)
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/login")
    row = get_user("asha@example.com")
    assert row is not None and row["password_hash"] != "secret123"
    page = client.get("/login").get_data(as_text=True)
    assert "Account created" in page


def test_mismatched_passwords(client):
    r = post(client, confirm_password="different")
    assert r.status_code == 200
    assert "Passwords do not match" in r.get_data(as_text=True)
    assert count_users() == 1


@pytest.mark.parametrize("field", ["name", "email", "password", "confirm_password"])
def test_each_empty_field(client, field):
    r = post(client, **{field: ""})
    assert r.status_code == 200
    assert "All fields are required" in r.get_data(as_text=True)
    assert count_users() == 1


@pytest.mark.parametrize("field", ["name", "email"])
def test_whitespace_only_name_and_email(client, field):
    r = post(client, **{field: "   "})
    assert r.status_code == 200
    assert "All fields are required" in r.get_data(as_text=True)
    assert count_users() == 1


def test_duplicate_email(client):
    r = post(client, email="demo@spendly.com")
    assert r.status_code == 200
    assert "Email already registered" in r.get_data(as_text=True)


def test_duplicate_email_case_and_spaces(client):
    r = post(client, email="  Demo@Spendly.com ")
    assert r.status_code == 200
    assert "Email already registered" in r.get_data(as_text=True)
    assert count_users() == 1


def test_email_stored_lowercase_and_name_stripped(client):
    post(client, name="  Asha  ", email="  Asha@Example.COM ")
    row = get_user("asha@example.com")
    assert row is not None and row["name"] == "Asha"


def test_failure_keeps_name_and_email_not_passwords(client):
    r = post(client, confirm_password="different")
    body = r.get_data(as_text=True)
    assert 'value="Asha"' in body
    assert 'value="asha@example.com"' in body
    assert "secret123" not in body
    assert "different" not in body


def test_password_with_spaces_stored_unaltered(client):
    post(client, password=" pass word ", confirm_password=" pass word ")
    row = get_user("asha@example.com")
    assert check_password_hash(row["password_hash"], " pass word ")


def test_repeat_submission_creates_one_user(client):
    assert post(client).status_code == 302
    r = post(client)
    assert r.status_code == 200
    assert "Email already registered" in r.get_data(as_text=True)
    assert count_users() == 2


def test_html_in_name_is_escaped(client):
    r = post(client, name="<script>x</script>", confirm_password="different")
    body = r.get_data(as_text=True)
    assert "&lt;script&gt;" in body
    assert "<script>x" not in body


def test_unsupported_method_405(client):
    assert client.put("/register").status_code == 405

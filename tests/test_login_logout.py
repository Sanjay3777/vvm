from database import db


def login(client, email="demo@spendly.com", password="demo123", **extra):
    data = {"email": email, "password": password}
    data.update(extra)
    return client.post("/login", data=data)


# ---------------- Task 1 ----------------

def test_get_user_by_email_found(db_path):
    db.init_db()
    db.create_user("A", "a@x.com", "pw")
    row = db.get_user_by_email("a@x.com")
    assert row["name"] == "A" and row["email"] == "a@x.com"
    assert row["id"] and row["password_hash"]


def test_get_user_by_email_missing_returns_none(db_path):
    db.init_db()
    assert db.get_user_by_email("nobody@x.com") is None


# ---------------- Task 2 ----------------

def test_get_login_renders_form(client):
    r = client.get("/login")
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert 'name="email"' in body and 'name="password"' in body
    assert 'action="/login"' in body
    assert 'href="/register"' in body


def test_valid_login_sets_session_and_redirects(client):
    r = login(client)
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/")
    with client.session_transaction() as s:
        assert s["user_id"] == 1 and isinstance(s["user_id"], int)


def test_login_normalises_email(client):
    r = login(client, email="Demo@Spendly.com ")
    assert r.status_code == 302
    with client.session_transaction() as s:
        assert s["user_id"] == 1


def test_wrong_password(client):
    r = login(client, password="wrong")
    assert r.status_code == 200
    assert "Invalid email or password." in r.get_data(as_text=True)
    with client.session_transaction() as s:
        assert "user_id" not in s


def test_unknown_email(client):
    r = login(client, email="nobody@x.com")
    assert r.status_code == 200
    assert "Invalid email or password." in r.get_data(as_text=True)
    with client.session_transaction() as s:
        assert "user_id" not in s


def test_missing_fields_give_generic_error(client):
    for data in ({}, {"email": "demo@spendly.com"}):
        r = client.post("/login", data=data)
        assert r.status_code == 200
        assert "Invalid email or password." in r.get_data(as_text=True)


def test_password_not_stripped(client):
    assert login(client, password=" demo123").status_code == 200


def test_next_parameter_ignored(client):
    r = client.post(
        "/login?next=https://evil.example",
        data={"email": "demo@spendly.com", "password": "demo123", "next": "https://evil.example"},
    )
    assert r.status_code == 302
    assert "evil" not in r.headers["Location"]
    assert r.headers["Location"].endswith("/")


def test_login_clears_previous_session(client):
    with client.session_transaction() as s:
        s["foo"] = "bar"
        s["user_id"] = 999
    login(client)
    with client.session_transaction() as s:
        assert s["user_id"] == 1
        assert "foo" not in s


def test_failed_login_keeps_email_only(client):
    body = login(client, password="wrongpass").get_data(as_text=True)
    assert 'value="demo@spendly.com"' in body
    assert "wrongpass" not in body


def test_html_in_email_is_escaped(client):
    body = login(client, email="<b>x</b>").get_data(as_text=True)
    assert "&lt;b&gt;" in body
    assert "<b>x" not in body


def test_logout_clears_session(client):
    login(client)
    r = client.get("/logout")
    assert r.status_code == 302 and r.headers["Location"].endswith("/")
    with client.session_transaction() as s:
        assert "user_id" not in s
    assert "coming in Step 3" not in r.get_data(as_text=True)


def test_logout_without_session_redirects(client):
    r = client.get("/logout")
    assert r.status_code == 302 and r.headers["Location"].endswith("/")


def test_secret_key_comes_from_environment(monkeypatch):
    import importlib
    import app as app_module

    monkeypatch.setenv("SECRET_KEY", "from-env-value")
    importlib.reload(app_module)
    assert app_module.app.secret_key == "from-env-value"
    monkeypatch.delenv("SECRET_KEY")
    with __import__("pytest").warns(UserWarning):
        importlib.reload(app_module)
    assert app_module.app.secret_key != "spendly-dev-secret-change-me"
    assert len(app_module.app.secret_key) == 32

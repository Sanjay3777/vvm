import pytest

from database import db, queries


def row(expense_id):
    conn = db.get_db()
    r = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    return r


def count():
    conn = db.get_db()
    n = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    conn.close()
    return n


def setup_other(db_path):
    """Seeded DB plus a second user owning one expense. Returns (other_uid, other_expense_id)."""
    db.init_db()
    db.seed_db()
    uid = db.create_user("Other", "other@example.com", "secret123")
    eid = queries.insert_expense(uid, 5.0, "Other", "2026-03-03", "theirs")
    return uid, eid


def login_session(client, uid=1):
    with client.session_transaction() as s:
        s["user_id"] = uid


def make_other(client):
    uid = db.create_user("Other", "other@example.com", "secret123")
    eid = queries.insert_expense(uid, 5.0, "Other", "2026-03-03", "theirs")
    return uid, eid


def post(client, eid, **overrides):
    data = dict(amount="99.0", category="Bills", date="2026-02-02", description="Updated")
    data.update(overrides)
    data = {k: v for k, v in data.items() if v is not None}
    return client.post(f"/expenses/{eid}/edit", data=data)


# ---------------- Task 1 ----------------

def test_get_expense_by_id_owner(db_path):
    setup_other(db_path)
    e = queries.get_expense_by_id(1, 1)
    assert (e["category"], e["amount"], e["date"], e["description"]) == (
        "Food", 45.5, "2026-11-01", "Groceries")


def test_get_expense_by_id_wrong_user(db_path):
    uid, eid = setup_other(db_path)
    assert queries.get_expense_by_id(eid, 1) is None


def test_get_expense_by_id_missing(db_path):
    setup_other(db_path)
    assert queries.get_expense_by_id(999, 1) is None


def test_update_expense_updates_row(db_path):
    setup_other(db_path)
    before = row(1)
    n = count()
    assert queries.update_expense(1, 1, 99.0, "Bills", "2026-02-02", None) == 1
    after = row(1)
    assert (after["amount"], after["category"], after["date"], after["description"]) == (
        99.0, "Bills", "2026-02-02", None)
    assert after["user_id"] == before["user_id"] and after["created_at"] == before["created_at"]
    assert count() == n


def test_update_expense_wrong_user(db_path):
    uid, eid = setup_other(db_path)
    before = dict(row(eid))
    assert queries.update_expense(eid, 1, 99.0, "Bills", "2026-02-02", "x") == 0
    assert dict(row(eid)) == before


def test_update_expense_missing(db_path):
    setup_other(db_path)
    assert queries.update_expense(999, 1, 1.0, "Food", "2026-02-02", None) == 0


def test_recent_transactions_include_id(db_path):
    setup_other(db_path)
    for r in queries.get_recent_transactions(1):
        assert {"id", "date", "description", "category", "amount"} <= set(r)
    assert queries.get_recent_transactions(1)[0]["id"] == 8


# ---------------- Task 2 ----------------

def test_get_unauthenticated_redirects(client):
    r = client.get("/expenses/1/edit")
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")


def test_post_unauthenticated_redirects(client):
    before = dict(row(1))
    for eid in (1, 999):
        r = post(client, eid)
        assert r.status_code == 302 and r.headers["Location"].endswith("/login")
    assert dict(row(1)) == before


def test_get_own_expense_prefilled(client):
    login_session(client)
    r = client.get("/expenses/1/edit")
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    for text in ('value="45.50"', 'value="2026-11-01"', 'value="Groceries"',
                 '<option value="Food" selected', 'action="/expenses/1/edit"',
                 "Save Changes", 'href="/profile"'):
        assert text in body


def test_get_other_users_expense_404(client):
    _, eid = make_other(client)
    login_session(client)
    assert client.get(f"/expenses/{eid}/edit").status_code == 404


def test_get_missing_expense_404(client):
    login_session(client)
    assert client.get("/expenses/999/edit").status_code == 404


def test_post_other_users_expense_404_and_unchanged(client):
    _, eid = make_other(client)
    login_session(client)
    before = dict(row(eid))
    assert post(client, eid).status_code == 404
    assert dict(row(eid)) == before


def test_post_missing_expense_404(client):
    login_session(client)
    assert post(client, 999).status_code == 404


def test_post_other_user_invalid_data_still_404(client):
    _, eid = make_other(client)
    login_session(client)
    assert post(client, eid, amount="abc").status_code == 404


def test_valid_post_updates_and_redirects(client):
    login_session(client)
    r = post(client, 1)
    assert r.status_code == 302 and r.headers["Location"].endswith("/profile")
    e = row(1)
    assert (e["amount"], e["category"], e["date"], e["description"]) == (
        99.0, "Bills", "2026-02-02", "Updated")
    body = client.get("/profile").get_data(as_text=True)
    assert "Updated" in body and "₹99.00" in body


def test_no_description_stores_null(client):
    login_session(client)
    assert post(client, 1, description=None).status_code == 302
    assert row(1)["description"] is None


def test_whitespace_description_stores_null(client):
    login_session(client)
    assert post(client, 1, description="   ").status_code == 302
    assert row(1)["description"] is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": None}, {"amount": ""}, {"amount": "0"}, {"amount": "-5"},
        {"amount": "abc"}, {"amount": "inf"}, {"amount": "nan"}, {"amount": "1e999"},
        {"amount": "10000000"}, {"category": "Travel"}, {"category": "food"},
        {"category": None}, {"date": "2026-13-45"}, {"date": "not-a-date"},
        {"date": ""}, {"description": "x" * 201},
    ],
)
def test_error_cases(client, overrides):
    login_session(client)
    before = dict(row(1))
    r = post(client, 1, **overrides)
    assert r.status_code == 200
    assert 'class="auth-error"' in r.get_data(as_text=True)
    assert dict(row(1)) == before


def test_failure_repopulates_submitted_values(client):
    login_session(client)
    body = post(client, 1, amount="abc", category="Health", date="2026-04-01",
                description="Doctor").get_data(as_text=True)
    assert 'value="abc"' in body and 'value="2026-04-01"' in body and 'value="Doctor"' in body
    assert '<option value="Health" selected' in body
    assert 'value="Groceries"' not in body and 'value="2026-11-01"' not in body


def test_date_zero_padded_and_amount_rounded(client):
    login_session(client)
    post(client, 1, date="2026-3-5", amount="12.345")
    e = row(1)
    assert e["date"] == "2026-03-05" and e["amount"] == 12.35


def test_update_returning_zero_gives_404(client, monkeypatch):
    import app as app_module

    login_session(client)
    monkeypatch.setattr(app_module, "update_expense", lambda *a, **k: 0)
    assert post(client, 1).status_code == 404


def test_null_description_shows_empty_field(client):
    queries.update_expense(1, 1, 45.5, "Food", "2026-11-01", None)
    login_session(client)
    body = client.get("/expenses/1/edit").get_data(as_text=True)
    assert 'id="description"' in body and 'value=""' in body and "None" not in body


def test_huge_id_does_not_500(client):
    login_session(client)
    assert client.get("/expenses/99999999999999999999/edit").status_code == 404


def test_html_escaped_on_edit_form(client):
    login_session(client)
    body = post(client, 1, amount="abc", description="<script>x</script>").get_data(as_text=True)
    assert "&lt;script&gt;" in body and "<script>x" not in body


def test_unsupported_method_405(client):
    login_session(client)
    assert client.delete("/expenses/1/edit").status_code == 405


def test_profile_has_edit_links_and_actions_header(client):
    login_session(client)
    body = client.get("/profile").get_data(as_text=True)
    assert "Actions" in body
    for eid in range(1, 9):
        assert f'href="/expenses/{eid}/edit"' in body
    assert body.count(">Edit<") == 8


def test_add_expense_still_validates(client):
    login_session(client)
    r = client.post("/expenses/add", data=dict(amount="inf", category="Food", date="2026-03-20"))
    assert r.status_code == 200 and 'class="auth-error"' in r.get_data(as_text=True)

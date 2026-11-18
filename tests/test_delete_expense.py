import os
import re

from database import db, queries

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def exists(expense_id):
    conn = db.get_db()
    n = conn.execute("SELECT COUNT(*) FROM expenses WHERE id = ?", (expense_id,)).fetchone()[0]
    conn.close()
    return n == 1


def total():
    conn = db.get_db()
    n = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    conn.close()
    return n


def make_other():
    uid = db.create_user("Other", "other@example.com", "secret123")
    eid = queries.insert_expense(uid, 45.5, "Food", "2026-11-01", "Groceries")
    return uid, eid


def login_session(client, uid=1):
    with client.session_transaction() as s:
        s["user_id"] = uid


def tbody_rows(body):
    return body.split("<tbody>")[1].split("</tbody>")[0].count("<tr")


# ---------------- Task 1 ----------------

def test_delete_own_row_removed_returns_1(db_path):
    db.init_db()
    db.seed_db()
    assert queries.delete_expense(1, 1) == 1
    assert not exists(1)


def test_delete_leaves_other_rows(db_path):
    db.init_db()
    db.seed_db()
    _, eid = make_other()
    queries.delete_expense(1, 1)
    assert all(exists(i) for i in range(2, 9)) and exists(eid)
    assert total() == 8


def test_delete_wrong_user_returns_0(db_path):
    db.init_db()
    db.seed_db()
    _, eid = make_other()
    assert queries.delete_expense(eid, 1) == 0
    assert exists(eid)


def test_delete_missing_returns_0(db_path):
    db.init_db()
    db.seed_db()
    before = total()
    assert queries.delete_expense(999, 1) == 0
    assert total() == before


# ---------------- Task 2 ----------------

def test_post_unauthenticated_redirects(client):
    for eid in (1, 999):
        r = client.post(f"/expenses/{eid}/delete")
        assert r.status_code == 302 and r.headers["Location"].endswith("/login")
    assert exists(1)


def test_post_own_expense_deletes_and_redirects(client):
    login_session(client)
    r = client.post("/expenses/1/delete")
    assert r.status_code == 302 and r.headers["Location"].endswith("/profile")
    assert not exists(1)


def test_flash_shown_after_redirect(client):
    login_session(client)
    r = client.post("/expenses/1/delete", follow_redirects=True)
    body = r.get_data(as_text=True)
    assert "Expense deleted." in body and tbody_rows(body) == 7


def test_post_other_users_expense_404_row_remains(client):
    _, eid = make_other()
    login_session(client)
    assert client.post(f"/expenses/{eid}/delete").status_code == 404
    assert exists(eid)


def test_post_missing_expense_404(client):
    login_session(client)
    assert client.post("/expenses/999/delete").status_code == 404


def test_huge_id_404(client):
    login_session(client)
    assert client.post("/expenses/99999999999999999999/delete").status_code == 404


def test_get_returns_405(client):
    assert client.get("/expenses/1/delete").status_code == 405
    login_session(client)
    assert client.get("/expenses/1/delete").status_code == 405
    assert exists(1)


def test_other_methods_405(client):
    login_session(client)
    for method in (client.put, client.patch, client.delete):
        assert method("/expenses/1/delete").status_code == 405
    assert exists(1)


def test_double_delete_second_404_no_second_flash(client):
    login_session(client)
    assert client.post("/expenses/1/delete").status_code == 302
    assert client.post("/expenses/1/delete").status_code == 404
    body = client.get("/profile").get_data(as_text=True)
    assert body.count("Expense deleted.") == 1


def test_zero_rows_deleted_returns_404(client, monkeypatch):
    import app as app_module

    login_session(client)
    monkeypatch.setattr(app_module, "delete_expense_record", lambda *a, **k: 0)
    assert client.post("/expenses/1/delete").status_code == 404
    assert "Expense deleted." not in client.get("/profile").get_data(as_text=True)


def test_profile_has_delete_form_per_row(client):
    login_session(client)
    body = client.get("/profile").get_data(as_text=True)
    forms = re.findall(r"<form[^>]*delete[^>]*>.*?</form>", body, re.S)
    assert len(forms) == 8
    ids = set()
    for f in forms:
        m = re.search(r'action="/expenses/(\d+)/delete"', f)
        assert m
        ids.add(int(m.group(1)))
        assert 'method="POST"' in f and "inline-form" in f and "confirm(" in f
        assert re.search(r'<button[^>]*class="btn-delete"[^>]*>\s*Delete\s*</button>', f)
    assert ids == set(range(1, 9))
    assert body.count(">Edit<") == 8


def test_profile_no_style_attributes(client):
    login_session(client)
    assert "style=" not in client.get("/profile").get_data(as_text=True)


def test_css_defines_btn_delete_and_inline_form_with_variable():
    with open(os.path.join(ROOT, "static", "css", "style.css"), encoding="utf-8") as f:
        css = f.read()
    assert ".inline-form" in css
    block = re.search(r"\.btn-delete\s*\{[^}]*\}", css)
    assert block and "var(--danger" in block.group(0)
    assert re.search(r"--danger\s*:", css)


def test_delete_keeps_other_users_rows(client):
    uid, eid = make_other()
    login_session(client)
    client.post("/expenses/1/delete")
    assert exists(eid)
    assert all(exists(i) for i in range(2, 9))

import re

from database import db, queries


def setup(db_path):
    db.init_db()
    db.seed_db()


def add_expense(user_id, category, amount, date, description=None):
    conn = db.get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    conn.commit()
    conn.close()


def new_user(name="Asha Rao", email="asha@example.com"):
    return db.create_user(name, email, "secret123")


def login_session(client, user_id):
    with client.session_transaction() as s:
        s["user_id"] = user_id


# ---------------- Task 1: helpers ----------------

def test_get_user_by_id_valid(db_path):
    setup(db_path)
    u = queries.get_user_by_id(1)
    assert u["name"] == "Demo User" and u["email"] == "demo@spendly.com"
    assert re.fullmatch(r"[A-Z][a-z]+ \d{4}", u["member_since"])


def test_get_user_by_id_missing(db_path):
    setup(db_path)
    assert queries.get_user_by_id(999) is None


def test_member_since_format(db_path):
    setup(db_path)
    uid = new_user()
    conn = db.get_db()
    conn.execute("UPDATE users SET created_at = '2026-01-15 09:00:00' WHERE id = ?", (uid,))
    conn.commit()
    conn.close()
    assert queries.get_user_by_id(uid)["member_since"] == "January 2026"


def test_summary_stats_seed(db_path):
    setup(db_path)
    s = queries.get_summary_stats(1)
    assert s["total_spent"] == 346.24
    assert s["transaction_count"] == 8
    assert s["top_category"] == "Bills"


def test_summary_stats_empty(db_path):
    setup(db_path)
    uid = new_user()
    assert queries.get_summary_stats(uid) == {
        "total_spent": 0,
        "transaction_count": 0,
        "top_category": "—",
    }


def test_top_category_uses_sum_not_single_expense(db_path):
    setup(db_path)
    uid = new_user()
    add_expense(uid, "Food", 100, "2026-03-01")
    add_expense(uid, "Bills", 60, "2026-03-02")
    add_expense(uid, "Bills", 60, "2026-03-03")
    assert queries.get_summary_stats(uid)["top_category"] == "Bills"


def test_amounts_rounded_to_two_decimals(db_path):
    setup(db_path)
    uid = new_user()
    add_expense(uid, "Food", 0.1, "2026-03-01")
    add_expense(uid, "Food", 0.2, "2026-03-02")
    assert queries.get_summary_stats(uid)["total_spent"] == 0.3
    assert queries.get_category_breakdown(uid)[0]["amount"] == 0.3


def test_recent_transactions_order_and_keys(db_path):
    setup(db_path)
    rows = queries.get_recent_transactions(1)
    assert len(rows) == 8
    assert rows[0]["description"] == "Dinner out"
    assert [r["date"] for r in rows] == sorted((r["date"] for r in rows), reverse=True)
    assert set(rows[0]) == {"id", "date", "description", "category", "amount"}


def test_recent_transactions_same_date_newest_id_first(db_path):
    setup(db_path)
    uid = new_user()
    add_expense(uid, "Food", 1, "2026-03-01", "first")
    add_expense(uid, "Food", 2, "2026-03-01", "second")
    assert [r["description"] for r in queries.get_recent_transactions(uid)] == ["second", "first"]


def test_recent_transactions_limit(db_path):
    setup(db_path)
    uid = new_user()
    for i in range(12):
        add_expense(uid, "Food", 1, f"2026-03-{i + 1:02d}")
    assert len(queries.get_recent_transactions(uid)) == 10
    assert len(queries.get_recent_transactions(uid, limit=3)) == 3


def test_recent_transactions_empty(db_path):
    setup(db_path)
    assert queries.get_recent_transactions(new_user()) == []


def test_category_breakdown_seed(db_path):
    setup(db_path)
    rows = queries.get_category_breakdown(1)
    assert len(rows) == 7
    assert rows[0]["name"] == "Bills"
    amounts = [r["amount"] for r in rows]
    assert amounts == sorted(amounts, reverse=True)
    assert all(isinstance(r["pct"], int) for r in rows)
    assert sum(r["pct"] for r in rows) == 100


def test_category_breakdown_empty(db_path):
    setup(db_path)
    assert queries.get_category_breakdown(new_user()) == []


def test_category_breakdown_equal_thirds(db_path):
    setup(db_path)
    uid = new_user()
    for cat in ("Food", "Bills", "Health"):
        add_expense(uid, cat, 10, "2026-03-01")
    assert [r["pct"] for r in queries.get_category_breakdown(uid)] == [34, 33, 33]


def test_helpers_scope_to_user(db_path):
    setup(db_path)
    uid = new_user()
    add_expense(uid, "Other", 500, "2026-03-05", "theirs")
    assert queries.get_summary_stats(1)["total_spent"] == 346.24
    assert all(r["description"] != "theirs" for r in queries.get_recent_transactions(1))
    assert "Other" in [r["name"] for r in queries.get_category_breakdown(uid)]
    assert queries.get_summary_stats(uid)["transaction_count"] == 1
    assert next(r for r in queries.get_category_breakdown(1) if r["name"] == "Other")["amount"] == 10.0


# ---------------- Task 2: route ----------------

def test_profile_unauthenticated_redirects(client):
    r = client.get("/profile")
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")


def test_profile_seed_user_live_data(client):
    login_session(client, 1)
    r = client.get("/profile")
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    for text in ("Demo User", "demo@spendly.com", "₹346.24", "Bills"):
        assert text in body
    stats = body.split('class="stats-row"')[1].split("profile-panel")[0]
    assert re.search(r"Transactions</span>\s*<span class=\"stat-value\">8<", stats)
    tbody = body.split("<tbody>")[1].split("</tbody>")[0]
    assert tbody.count("<tr") == 8
    assert tbody.index("Dinner out") < tbody.index("Groceries")
    section = body.split('<ul class="breakdown">')[1]
    for cat in ("Bills", "Food", "Shopping", "Health", "Transport", "Entertainment", "Other"):
        assert cat in section
    values = [int(v) for v in re.findall(r'<progress[^>]*value="(\d+)"', body)]
    assert len(values) == 7 and sum(values) == 100


def test_profile_new_user_empty_state(client):
    uid = new_user()
    login_session(client, uid)
    r = client.get("/profile")
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "₹0.00" in body
    assert re.search(r"Transactions</span>\s*<span class=\"stat-value\">0<", body)
    assert "—" in body
    assert "<progress" not in body


def test_profile_unknown_session_user(client):
    login_session(client, 999)
    r = client.get("/profile")
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")
    with client.session_transaction() as s:
        assert "user_id" not in s


def test_profile_shows_only_own_data(client):
    uid = new_user()
    add_expense(uid, "Other", 500, "2026-03-05", "theirs")
    login_session(client, 1)
    body = client.get("/profile").get_data(as_text=True)
    assert "₹346.24" in body and "theirs" not in body


def test_profile_null_description_and_html_escaped(client):
    uid = new_user()
    add_expense(uid, "Food", 5, "2026-03-05", None)
    add_expense(uid, "Food", 6, "2026-03-06", "<b>x</b>")
    login_session(client, uid)
    body = client.get("/profile").get_data(as_text=True)
    assert "&lt;b&gt;" in body and "<b>x" not in body
    assert "None" not in body


def test_profile_initials(client):
    uid = new_user("Asha Rao", "ar@example.com")
    login_session(client, uid)
    assert 'class="profile-avatar">AR<' in client.get("/profile").get_data(as_text=True)
    uid2 = new_user("Asha", "a@example.com")
    login_session(client, uid2)
    assert 'class="profile-avatar">A<' in client.get("/profile").get_data(as_text=True)

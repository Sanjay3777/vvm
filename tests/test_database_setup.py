import datetime
import importlib
import re
import sqlite3

import pytest
from werkzeug.security import check_password_hash

from database import db


def add_user(conn, email="a@x.com"):
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("A", email, "h"),
    )
    conn.commit()
    return cur.lastrowid


def add_expense(conn, user_id, category="Food", date="2026-03-05", amount=1.0):
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
        (user_id, amount, category, date),
    )
    conn.commit()


# ---------------- Task 1: connection and schema ----------------

def test_get_db_row_factory_and_fk(db_path):
    db.init_db()
    conn = db.get_db()
    uid = add_user(conn)
    assert conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()["name"] == "A"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    conn.close()


def test_init_db_creates_tables_and_is_idempotent(db_path):
    db.init_db()
    db.init_db()
    conn = db.get_db()
    names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert {"users", "expenses"} <= names


def test_init_db_keeps_existing_data(db_path):
    db.init_db()
    conn = db.get_db()
    add_user(conn)
    conn.close()
    db.init_db()
    conn = db.get_db()
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    conn.close()


def test_duplicate_email_rejected(db_path):
    db.init_db()
    conn = db.get_db()
    add_user(conn)
    with pytest.raises(sqlite3.IntegrityError):
        add_user(conn)
    conn.close()


def test_expense_fk_rejected(db_path):
    db.init_db()
    conn = db.get_db()
    with pytest.raises(sqlite3.IntegrityError):
        add_expense(conn, 999)
    conn.close()


def test_user_with_expenses_cannot_be_deleted(db_path):
    db.init_db()
    conn = db.get_db()
    uid = add_user(conn)
    add_expense(conn, uid)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM users WHERE id = ?", (uid,))
    conn.close()


def test_invalid_category_rejected(db_path):
    db.init_db()
    conn = db.get_db()
    uid = add_user(conn)
    for cat in db.CATEGORIES:
        add_expense(conn, uid, category=cat)
    assert len(db.CATEGORIES) == 7
    with pytest.raises(sqlite3.IntegrityError):
        add_expense(conn, uid, category="Travel")
    conn.close()


@pytest.mark.parametrize("bad", ["2026-3-5", "2026-13-45", "05-03-2026", ""])
def test_invalid_date_rejected(db_path, bad):
    db.init_db()
    conn = db.get_db()
    uid = add_user(conn)
    with pytest.raises(sqlite3.IntegrityError):
        add_expense(conn, uid, date=bad)
    add_expense(conn, uid, date="2026-03-05")
    conn.close()


def test_created_at_default(db_path):
    db.init_db()
    conn = db.get_db()
    uid = add_user(conn)
    add_expense(conn, uid)
    assert conn.execute("SELECT created_at FROM users").fetchone()[0]
    assert conn.execute("SELECT created_at FROM expenses").fetchone()[0]
    conn.close()


def test_not_null_columns(db_path):
    db.init_db()
    conn = db.get_db()
    uid = add_user(conn)
    for sql, params in [
        ("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", (None, "n@x.com", "h")),
        ("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", ("n", None, "h")),
        ("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", ("n", "m@x.com", None)),
        ("INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)", (uid, None, "Food", "2026-03-05")),
        ("INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)", (uid, 1.0, None, "2026-03-05")),
        ("INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)", (uid, 1.0, "Food", None)),
    ]:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql, params)
    conn.close()


# ---------------- Task 2: seed data ----------------

def seeded(today=None):
    db.init_db()
    db.seed_db(today) if today else db.seed_db()
    return db.get_db()


def test_seed_creates_demo_user(db_path):
    conn = seeded()
    rows = conn.execute("SELECT * FROM users").fetchall()
    assert len(rows) == 1
    u = rows[0]
    assert (u["name"], u["email"]) == ("Demo User", "demo@spendly.com")
    assert u["password_hash"] != "demo123"
    assert check_password_hash(u["password_hash"], "demo123")
    conn.close()


def test_seed_expenses(db_path):
    conn = seeded()
    rows = conn.execute("SELECT * FROM expenses").fetchall()
    assert len(rows) == 8
    uid = conn.execute("SELECT id FROM users").fetchone()[0]
    assert all(r["user_id"] == uid for r in rows)
    assert {r["category"] for r in rows} == set(db.CATEGORIES)
    assert round(sum(r["amount"] for r in rows), 2) == 346.24
    totals = {}
    for r in rows:
        totals[r["category"]] = totals.get(r["category"], 0) + r["amount"]
    assert max(totals, key=totals.get) == "Bills"
    assert round(totals["Bills"], 2) == 120.00
    conn.close()


@pytest.mark.parametrize("day", [2, 9, 16, 28])
def test_seed_dates_not_in_future(db_path, day):
    today = datetime.date(2026, 3, day)
    conn = seeded(today)
    for r in conn.execute("SELECT date FROM expenses"):
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["date"])
        assert r["date"].startswith("2026-03-")
        assert r["date"] <= today.isoformat()
    conn.close()


def test_seed_uses_pinned_days_when_today_is_late(db_path):
    conn = seeded(datetime.date(2026, 3, 28))
    rows = conn.execute("SELECT date, amount, category FROM expenses ORDER BY date").fetchall()
    assert [r["date"][-2:] for r in rows] == ["01", "03", "05", "08", "10", "12", "14", "16"]
    assert [r["amount"] for r in rows] == [45.50, 28.00, 120.00, 35.99, 25.00, 49.00, 10.00, 32.75]
    conn.close()


def test_seed_idempotent(db_path):
    db.init_db()
    db.seed_db()
    db.seed_db()
    conn = db.get_db()
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 8
    conn.close()


def test_seed_skips_when_users_exist(db_path):
    db.init_db()
    conn = db.get_db()
    add_user(conn, "other@x.com")
    conn.close()
    db.seed_db()
    conn = db.get_db()
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 0
    conn.close()


# ---------------- Task 3: app startup ----------------

def test_app_startup_creates_database(db_path):
    import os
    import app as app_module

    importlib.reload(app_module)
    assert os.path.exists(db_path)
    conn = db.get_db()
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    conn.close()
    assert app_module.app.test_client().get("/").status_code == 200

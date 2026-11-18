import datetime
import os
import sqlite3

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "spendly.db"
)

CATEGORIES = (
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
)

_CATEGORY_LIST_SQL = ", ".join("'" + c + "'" for c in CATEGORIES)

SEED_EXPENSES = (
    ("Food", 45.50, 1, "Groceries"),
    ("Transport", 28.00, 3, "Metro card top-up"),
    ("Bills", 120.00, 5, "Electricity bill"),
    ("Health", 35.99, 8, "Pharmacy"),
    ("Entertainment", 25.00, 10, "Movie tickets"),
    ("Shopping", 49.00, 12, "Clothing"),
    ("Other", 10.00, 14, "Miscellaneous"),
    ("Food", 32.75, 16, "Dinner out"),
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                amount REAL NOT NULL,
                category TEXT NOT NULL CHECK (category IN ({_CATEGORY_LIST_SQL})),
                date TEXT NOT NULL CHECK (
                    date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                    AND date(date) IS NOT NULL
                    AND date(date) = date
                ),
                description TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_db(today=None):
    today = today or datetime.date.today()
    conn = get_db()
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cur.lastrowid
        rows = [
            (
                user_id,
                amount,
                category,
                datetime.date(today.year, today.month, min(day, today.day)).isoformat(),
                description,
            )
            for category, amount, day, description in SEED_EXPENSES
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def create_user(name, email, password):
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()

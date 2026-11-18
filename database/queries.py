"""Query helpers (profile reads, expense insert). No Flask imports."""

from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    created = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": created.strftime("%B %Y"),
    }


def _range_clause(date_from, date_to):
    """SQL fragment and parameters for an inclusive date range; both bounds are needed."""
    if date_from and date_to:
        return " AND date BETWEEN ? AND ?", [date_from, date_to]
    return "", []


def get_category_totals(user_id, date_from=None, date_to=None):
    clause, extra = _range_clause(date_from, date_to)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ?" + clause + " GROUP BY category "
            "ORDER BY total DESC, category ASC",
            [user_id] + extra,
        ).fetchall()
    finally:
        conn.close()
    return [(r["category"], round(r["total"], 2)) for r in rows]


def get_summary_stats(user_id, date_from=None, date_to=None, totals=None):
    clause, extra = _range_clause(date_from, date_to)
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS n "
            "FROM expenses WHERE user_id = ?" + clause,
            [user_id] + extra,
        ).fetchone()
    finally:
        conn.close()
    if totals is None:
        totals = get_category_totals(user_id, date_from, date_to)
    return {
        "total_spent": round(row["total"], 2),
        "transaction_count": row["n"],
        "top_category": totals[0][0] if totals else "—",
    }


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    clause, extra = _range_clause(date_from, date_to)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, date, description, category, amount FROM expenses "
            "WHERE user_id = ?" + clause + " ORDER BY date DESC, id DESC LIMIT ?",
            [user_id] + extra + [limit],
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": r["id"],
            "date": r["date"],
            "description": r["description"],
            "category": r["category"],
            "amount": r["amount"],
        }
        for r in rows
    ]


def get_category_breakdown(user_id, date_from=None, date_to=None, totals=None):
    if totals is None:
        totals = get_category_totals(user_id, date_from, date_to)
    grand = sum(amount for _, amount in totals)
    if not totals or grand <= 0:
        return []
    items = [
        {"name": name, "amount": amount, "pct": round(amount / grand * 100)}
        for name, amount in totals
    ]
    items[0]["pct"] += 100 - sum(i["pct"] for i in items)
    return items


def insert_expense(user_id, amount, category, date, description):
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_expense_by_id(expense_id, user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, user_id, amount, category, date, description "
            "FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        ).fetchone()
    except OverflowError:
        return None
    finally:
        conn.close()
    return dict(row) if row else None


def update_expense(expense_id, user_id, amount, category, date, description):
    conn = get_db()
    try:
        cur = conn.execute(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? "
            "WHERE id = ? AND user_id = ?",
            (amount, category, date, description, expense_id, user_id),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def delete_expense(expense_id, user_id):
    conn = get_db()
    try:
        cur = conn.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()

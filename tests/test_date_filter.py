import re
from datetime import date

import pytest

from database import db, queries

DATA = [
    ("Food", 10.0, "2026-01-10"),
    ("Bills", 20.0, "2026-02-15"),
    ("Food", 30.0, "2026-03-20"),
    ("Health", 5.0, "2026-03-20"),
    ("Other", 40.0, "2026-04-01"),
]


def make_user(email="u@example.com", data=DATA):
    uid = db.create_user("Filter User", email, "secret123")
    for cat, amt, d in data:
        queries.insert_expense(uid, amt, cat, d, f"{cat} {d}")
    return uid


def setup_user(db_path):
    db.init_db()
    return make_user()


def login(client, uid):
    with client.session_transaction() as s:
        s["user_id"] = uid


def page(client, query=""):
    r = client.get("/profile" + query)
    assert r.status_code == 200
    return r.get_data(as_text=True)


def rows(body):
    return body.split("<tbody>")[1].split("</tbody>")[0].count("<tr")


def anchor(body, label):
    return re.search(r"<a [^>]*>\s*" + re.escape(label) + r"\s*</a>", body).group(0)


@pytest.fixture
def user_client(client):
    uid = make_user()
    login(client, uid)
    return client


# ---------------- Task 1 ----------------

def test_stats_inclusive_bounds(db_path):
    uid = setup_user(db_path)
    s = queries.get_summary_stats(uid, "2026-01-10", "2026-04-01")
    assert s["transaction_count"] == 5 and s["total_spent"] == 105.0


def test_stats_range_inside(db_path):
    uid = setup_user(db_path)
    s = queries.get_summary_stats(uid, "2026-02-01", "2026-03-31")
    assert (s["total_spent"], s["transaction_count"], s["top_category"]) == (55.0, 3, "Food")


def test_stats_empty_range(db_path):
    uid = setup_user(db_path)
    assert queries.get_summary_stats(uid, "2026-05-01", "2026-05-31") == {
        "total_spent": 0, "transaction_count": 0, "top_category": "—"}


def test_stats_no_dates_unfiltered(db_path):
    uid = setup_user(db_path)
    assert queries.get_summary_stats(uid)["transaction_count"] == 5
    assert queries.get_summary_stats(uid) == queries.get_summary_stats(uid, None, None)


def test_stats_single_date_ignored(db_path):
    uid = setup_user(db_path)
    assert queries.get_summary_stats(uid, date_from="2026-03-01")["transaction_count"] == 5
    assert queries.get_summary_stats(uid, date_to="2026-01-31")["transaction_count"] == 5


def test_transactions_range_newest_first_limit(db_path):
    uid = setup_user(db_path)
    got = queries.get_recent_transactions(uid, date_from="2026-02-01", date_to="2026-03-31")
    assert len(got) == 3
    assert [r["date"] for r in got] == sorted((r["date"] for r in got), reverse=True)
    assert len(queries.get_recent_transactions(uid, limit=2, date_from="2026-02-01",
                                               date_to="2026-03-31")) == 2


def test_breakdown_range(db_path):
    uid = setup_user(db_path)
    got = queries.get_category_breakdown(uid, "2026-02-01", "2026-03-31")
    assert {r["name"] for r in got} == {"Food", "Bills", "Health"}
    assert sum(r["pct"] for r in got) == 100
    assert queries.get_category_breakdown(uid, "2026-05-01", "2026-05-31") == []


def test_other_users_not_included_in_range(db_path):
    uid = setup_user(db_path)
    make_user("other@example.com", [("Food", 999.0, "2026-03-01")])
    assert queries.get_summary_stats(uid, "2026-02-01", "2026-03-31")["total_spent"] == 55.0


# ---------------- Task 2 ----------------

def test_months_back_clamps():
    import app as a
    assert a._months_back(date(2024, 5, 31), 3) == date(2024, 2, 29)
    assert a._months_back(date(2026, 8, 31), 6) == date(2026, 2, 28)
    assert a._months_back(date(2026, 3, 15), 3) == date(2025, 12, 15)


def test_preset_ranges():
    import app as a
    p = {r["label"]: r for r in a._preset_ranges(date(2026, 5, 31))}
    assert (p["This Month"]["date_from"], p["This Month"]["date_to"]) == ("2026-05-01", "2026-05-31")
    assert p["Last 3 Months"]["date_from"] == "2026-02-28"
    assert p["Last 6 Months"]["date_from"] == "2025-11-30"
    assert p["All Time"]["date_from"] is None and p["All Time"]["date_to"] is None


def test_no_params_all_shown(user_client):
    body = page(user_client)
    assert rows(body) == 5 and "₹105.00" in body
    tag = anchor(body, "All Time")
    assert 'href="/profile"' in tag and "filter-active" in tag


def test_valid_range_filters_all_sections(user_client):
    body = page(user_client, "?date_from=2026-02-01&date_to=2026-03-31")
    assert "₹55.00" in body and rows(body) == 3
    assert body.count("<progress") == 3
    section = body.split('<ul class="breakdown">')[1]
    assert "Other" not in section


def test_equal_dates_single_day(user_client):
    body = page(user_client, "?date_from=2026-03-20&date_to=2026-03-20")
    assert rows(body) == 2 and "must not be after" not in body


def test_reversed_range_flashes_and_unfiltered(user_client):
    body = page(user_client, "?date_from=2026-04-01&date_to=2026-01-01")
    assert "Start date must not be after end date." in body
    assert rows(body) == 5


def test_flash_shown_once(user_client):
    page(user_client, "?date_from=2026-04-01&date_to=2026-01-01")
    assert "must not be after" not in page(user_client)
    assert "must not be after" not in user_client.get("/expenses/add").get_data(as_text=True)


@pytest.mark.parametrize("query", [
    "?date_from=not-a-date",
    "?date_from=2026-02-30&date_to=2026-03-31",
    "?date_from=&date_to=",
    "?date_from=2026-02-01",
    "?date_to=2026-02-01",
])
def test_malformed_no_error_unfiltered(user_client, query):
    body = page(user_client, query)
    assert rows(body) == 5 and "must not be after" not in body


def test_hostile_values_safe(user_client):
    body = page(user_client, "?date_from=<script>x</script>&date_to=2026-01-01")
    assert "<script>x" not in body
    page(user_client, "?date_from=" + "9" * 10000 + "&date_to=2026-01-01")
    page(user_client, "?date_from[]=x")


def test_unpadded_date_normalised(user_client):
    body = page(user_client, "?date_from=2026-2-1&date_to=2026-3-31")
    assert rows(body) == 3
    assert 'value="2026-02-01"' in body and 'value="2026-03-31"' in body


def test_preset_links_present(user_client):
    body = page(user_client)
    for label in ("This Month", "Last 3 Months", "Last 6 Months", "All Time"):
        assert anchor(body, label)
    assert 'href="/profile"' in anchor(body, "All Time")
    for label in ("This Month", "Last 3 Months", "Last 6 Months"):
        tag = anchor(body, label)
        assert "date_from=" in tag and "date_to=" in tag


def test_active_state_for_preset(user_client):
    import app as a
    for p in a._preset_ranges(date.today()):
        if p["date_from"] is None:
            continue
        body = page(user_client, f"?date_from={p['date_from']}&date_to={p['date_to']}")
        for label in ("This Month", "Last 3 Months", "Last 6 Months", "All Time"):
            assert ("filter-active" in anchor(body, label)) == (label == p["label"]), (p["label"], label)


def test_custom_range_prefilled_no_preset_active(user_client):
    body = page(user_client, "?date_from=2026-02-01&date_to=2026-03-31")
    assert 'value="2026-02-01"' in body and 'value="2026-03-31"' in body
    for label in ("This Month", "Last 3 Months", "Last 6 Months", "All Time"):
        assert "filter-active" not in anchor(body, label)


def test_empty_range_shows_zeros(user_client):
    body = page(user_client, "?date_from=2026-05-01&date_to=2026-05-31")
    assert "₹0.00" in body and "<progress" not in body
    assert re.search(r"Transactions</span>\s*<span class=\"stat-value\">0<", body)


def test_currency_kept_when_filtered(user_client):
    body = page(user_client, "?date_from=2026-02-01&date_to=2026-03-31")
    assert "₹" in body and "£" not in body and "$" not in body


def test_no_inline_styles_with_filter_bar(user_client):
    assert "style=" not in page(user_client, "?date_from=2026-02-01&date_to=2026-03-31")

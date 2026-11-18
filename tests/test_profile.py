import os
import re

from database import db

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def login_session(client, user_id=1):
    with client.session_transaction() as s:
        s["user_id"] = user_id


def profile_body(client):
    login_session(client)
    r = client.get("/profile")
    assert r.status_code == 200
    return r.get_data(as_text=True)


# ---------------- Task 1: navbar ----------------

def test_navbar_guest_links(client):
    body = client.get("/").get_data(as_text=True)
    assert "Sign in" in body and "Get started" in body
    assert 'href="/logout"' not in body


def test_navbar_logged_in_on_landing(client):
    login_session(client)
    body = client.get("/").get_data(as_text=True)
    assert 'href="/logout"' in body
    assert 'href="/profile"' in body and "Profile" in body
    assert "Get started" not in body


# ---------------- Task 2: profile page ----------------

def test_profile_requires_login(client):
    r = client.get("/profile")
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")
    assert "Demo User" not in r.get_data(as_text=True)


def test_profile_logged_in_200(client):
    profile_body(client)


def test_profile_user_card(client):
    body = profile_body(client)
    for text in ("Demo User", "demo@spendly.com", "DU", "Member since"):
        assert text in body


def test_profile_stats(client):
    body = profile_body(client)
    assert "₹346.24" in body and "Bills" in body
    assert "Total spent" in body and "Transactions" in body and "Top category" in body


def test_profile_transactions(client):
    body = profile_body(client)
    tbody = body.split("<tbody>")[1].split("</tbody>")[0]
    assert tbody.count("<tr") == 8
    assert tbody.count('class="badge') == 8
    assert "Electricity bill" in body and "₹120.00" in body


def test_profile_category_breakdown(client):
    body = profile_body(client)
    section = body.split('<ul class="breakdown">')[1]
    for cat in ("Bills", "Food", "Shopping", "Health", "Transport", "Entertainment", "Other"):
        assert cat in section
    values = [int(v) for v in re.findall(r'<progress[^>]*value="(\d+)"', body)]
    assert len(values) == 7 and sum(values) == 100


def test_profile_currency(client):
    body = profile_body(client)
    assert "₹" in body and "£" not in body and "$" not in body


def test_profile_no_inline_styles_or_hex(client):
    body = profile_body(client)
    assert "style=" not in body
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", body)
    with open(os.path.join(ROOT, "static", "css", "profile.css"), encoding="utf-8") as f:
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", f.read())


def test_profile_css_linked(client):
    assert "css/profile.css" in profile_body(client)
    assert os.path.getsize(os.path.join(ROOT, "static", "css", "profile.css")) > 0


def test_profile_navbar_shows_name_and_logout(client):
    nav = profile_body(client).split("</nav>")[0]
    assert "Demo User" in nav and 'href="/logout"' in nav

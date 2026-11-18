import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db  # noqa: E402


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = str(tmp_path / "test_spendly.db")
    monkeypatch.setattr(db, "DB_PATH", path)
    return path


@pytest.fixture
def client(db_path):
    db.init_db()
    db.seed_db()
    import app as app_module

    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Each test gets its own database file so they don't step on each other.
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SEED_DEMO_DATA", "1")
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

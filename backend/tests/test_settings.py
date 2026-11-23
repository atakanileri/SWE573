"""Settings that differ between a laptop, Docker Compose, and Render.

The API tests cover the routes. These check the small bits of configuration
those routes depend on: which database URL we open, and which demo login
the seed creates.
"""

from fastapi.testclient import TestClient

from app.database import normalize_database_url


def test_sqlite_url_is_left_alone():
    assert normalize_database_url("sqlite:////data/crafts.db") == "sqlite:////data/crafts.db"


def test_render_postgres_url_names_the_driver():
    # Render's blueprint uses postgresql://. Older docs also show postgres://.
    assert (
        normalize_database_url("postgresql://user:pass@host/crafts")
        == "postgresql+psycopg://user:pass@host/crafts"
    )
    assert (
        normalize_database_url("postgres://user:pass@host:5432/crafts")
        == "postgresql+psycopg://user:pass@host:5432/crafts"
    )


def test_missing_database_url_means_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from app.database import database_url

    assert database_url().startswith("sqlite:///")


def test_demo_login_can_come_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'demo.db'}")
    monkeypatch.setenv("SEED_DEMO_DATA", "1")
    monkeypatch.setenv("DEMO_EMAIL", "grader@example.com")
    monkeypatch.setenv("DEMO_PASSWORD", "class-demo")

    from app.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"email": "grader@example.com", "password": "class-demo"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["user"]["email"] == "grader@example.com"

        # The default password must not keep working for the overridden account.
        rejected = client.post(
            "/api/auth/login",
            json={"email": "grader@example.com", "password": "password"},
        )
        assert rejected.status_code == 401

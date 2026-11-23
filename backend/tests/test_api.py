"""API tests for the prototype.

They use FastAPI's TestClient, which calls the app in-process. No server
has to be running. Each test gets a fresh SQLite file (see conftest.py)
that is seeded with the sample crafts.
"""

DEMO_EMAIL = "atakan@example.com"
DEMO_PASSWORD = "password"


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def login(client, email=DEMO_EMAIL, password=DEMO_PASSWORD):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["token"]


def register(client, email, name="Test User", password="secret123"):
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "display_name": name},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["token"], body["user"]


def craft_payload(**overrides):
    data = {
        "title": "Test kilim",
        "description": "A small test post.",
        "image_url": "",
        "category": "Textiles",
        "tags": ["wool"],
        "dimensions": "10 × 10 cm",
        "colors": "red",
        "tools": "loom",
        "backstory": "Made while checking the prototype.",
        "note": "A note.",
        "location_text": "Toros, Mersin",
        "latitude": 36.8,
        "longitude": 34.0,
        "status": "published",
    }
    data.update(overrides)
    return data


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_docs_list_the_routes(client):
    docs = client.get("/docs")
    assert docs.status_code == 200
    assert "swagger" in docs.text.lower()

    spec = client.get("/openapi.json")
    assert spec.status_code == 200
    paths = spec.json()["paths"]
    expected = [
        "/health",
        "/api/counter",
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/me",
        "/api/categories",
        "/api/tags",
        "/api/crafts",
        "/api/crafts/{craft_id}",
        "/api/crafts/{craft_id}/favorite",
        "/api/crafts/{craft_id}/reports",
        "/api/reports",
        "/api/proposals",
        "/api/proposals/{proposal_id}/approve",
        "/api/proposals/{proposal_id}/reject",
    ]
    for path in expected:
        assert path in paths, path
    assert "get" in paths["/api/counter"]
    assert "post" in paths["/api/counter"]


def test_homepage_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Indigenous Crafts" in response.text
    assert "API counter" in response.text


def test_counter_starts_at_zero_and_increments(client):
    first = client.get("/api/counter")
    assert first.status_code == 200
    assert first.json() == {"count": 0}

    bumped = client.post("/api/counter")
    assert bumped.status_code == 200
    assert bumped.json() == {"count": 1}

    again = client.post("/api/counter")
    assert again.json()["count"] == 2

    # GET reads the same row, it does not reset it.
    assert client.get("/api/counter").json()["count"] == 2


def test_crafts_require_login(client):
    assert client.get("/api/crafts").status_code == 401
    assert client.get("/api/crafts/1").status_code == 401
    assert client.post("/api/crafts", json=craft_payload()).status_code == 401


def test_login_and_seeded_feed(client):
    token = login(client)
    me = client.get("/api/auth/me", headers=auth(token))
    assert me.status_code == 200
    assert me.json()["email"] == DEMO_EMAIL
    assert me.json()["display_name"] == "Atakan İ."

    feed = client.get("/api/crafts", headers=auth(token))
    assert feed.status_code == 200
    crafts = feed.json()
    assert len(crafts) >= 16
    titles = [craft["title"] for craft in crafts]
    assert titles[0] == "Hand-woven Yörük kilim"
    # The feed is for logged-in people, but other people's emails stay hidden.
    assert "email" not in crafts[0]
    assert crafts[0]["author_name"] == "Atakan İ."
    assert crafts[0]["owner"] is True
    assert "location_text" in crafts[0]


def test_wrong_password(client):
    response = client.post(
        "/api/auth/login",
        json={"email": DEMO_EMAIL, "password": "not-the-password"},
    )
    assert response.status_code == 401


def test_register_and_reject_duplicate(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "secret123", "display_name": "New Person"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["email"] == "new@example.com"
    assert "stubbed" in body["note"]
    assert "password_hash" not in response.text

    duplicate = client.post(
        "/api/auth/register",
        json={"email": "New@Example.com", "password": "secret123", "display_name": "Again"},
    )
    assert duplicate.status_code == 409

    # Register already logged them in.
    assert client.get("/api/auth/me", headers=auth(body["token"])).status_code == 200


def test_create_craft_appears_in_the_feed(client):
    token = login(client)
    created = client.post("/api/crafts", json=craft_payload(title="Brand new basket"), headers=auth(token))
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["title"] == "Brand new basket"
    assert body["owner"] is True
    assert body["status"] == "published"
    assert body["author_name"] == "Atakan İ."

    feed = client.get("/api/crafts", headers=auth(token)).json()
    assert feed[0]["id"] == body["id"]

    one = client.get(f"/api/crafts/{body['id']}", headers=auth(token))
    assert one.status_code == 200
    assert one.json()["location_text"] == "Toros, Mersin"


def test_publish_requires_location_and_real_tags(client):
    token = login(client)
    missing = client.post(
        "/api/crafts",
        json=craft_payload(location_text="", latitude=None, longitude=None),
        headers=auth(token),
    )
    assert missing.status_code == 422
    assert any("location" in msg.lower() for msg in missing.json()["detail"])

    bad_tag = client.post(
        "/api/crafts",
        json=craft_payload(tags=["not-a-real-tag"]),
        headers=auth(token),
    )
    assert bad_tag.status_code == 422

    bad_url = client.post(
        "/api/crafts",
        json=craft_payload(image_url="javascript:alert(1)"),
        headers=auth(token),
    )
    assert bad_url.status_code == 422


def test_draft_is_private_until_the_author_publishes_it(client):
    author, _user = register(client, "author@example.com", name="Author")
    other, _other = register(client, "other@example.com", name="Other")

    created = client.post(
        "/api/crafts",
        json=craft_payload(title="Secret draft", status="draft", location_text=""),
        headers=auth(author),
    )
    assert created.status_code == 201, created.text
    draft_id = created.json()["id"]
    assert created.json()["status"] == "draft"

    # The other person cannot see it in the feed or by id.
    public_feed = client.get("/api/crafts", headers=auth(other)).json()
    assert all(craft["id"] != draft_id for craft in public_feed)
    assert client.get(f"/api/crafts/{draft_id}", headers=auth(other)).status_code == 404

    mine = client.get("/api/crafts?mine=true&status=draft", headers=auth(author)).json()
    assert [craft["id"] for craft in mine] == [draft_id]

    # Publishing is an update of the same row, not a second post.
    published = client.put(
        f"/api/crafts/{draft_id}",
        json=craft_payload(title="Secret draft", status="published"),
        headers=auth(author),
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    public_feed = client.get("/api/crafts", headers=auth(other)).json()
    assert any(craft["id"] == draft_id for craft in public_feed)


def test_only_the_author_can_edit_or_delete(client):
    author, _user = register(client, "owner@example.com", name="Owner")
    other, _other = register(client, "stranger@example.com", name="Stranger")
    created = client.post("/api/crafts", json=craft_payload(), headers=auth(author)).json()
    craft_id = created["id"]

    forbidden = client.put(
        f"/api/crafts/{craft_id}",
        json=craft_payload(title="Hijacked"),
        headers=auth(other),
    )
    assert forbidden.status_code == 403

    deleted = client.delete(f"/api/crafts/{craft_id}", headers=auth(other))
    assert deleted.status_code == 403

    assert client.delete(f"/api/crafts/{craft_id}", headers=auth(author)).status_code == 204
    assert client.get(f"/api/crafts/{craft_id}", headers=auth(author)).status_code == 404


def test_search_and_category_filter(client):
    token = login(client)
    wool = client.get("/api/crafts?q=wool", headers=auth(token))
    assert wool.status_code == 200
    assert len(wool.json()) >= 1
    assert any("kilim" in craft["title"].lower() or "wool" in craft["tags"] for craft in wool.json())

    pottery = client.get("/api/crafts?category=Pottery", headers=auth(token)).json()
    assert len(pottery) >= 1
    assert all(craft["category"] == "Pottery" for craft in pottery)

    silver = client.get("/api/crafts?tag=silver", headers=auth(token)).json()
    assert any(craft["title"] == "Tuareg silver cross" for craft in silver)

    unknown = client.get("/api/crafts?category=Nope", headers=auth(token))
    assert unknown.status_code == 400


def test_favorite_and_report(client):
    token = login(client)
    craft_id = client.get("/api/crafts", headers=auth(token)).json()[0]["id"]

    on = client.post(f"/api/crafts/{craft_id}/favorite", headers=auth(token))
    assert on.status_code == 200
    assert on.json() == {"favorited": True}

    listed = client.get("/api/crafts?favorites=true", headers=auth(token)).json()
    assert [craft["id"] for craft in listed] == [craft_id]
    assert listed[0]["favorited"] is True

    off = client.post(f"/api/crafts/{craft_id}/favorite", headers=auth(token))
    assert off.json() == {"favorited": False}

    report = client.post(
        f"/api/crafts/{craft_id}/reports",
        json={"reason": "Wrong or misleading information", "details": "The size looks wrong."},
        headers=auth(token),
    )
    assert report.status_code == 201, report.text
    mine = client.get("/api/reports", headers=auth(token)).json()
    assert len(mine) == 1
    assert mine[0]["details"] == "The size looks wrong."


def test_logout_makes_the_token_useless(client):
    token = login(client)
    assert client.post("/api/auth/logout", headers=auth(token)).status_code == 204
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 401


def test_status_filter_does_not_apply_to_the_public_feed(client):
    token = login(client)
    response = client.get("/api/crafts?status=draft", headers=auth(token))
    assert response.status_code == 400

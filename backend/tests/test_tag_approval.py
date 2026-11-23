"""Tag and category approval (issue #15).

Posters pick from the official list. A new name stays pending until an
admin approves it. The demo account is that admin. Anyone else gets 403
on approve and reject.
"""

from fastapi.testclient import TestClient

from tests.test_api import DEMO_EMAIL, auth, craft_payload, login, register

STARTER_CATEGORIES = [
    "Textiles",
    "Pottery",
    "Carving",
    "Jewelry",
    "Painting",
    "Embroidery",
]
STARTER_TAGS = ["wool", "natural-dye", "clay", "wood", "beads", "silver"]


def test_posters_pick_from_the_official_list(client):
    token = login(client)
    categories = client.get("/api/categories", headers=auth(token))
    tags = client.get("/api/tags", headers=auth(token))
    assert categories.status_code == 200
    assert categories.json() == STARTER_CATEGORIES
    assert tags.json() == STARTER_TAGS

    # A registered person, not the admin, can still publish with those names.
    user, _user = register(client, "picker@example.com", name="Picker")
    created = client.post("/api/crafts", json=craft_payload(), headers=auth(user))
    assert created.status_code == 201, created.text
    assert created.json()["category"] == "Textiles"
    assert created.json()["tags"] == ["wool"]


def test_the_demo_account_is_the_admin(client):
    admin = login(client)
    me = client.get("/api/auth/me", headers=auth(admin)).json()
    assert me["email"] == DEMO_EMAIL
    assert me["is_admin"] is True

    _token, user = register(client, "member@example.com", name="Member")
    assert user["is_admin"] is False


def test_a_proposal_stays_pending_until_an_admin_approves_it(client):
    user, _user = register(client, "proposer@example.com", name="Proposer")
    admin = login(client)

    tag = client.post(
        "/api/proposals",
        json={"kind": "tag", "name": "#Copper"},
        headers=auth(user),
    )
    assert tag.status_code == 201, tag.text
    assert tag.json()["name"] == "copper"
    assert tag.json()["status"] == "pending"
    assert tag.json()["proposed_by"] == "Proposer"
    assert tag.json()["mine"] is True

    category = client.post(
        "/api/proposals",
        json={"kind": "category", "name": "baskets"},
        headers=auth(user),
    )
    assert category.status_code == 201, category.text
    assert category.json()["name"] == "Baskets"
    assert category.json()["status"] == "pending"

    # Pending names are not on the picker, and a post cannot use them.
    tags = client.get("/api/tags", headers=auth(user)).json()
    assert "copper" not in tags
    blocked = client.post(
        "/api/crafts",
        json=craft_payload(tags=["copper"]),
        headers=auth(user),
    )
    assert blocked.status_code == 422
    assert client.get("/api/crafts?tag=copper", headers=auth(user)).status_code == 400

    # The proposer cannot approve their own name.
    assert client.post(
        f"/api/proposals/{tag.json()['id']}/approve",
        headers=auth(user),
    ).status_code == 403
    assert client.post(
        f"/api/proposals/{category.json()['id']}/reject",
        headers=auth(user),
    ).status_code == 403

    approved_tag = client.post(
        f"/api/proposals/{tag.json()['id']}/approve",
        headers=auth(admin),
    )
    approved_category = client.post(
        f"/api/proposals/{category.json()['id']}/approve",
        headers=auth(admin),
    )
    assert approved_tag.status_code == 200, approved_tag.text
    assert approved_tag.json()["status"] == "official"
    assert approved_category.json()["status"] == "official"

    assert client.get("/api/tags", headers=auth(user)).json()[-1] == "copper"
    assert client.get("/api/categories", headers=auth(user)).json()[-1] == "Baskets"

    published = client.post(
        "/api/crafts",
        json=craft_payload(title="Copper basket", category="Baskets", tags=["copper"]),
        headers=auth(user),
    )
    assert published.status_code == 201, published.text
    craft_id = published.json()["id"]
    by_tag = client.get("/api/crafts?tag=copper", headers=auth(admin)).json()
    by_category = client.get("/api/crafts?category=Baskets", headers=auth(admin)).json()
    assert [craft["id"] for craft in by_tag] == [craft_id]
    assert [craft["id"] for craft in by_category] == [craft_id]


def test_a_non_admin_cannot_approve_or_reject(client):
    user, _user = register(client, "nobody@example.com", name="Nobody")
    other, _other = register(client, "else@example.com", name="Else")
    created = client.post(
        "/api/proposals",
        json={"kind": "tag", "name": "linen"},
        headers=auth(user),
    )
    proposal_id = created.json()["id"]

    assert client.post(f"/api/proposals/{proposal_id}/approve", headers=auth(other)).status_code == 403
    assert client.post(f"/api/proposals/{proposal_id}/reject", headers=auth(other)).status_code == 403
    # No token at all.
    assert client.post("/api/proposals", json={"kind": "tag", "name": "silk"}).status_code == 401
    assert client.get("/api/proposals").status_code == 401
    assert client.post(f"/api/proposals/{proposal_id}/approve").status_code == 401

    still = client.get("/api/proposals", headers=auth(user)).json()
    assert still[0]["status"] == "pending"
    assert "linen" not in client.get("/api/tags", headers=auth(user)).json()


def test_admin_can_reject_and_the_person_can_propose_again(client):
    user, _user = register(client, "again@example.com", name="Again")
    admin = login(client)
    created = client.post(
        "/api/proposals",
        json={"kind": "tag", "name": "glass"},
        headers=auth(user),
    )
    proposal_id = created.json()["id"]

    rejected = client.post(f"/api/proposals/{proposal_id}/reject", headers=auth(admin))
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    assert "glass" not in client.get("/api/tags", headers=auth(user)).json()
    assert client.post(
        "/api/crafts",
        json=craft_payload(tags=["glass"]),
        headers=auth(user),
    ).status_code == 422

    # Asking again reopens the same row. It is pending, not official.
    reopened = client.post(
        "/api/proposals",
        json={"kind": "tag", "name": "glass"},
        headers=auth(user),
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["id"] == proposal_id
    assert reopened.json()["status"] == "pending"


def test_admin_adds_a_name_straight_onto_the_list(client):
    admin = login(client)
    created = client.post(
        "/api/proposals",
        json={"kind": "category", "name": "beadwork"},
        headers=auth(admin),
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "official"
    assert client.get("/api/categories", headers=auth(admin)).json()[-1] == "Beadwork"

    published = client.post(
        "/api/crafts",
        json=craft_payload(category="Beadwork"),
        headers=auth(admin),
    )
    assert published.status_code == 201, published.text

    # The same call approves a name that is still pending.
    user, _user = register(client, "waiter@example.com", name="Waiter")
    pending = client.post(
        "/api/proposals",
        json={"kind": "tag", "name": "sinew"},
        headers=auth(user),
    )
    decided = client.post(
        "/api/proposals",
        json={"kind": "tag", "name": "sinew"},
        headers=auth(admin),
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["id"] == pending.json()["id"]
    assert decided.json()["status"] == "official"
    assert "sinew" in client.get("/api/tags", headers=auth(user)).json()


def test_duplicate_and_bad_names_are_refused(client):
    user, _user = register(client, "dup@example.com", name="Dup")
    headers = auth(user)

    assert client.post(
        "/api/proposals", json={"kind": "tag", "name": "Natural Dye"}, headers=headers
    ).status_code == 409
    assert client.post(
        "/api/proposals", json={"kind": "category", "name": "pottery"}, headers=headers
    ).status_code == 409

    first = client.post(
        "/api/proposals", json={"kind": "tag", "name": "quill"}, headers=headers
    )
    assert first.status_code == 201
    again = client.post(
        "/api/proposals", json={"kind": "tag", "name": "quill"}, headers=headers
    )
    assert again.status_code == 409

    bad = client.post(
        "/api/proposals", json={"kind": "tag", "name": "!!"}, headers=headers
    )
    assert bad.status_code == 422
    short = client.post(
        "/api/proposals", json={"kind": "tag", "name": "a"}, headers=headers
    )
    assert short.status_code == 422


def test_proposals_are_private_unless_you_are_the_admin(client):
    owner, _owner = register(client, "owner-prop@example.com", name="Owner")
    other, _other = register(client, "other-prop@example.com", name="Other")
    created = client.post(
        "/api/proposals",
        json={"kind": "category", "name": "Masks"},
        headers=auth(owner),
    )
    assert created.status_code == 201

    theirs = client.get("/api/proposals", headers=auth(other)).json()
    assert theirs == []

    mine = client.get("/api/proposals", headers=auth(owner)).json()
    assert [row["name"] for row in mine] == ["Masks"]
    assert mine[0]["mine"] is True

    admin = login(client)
    queue = client.get("/api/proposals?status=pending", headers=auth(admin)).json()
    assert any(row["name"] == "Masks" and row["proposed_by"] == "Owner" for row in queue)
    assert client.get("/api/proposals?status=nope", headers=auth(admin)).status_code == 400

    # An official starter name cannot be rejected. Posts already use it.
    official = client.get("/api/proposals?status=official", headers=auth(admin)).json()
    wool = next(row for row in official if row["name"] == "wool" and row["kind"] == "tag")
    refused = client.post(f"/api/proposals/{wool['id']}/reject", headers=auth(admin))
    assert refused.status_code == 400
    assert "wool" in client.get("/api/tags", headers=auth(admin)).json()
    missing = client.post("/api/proposals/99999/approve", headers=auth(admin))
    assert missing.status_code == 404


def test_startup_restores_the_lists_and_the_admin_when_users_already_exist(tmp_path, monkeypatch):
    """The deployed database already has users.

    create_all creates a missing table and does not add a column to users.
    Booting, deleting the new tables' rows, and booting again is that case:
    the sample user is still there, and startup has to put the official
    names and the admin row back without inserting the crafts a second time.
    """
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'kept.db'}")
    monkeypatch.setenv("SEED_DEMO_DATA", "1")
    import app.database as database
    from app.main import app
    from app.models import Admin, Craft, Vocabulary

    with TestClient(app):
        pass

    db = database.SessionLocal()
    craft_count = db.query(Craft).count()
    assert craft_count >= 16
    db.query(Admin).delete()
    db.query(Vocabulary).delete()
    db.commit()
    db.close()

    with TestClient(app) as client:
        token = login(client)
        me = client.get("/api/auth/me", headers=auth(token)).json()
        assert me["is_admin"] is True
        assert client.get("/api/categories", headers=auth(token)).json() == STARTER_CATEGORIES
        assert client.get("/api/tags", headers=auth(token)).json() == STARTER_TAGS

    db = database.SessionLocal()
    try:
        assert db.query(Craft).count() == craft_count
    finally:
        db.close()

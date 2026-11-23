"""Draft rules (issue #14).

A draft is a craft with status "draft". These tests hit the real routes.
The small unit checks call check_rules directly, which is the same function
the routes use before they write a row.
"""

import pytest
from fastapi import HTTPException

from app.routers.crafts import check_rules
from app.schemas import CraftIn

# Same helpers as the other API tests. Importing that file does not run them.
from tests.test_api import auth, craft_payload, register


def draft_payload(**overrides):
    """A title and nothing else. Publishing this must be rejected."""
    data = craft_payload(
        title="Half-finished bowl",
        status="draft",
        description="",
        image_url="",
        category="",
        tags=[],
        dimensions="",
        colors="",
        tools="",
        backstory="",
        note="",
        location_text="",
        latitude=None,
        longitude=None,
    )
    data.update(overrides)
    return data


def ids(response):
    return [craft["id"] for craft in response.json()]


def test_a_draft_only_needs_a_title():
    # No database. This is the rule the form is copying.
    check_rules(CraftIn(title="Half-finished bowl", status="draft"))


def test_publishing_checks_the_required_fields():
    with pytest.raises(HTTPException) as caught:
        check_rules(CraftIn(title="Half-finished bowl", status="published"))
    assert caught.value.status_code == 422
    text = " ".join(caught.value.detail).lower()
    for word in ("description", "category", "tag", "dimensions", "colors", "tools", "backstory", "location"):
        assert word in text


def test_save_an_incomplete_draft_and_keep_it_private(client):
    author, _user = register(client, "drafter@example.com", name="Drafter")
    other, _other = register(client, "reader@example.com", name="Reader")

    created = client.post("/api/crafts", json=draft_payload(), headers=auth(author))
    assert created.status_code == 201, created.text
    draft = created.json()
    draft_id = draft["id"]
    assert draft["status"] == "draft"
    assert draft["title"] == "Half-finished bowl"
    assert draft["location_text"] == ""
    assert draft["owner"] is True
    # The author's email stays off the craft, same as a published post.
    assert "email" not in draft

    # A made-up tag is still rejected. A draft is not a way around the list.
    bad_tag = client.post(
        "/api/crafts",
        json=draft_payload(title="Bad tag", tags=["not-a-real-tag"]),
        headers=auth(author),
    )
    assert bad_tag.status_code == 422

    blank = client.post(
        "/api/crafts",
        json={"title": "   ", "status": "draft"},
        headers=auth(author),
    )
    assert blank.status_code == 422

    # The author can open it and list it. The public feed does not have it.
    assert client.get(f"/api/crafts/{draft_id}", headers=auth(author)).status_code == 200
    mine = client.get("/api/crafts?mine=true&status=draft", headers=auth(author))
    assert draft_id in ids(mine)
    published_only = client.get("/api/crafts?mine=true&status=published", headers=auth(author))
    assert draft_id not in ids(published_only)
    # mine=true with no status is "my posts and my drafts".
    assert draft_id in ids(client.get("/api/crafts?mine=true", headers=auth(author)))

    for headers in (auth(author), auth(other)):
        feed = client.get("/api/crafts", headers=headers)
        assert draft_id not in ids(feed)
        by_title = client.get("/api/crafts?q=Half-finished", headers=headers)
        assert draft_id not in ids(by_title)
        by_category = client.get("/api/crafts?category=Pottery", headers=headers)
        assert draft_id not in ids(by_category)
        by_tag = client.get("/api/crafts?tag=clay", headers=headers)
        assert draft_id not in ids(by_tag)

    # Searching your own posts is still search: the draft stays out of it.
    own_search = client.get("/api/crafts?mine=true&q=Half-finished", headers=auth(author))
    assert draft_id not in ids(own_search)

    # The other person gets the same answer as a missing post.
    assert client.get(f"/api/crafts/{draft_id}", headers=auth(other)).status_code == 404
    assert client.put(
        f"/api/crafts/{draft_id}",
        json=draft_payload(title="Stolen"),
        headers=auth(other),
    ).status_code == 404
    assert client.delete(f"/api/crafts/{draft_id}", headers=auth(other)).status_code == 404
    assert client.get("/api/crafts?mine=true&status=draft", headers=auth(other)).json() == []
    assert client.get("/api/crafts?status=draft", headers=auth(other)).status_code == 400

    # A draft is not a public post, so it cannot be favorited or reported.
    assert client.post(f"/api/crafts/{draft_id}/favorite", headers=auth(author)).status_code == 400
    assert client.post(
        f"/api/crafts/{draft_id}/reports",
        json={"reason": "Wrong or misleading information", "details": "Should not be possible."},
        headers=auth(author),
    ).status_code == 400
    assert draft_id not in ids(client.get("/api/crafts?favorites=true", headers=auth(author)))


def test_edit_a_draft_then_publish_it_when_it_is_complete(client):
    author, _user = register(client, "editor@example.com", name="Editor")
    other, _other = register(client, "visitor@example.com", name="Visitor")

    created = client.post("/api/crafts", json=draft_payload(), headers=auth(author))
    draft_id = created.json()["id"]

    # Still a draft after an edit that does not fill the required fields.
    edited = client.put(
        f"/api/crafts/{draft_id}",
        json=draft_payload(description="A bowl I have not finished."),
        headers=auth(author),
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["status"] == "draft"
    assert edited.json()["description"] == "A bowl I have not finished."

    # Publishing is rejected, and the saved title is not replaced.
    rejected = client.put(
        f"/api/crafts/{draft_id}",
        json=draft_payload(title="Renamed in a failed publish", status="published"),
        headers=auth(author),
    )
    assert rejected.status_code == 422
    assert any("location" in msg.lower() for msg in rejected.json()["detail"])
    saved = client.get(f"/api/crafts/{draft_id}", headers=auth(author)).json()
    assert saved["status"] == "draft"
    assert saved["title"] == "Half-finished bowl"
    assert client.get("/api/crafts?q=Renamed", headers=auth(other)).json() == []

    published = client.put(
        f"/api/crafts/{draft_id}",
        json=craft_payload(title="Finished bowl", status="published"),
        headers=auth(author),
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    assert published.json()["id"] == draft_id

    assert draft_id not in ids(client.get("/api/crafts?mine=true&status=draft", headers=auth(author)))
    assert draft_id in ids(client.get("/api/crafts?mine=true&status=published", headers=auth(author)))
    assert draft_id in ids(client.get("/api/crafts", headers=auth(other)))
    assert draft_id in ids(client.get("/api/crafts?q=Finished", headers=auth(other)))


def test_search_can_narrow_the_authors_draft_list_only(client):
    author, _user = register(client, "potter@example.com", name="Potter")
    other, _other = register(client, "browser@example.com", name="Browser")

    hidden = client.post(
        "/api/crafts",
        json=draft_payload(
            title="Hidden clay cup",
            description="secret glaze",
            category="Pottery",
            tags=["clay"],
        ),
        headers=auth(author),
    )
    assert hidden.status_code == 201, hidden.text
    hidden_id = hidden.json()["id"]

    visible = client.post(
        "/api/crafts",
        json=craft_payload(title="Visible clay cup", description="public glaze"),
        headers=auth(author),
    )
    visible_id = visible.json()["id"]

    # Public search, the author's own search, and the chips skip the draft.
    for path in (
        "/api/crafts?q=Hidden",
        "/api/crafts?q=secret%20glaze",
        "/api/crafts?category=Pottery",
        "/api/crafts?tag=clay",
        "/api/crafts?mine=true&q=Hidden",
        "/api/crafts?mine=true&category=Pottery",
        "/api/crafts?mine=true&tag=clay",
    ):
        assert hidden_id not in ids(client.get(path, headers=auth(author))), path
        assert hidden_id not in ids(client.get(path, headers=auth(other))), path

    # The published twin is still searchable, including on "my posts".
    assert visible_id in ids(client.get("/api/crafts?mine=true&q=Visible", headers=auth(author)))
    assert visible_id in ids(client.get("/api/crafts?q=public%20glaze", headers=auth(other)))

    # The draft list itself can be narrowed, and it is still private.
    narrowed = client.get(
        "/api/crafts?mine=true&status=draft&q=Hidden&category=Pottery&tag=clay",
        headers=auth(author),
    )
    assert ids(narrowed) == [hidden_id]
    assert client.get(
        "/api/crafts?mine=true&status=draft&q=Hidden",
        headers=auth(other),
    ).json() == []


def test_the_author_can_delete_a_draft(client):
    author, _user = register(client, "remover@example.com", name="Remover")
    created = client.post("/api/crafts", json=draft_payload(title="Throwaway"), headers=auth(author))
    draft_id = created.json()["id"]
    assert client.delete(f"/api/crafts/{draft_id}", headers=auth(author)).status_code == 204
    assert client.get(f"/api/crafts/{draft_id}", headers=auth(author)).status_code == 404
    assert client.get("/api/crafts?mine=true&status=draft", headers=auth(author)).json() == []

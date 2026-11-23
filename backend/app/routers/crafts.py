"""Craft posts: the feed, one post, create, update, delete, favorite, report.

Drafts are a status on the same table, not a second table. A draft is
returned only to its author. The public feed, search, and the category and
tag chips only see published posts. Publishing checks the fields the
requirements treat as mandatory (including a location). The photo is a URL
in this prototype, and it is optional: an empty URL means the page shows
the grey placeholder from the mockup.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import Text, cast, or_
from sqlalchemy.orm import Session as DbSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Craft, Favorite, Report, User
from app.schemas import CraftIn, CraftOut, FavoriteOut, ReportIn, ReportOut
from app.vocabulary import KIND_CATEGORY, KIND_TAG, official_names

router = APIRouter(prefix="/api", tags=["crafts"])


def _favorite_ids(db: DbSession, user_id: int) -> set[int]:
    rows = db.query(Favorite.craft_id).filter(Favorite.user_id == user_id).all()
    return {row[0] for row in rows}


def to_out(craft: Craft, favorited: bool, owner: bool) -> CraftOut:
    return CraftOut(
        id=craft.id,
        title=craft.title,
        description=craft.description or "",
        image_url=craft.image_url or "",
        category=craft.category or "",
        tags=list(craft.tags or []),
        dimensions=craft.dimensions or "",
        colors=craft.colors or "",
        tools=craft.tools or "",
        backstory=craft.backstory or "",
        note=craft.note or "",
        location_text=craft.location_text or "",
        latitude=craft.latitude,
        longitude=craft.longitude,
        status=craft.status,
        card_height=craft.card_height or 240,
        author_name=craft.author.display_name,
        owner=owner,
        favorited=favorited,
        created_at=craft.created_at,
    )


def check_rules(body: CraftIn, db: DbSession) -> None:
    """Server-side checks. The form checks too, but the API is the real gate.

    A pending or rejected name is not official, so it cannot be saved on a
    post. The person proposes it first, and an admin approves it.
    """
    errors: list[str] = []
    categories = official_names(db, KIND_CATEGORY)
    tags = official_names(db, KIND_TAG)
    if not body.title:
        errors.append("Title is required.")
    if body.category and body.category not in categories:
        errors.append(f"'{body.category}' is not an official category.")
    for tag in body.tags:
        if tag not in tags:
            errors.append(f"'{tag}' is not an official tag.")
    if body.status == "published":
        if not body.description:
            errors.append("Description is required to publish.")
        if not body.category:
            errors.append("Pick a category before publishing.")
        if not body.tags:
            errors.append("Pick at least one tag before publishing.")
        if not body.dimensions:
            errors.append("Dimensions are required to publish.")
        if not body.colors:
            errors.append("Colors are required to publish.")
        if not body.tools:
            errors.append("Tools are required to publish.")
        if not body.backstory:
            errors.append("Backstory is required to publish.")
        if not body.location_text:
            errors.append("A location is required to publish.")
    if errors:
        raise HTTPException(status_code=422, detail=errors)


def apply_fields(craft: Craft, body: CraftIn) -> None:
    craft.title = body.title
    craft.description = body.description
    craft.image_url = body.image_url
    craft.category = body.category
    craft.tags = body.tags
    craft.dimensions = body.dimensions
    craft.colors = body.colors
    craft.tools = body.tools
    craft.backstory = body.backstory
    craft.note = body.note
    craft.location_text = body.location_text
    craft.latitude = body.latitude
    craft.longitude = body.longitude
    craft.status = body.status


def is_search_or_filter(q: str | None, category: str | None, tag: str | None) -> bool:
    """True for the search box or a category/tag chip.

    Those look at published posts. The draft list is a different request
    (mine=true and status=draft). That list can use the same filters, and
    it is still only the caller's drafts.
    """
    if category or tag:
        return True
    return bool(q and q.strip())


def _like(term: str) -> str:
    # Escape LIKE wildcards so a search for "%" doesn't match everything.
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped.lower()}%"


def visible_craft(db: DbSession, craft_id: int, user: User) -> Craft:
    craft = db.get(Craft, craft_id)
    if craft is None:
        raise HTTPException(status_code=404, detail="Craft not found.")
    if craft.status == "draft" and craft.author_id != user.id:
        # Same answer as a missing post, so drafts don't leak.
        raise HTTPException(status_code=404, detail="Craft not found.")
    return craft


@router.get("/categories", response_model=list[str])
def categories(
    _user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> list[str]:
    """Official categories. Pending proposals are not included."""
    return official_names(db, KIND_CATEGORY)


@router.get("/tags", response_model=list[str])
def tags(
    _user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> list[str]:
    """Official tags. Pending proposals are not included."""
    return official_names(db, KIND_TAG)


@router.get("/crafts", response_model=list[CraftOut])
def list_crafts(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
    q: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    mine: bool = False,
    favorites: bool = False,
    status: str | None = None,
) -> list[CraftOut]:
    """Published posts, newest first.

    `q`, `category` and `tag` only match published posts. The one exception
    is the caller's own draft list: `mine=true` and `status=draft`, which
    may also be narrowed with those filters. `status=draft` without
    `mine=true` is a 400. `mine=true` on its own returns that user's
    published posts and drafts.
    """
    query = db.query(Craft).join(User, Craft.author_id == User.id)

    if favorites:
        query = query.join(
            Favorite, (Favorite.craft_id == Craft.id) & (Favorite.user_id == user.id)
        ).filter(Craft.status == "published")
    elif mine:
        # My posts, or my drafts when status=draft. Never someone else's.
        query = query.filter(Craft.author_id == user.id)
        if status:
            if status not in ("published", "draft"):
                raise HTTPException(status_code=400, detail="Status must be published or draft.")
            query = query.filter(Craft.status == status)
        elif is_search_or_filter(q, category, tag):
            # Search and the chips are not the draft list. A draft shows up
            # here only when status=draft was asked for explicitly.
            query = query.filter(Craft.status == "published")
    else:
        if status:
            raise HTTPException(
                status_code=400,
                detail="You can only filter by status on your own posts (pass mine=true).",
            )
        query = query.filter(Craft.status == "published")

    if category:
        if category not in official_names(db, KIND_CATEGORY):
            raise HTTPException(status_code=400, detail="Unknown category.")
        query = query.filter(Craft.category == category)
    if tag:
        tag = tag.strip().lower().lstrip("#")
        if tag not in official_names(db, KIND_TAG):
            raise HTTPException(status_code=400, detail="Unknown tag.")
        # Text, not String. Postgres rejects CAST(json AS VARCHAR).
        # SQLite accepts CAST(... AS TEXT), which is what this compiles to.
        query = query.filter(cast(Craft.tags, Text).like(f'%"{tag}"%'))
    if q and q.strip():
        pattern = _like(q.strip()[:100])
        query = query.filter(
            or_(
                Craft.title.ilike(pattern, escape="\\"),
                Craft.description.ilike(pattern, escape="\\"),
                Craft.location_text.ilike(pattern, escape="\\"),
                Craft.backstory.ilike(pattern, escape="\\"),
                Craft.category.ilike(pattern, escape="\\"),
                cast(Craft.tags, Text).ilike(pattern, escape="\\"),
                User.display_name.ilike(pattern, escape="\\"),
            )
        )

    crafts = query.order_by(Craft.created_at.desc(), Craft.id.desc()).limit(200).all()
    fav_ids = _favorite_ids(db, user.id)
    return [to_out(craft, craft.id in fav_ids, craft.author_id == user.id) for craft in crafts]


@router.get("/crafts/{craft_id}", response_model=CraftOut)
def get_craft(
    craft_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> CraftOut:
    """One post. Someone else's draft is a 404, the same as a missing post."""
    craft = visible_craft(db, craft_id, user)
    return to_out(craft, craft.id in _favorite_ids(db, user.id), craft.author_id == user.id)


@router.post("/crafts", response_model=CraftOut, status_code=201)
def create_craft(
    body: CraftIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> CraftOut:
    """Create a post.

    `status=draft` saves an unfinished post. A draft only needs a title.
    `status=published` (the default) checks the required fields, including
    a location. A new draft is visible only to the author.
    """
    check_rules(body, db)
    craft = Craft(author_id=user.id, card_height=240)
    apply_fields(craft, body)
    db.add(craft)
    db.commit()
    db.refresh(craft)
    return to_out(craft, False, True)


@router.put("/crafts/{craft_id}", response_model=CraftOut)
def update_craft(
    craft_id: int,
    body: CraftIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> CraftOut:
    """Replace one of your posts.

    Sending `status=published` is how a draft goes live. The required
    fields are checked first. If that check fails, the saved draft is
    left unchanged. Only the author can update. Someone else's draft is
    a 404.
    """
    craft = db.get(Craft, craft_id)
    if craft is None or (craft.status == "draft" and craft.author_id != user.id):
        raise HTTPException(status_code=404, detail="Craft not found.")
    if craft.author_id != user.id:
        raise HTTPException(status_code=403, detail="You can only change your own posts.")
    # Check before writing. A rejected publish must leave the draft as it was.
    check_rules(body, db)
    apply_fields(craft, body)
    db.commit()
    db.refresh(craft)
    return to_out(craft, craft.id in _favorite_ids(db, user.id), True)


@router.delete("/crafts/{craft_id}", status_code=204)
def delete_craft(
    craft_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> Response:
    craft = db.get(Craft, craft_id)
    if craft is None or (craft.status == "draft" and craft.author_id != user.id):
        raise HTTPException(status_code=404, detail="Craft not found.")
    if craft.author_id != user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own posts.")
    db.query(Favorite).filter(Favorite.craft_id == craft.id).delete()
    db.query(Report).filter(Report.craft_id == craft.id).delete()
    db.delete(craft)
    db.commit()
    return Response(status_code=204)


@router.post("/crafts/{craft_id}/favorite", response_model=FavoriteOut)
def toggle_favorite(
    craft_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> FavoriteOut:
    craft = visible_craft(db, craft_id, user)
    if craft.status == "draft":
        raise HTTPException(status_code=400, detail="Drafts can't be favorited.")
    existing = (
        db.query(Favorite)
        .filter(Favorite.user_id == user.id, Favorite.craft_id == craft.id)
        .one_or_none()
    )
    if existing is None:
        db.add(Favorite(user_id=user.id, craft_id=craft.id))
        favorited = True
    else:
        db.delete(existing)
        favorited = False
    db.commit()
    return FavoriteOut(favorited=favorited)


@router.post("/crafts/{craft_id}/reports", response_model=ReportOut, status_code=201)
def report_craft(
    craft_id: int,
    body: ReportIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> ReportOut:
    craft = visible_craft(db, craft_id, user)
    if craft.status != "published":
        raise HTTPException(status_code=400, detail="Only published posts can be reported.")
    report = Report(
        craft_id=craft.id,
        reporter_id=user.id,
        reason=body.reason,
        details=body.details,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return ReportOut(
        id=report.id,
        craft_id=report.craft_id,
        reason=report.reason,
        details=report.details,
        created_at=report.created_at,
    )


@router.get("/reports", response_model=list[ReportOut])
def my_reports(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> list[ReportOut]:
    """Reports the current user has sent. There is no admin queue yet."""
    rows = (
        db.query(Report)
        .filter(Report.reporter_id == user.id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return [
        ReportOut(
            id=row.id,
            craft_id=row.craft_id,
            reason=row.reason,
            details=row.details,
            created_at=row.created_at,
        )
        for row in rows
    ]


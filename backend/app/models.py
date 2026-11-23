"""Tables for the prototype.

One row in `counter` is the little proof-the-API-works number.
Craft posts, users, sessions, favorites and reports are the rest.
Categories and tags live in `vocabulary`. Who is an admin lives in
`admins`, not as a column on the user. See docs/adr/008-tag-approval.md.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


def utcnow() -> datetime:
    # Stored as UTC. SQLite doesn't have a real timestamp type, so this is
    # just a Python datetime written into a text column.
    from datetime import timezone

    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(255))
    # Always true in this prototype. The column is here so the check in the
    # login route has somewhere to look once email sending exists.
    email_verified: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    crafts: Mapped[list["Craft"]] = relationship(back_populates="author")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()


class Craft(Base):
    __tablename__ = "crafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(140))
    description: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str] = mapped_column(String(500), default="")
    category: Mapped[str] = mapped_column(String(80), default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    dimensions: Mapped[str] = mapped_column(String(120), default="")
    colors: Mapped[str] = mapped_column(String(200), default="")
    tools: Mapped[str] = mapped_column(String(300), default="")
    backstory: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")
    location_text: Mapped[str] = mapped_column(String(200), default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    # "published" shows up in the feed. "draft" is the same row before it is
    # published, and only the author can see it. No second table and no extra
    # column: Render builds tables with create_all, which does not alter a
    # table that already exists. status was already there from the prototype.
    status: Mapped[str] = mapped_column(String(20), default="published", index=True)
    # How tall the grey placeholder is, in pixels. Seeded posts use the
    # heights from the mockup so the masonry grid looks similar. New posts
    # just get a default.
    card_height: Mapped[int] = mapped_column(Integer, default=240)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    author: Mapped[User] = relationship(back_populates="crafts")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "craft_id", name="uq_favorite"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    craft_id: Mapped[int] = mapped_column(ForeignKey("crafts.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    craft_id: Mapped[int] = mapped_column(ForeignKey("crafts.id"), index=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(String(200))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    reporter: Mapped[User] = relationship()
    craft: Mapped[Craft] = relationship()


class Vocabulary(Base):
    """One category or tag.

    status is "official" (it can be picked on a post), "pending" (someone
    proposed it), or "rejected". The craft still stores the name as text.
    name_key is the lowercase form, so "Pottery" and "pottery" cannot both
    exist. A new table is created by create_all; a new column on crafts
    would not be.
    """

    __tablename__ = "vocabulary"
    __table_args__ = (UniqueConstraint("kind", "name_key", name="uq_vocabulary_kind_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # "category" or "tag".
    kind: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(80))
    name_key: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # Empty for the starter list copied from constants.py.
    proposed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    proposer: Mapped[User | None] = relationship()


class Admin(Base):
    """A user who can approve tag and category proposals.

    This is a table of its own so create_all can add it on the Render
    database. A role column on users would not be added to a table that
    already has rows.
    """

    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship()


class Counter(Base):
    """Single-row table. id is always 1."""

    __tablename__ = "counter"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)

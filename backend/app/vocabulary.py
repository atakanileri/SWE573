"""Official categories and tags, plus names people have proposed.

The starter lists still live in constants.py. Startup copies any missing
name into the vocabulary table. After that, an approved proposal is just
another official row. The lists can change without editing this file, and
without adding a column to a table that already exists on Render.
"""

import re

from sqlalchemy.orm import Session as DbSession

from app.constants import CATEGORIES, TAGS
from app.models import Vocabulary

KIND_CATEGORY = "category"
KIND_TAG = "tag"
STATUS_OFFICIAL = "official"
STATUS_PENDING = "pending"
STATUS_REJECTED = "rejected"

# Letters, digits, and single hyphens. "natural dye" becomes "natural-dye".
_TAG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
# Letters (including accents), numbers, spaces, apostrophes, and hyphens.
_CATEGORY = re.compile(r"[\w][\w '&-]*", re.UNICODE)


class BadName(ValueError):
    """A proposal name we can show back to the person as a 422."""


def normalize_tag(raw: str) -> str:
    tag = raw.strip().lower().lstrip("#")
    tag = "-".join(part for part in tag.replace("_", "-").split() if part)
    tag = tag.strip("-")
    while "--" in tag:
        tag = tag.replace("--", "-")
    if len(tag) < 2:
        raise BadName("A tag needs at least 2 characters.")
    if len(tag) > 40:
        raise BadName("A tag can be at most 40 characters.")
    if not _TAG.fullmatch(tag):
        raise BadName("Use letters, numbers, and hyphens for a tag.")
    return tag


def _cap_word(part: str) -> str:
    if part.isupper() or part.islower():
        return part[:1].upper() + part[1:].lower()
    return part[:1].upper() + part[1:]


def normalize_category(raw: str) -> tuple[str, str]:
    cleaned = " ".join(raw.strip().split())
    if len(cleaned) < 2:
        raise BadName("A category needs at least 2 characters.")
    if len(cleaned) > 80:
        raise BadName("A category can be at most 80 characters.")
    if not _CATEGORY.fullmatch(cleaned):
        raise BadName(
            "Use letters, numbers, spaces, apostrophes, and hyphens for a category."
        )
    display = " ".join(_cap_word(part) for part in cleaned.split(" "))
    return display, display.casefold()


def normalize(kind: str, raw: str) -> tuple[str, str]:
    """Return (name to store, comparison key)."""
    if kind == KIND_TAG:
        name = normalize_tag(raw)
        return name, name.casefold()
    if kind == KIND_CATEGORY:
        return normalize_category(raw)
    raise BadName("Kind must be category or tag.")


def find_vocabulary(db: DbSession, kind: str, name_key: str) -> Vocabulary | None:
    return (
        db.query(Vocabulary)
        .filter(Vocabulary.kind == kind, Vocabulary.name_key == name_key)
        .one_or_none()
    )


def official_names(db: DbSession, kind: str) -> list[str]:
    """Official names only. Starter names stay in their old order."""
    rows = (
        db.query(Vocabulary.name)
        .filter(Vocabulary.kind == kind, Vocabulary.status == STATUS_OFFICIAL)
        .all()
    )
    found = {row[0] for row in rows}
    starter = CATEGORIES if kind == KIND_CATEGORY else TAGS
    ordered = [name for name in starter if name in found]
    extras = sorted(name for name in found if name not in set(starter))
    return ordered + extras


def ensure_official_vocabulary(db: DbSession) -> None:
    """Insert starter names that are not in the table yet.

    Safe to run on every boot. A row that is already there is left alone,
    so an admin's decision is not overwritten.
    """
    added = False
    for kind, names in ((KIND_CATEGORY, CATEGORIES), (KIND_TAG, TAGS)):
        for name in names:
            key = name.casefold()
            existing = (
                db.query(Vocabulary.id)
                .filter(Vocabulary.kind == kind, Vocabulary.name_key == key)
                .first()
            )
            if existing is not None:
                continue
            db.add(
                Vocabulary(
                    kind=kind,
                    name=name,
                    name_key=key,
                    status=STATUS_OFFICIAL,
                    proposed_by_id=None,
                )
            )
            added = True
    if added:
        db.commit()

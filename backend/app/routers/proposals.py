"""Propose a tag or category, and let an admin approve or reject it.

A logged-in person can propose a name. It stays pending, and it cannot be
picked on a post, until an admin approves it. The demo account is the admin
(see seed.ensure_demo_admin). An admin who proposes a name adds it straight
to the official list.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session as DbSession

from app.auth import get_current_user, is_admin
from app.database import get_db
from app.models import User, Vocabulary
from app.schemas import ProposalIn, ProposalOut
from app.vocabulary import (
    STATUS_OFFICIAL,
    STATUS_PENDING,
    STATUS_REJECTED,
    BadName,
    find_vocabulary,
    normalize,
)

router = APIRouter(prefix="/api", tags=["proposals"])

_STATUSES = (STATUS_PENDING, STATUS_OFFICIAL, STATUS_REJECTED)


def _word(kind: str) -> str:
    return "tag" if kind == "tag" else "category"


def _require_admin(db: DbSession, user: User) -> None:
    if not is_admin(db, user):
        raise HTTPException(status_code=403, detail="Only an admin can do that.")


def _out(row: Vocabulary, user: User) -> ProposalOut:
    proposed_by = None
    if row.proposer is not None:
        proposed_by = row.proposer.display_name
    return ProposalOut(
        id=row.id,
        kind=row.kind,
        name=row.name,
        status=row.status,
        proposed_by=proposed_by,
        mine=row.proposed_by_id == user.id,
        created_at=row.created_at,
    )


def _get_row(db: DbSession, proposal_id: int) -> Vocabulary:
    row = db.get(Vocabulary, proposal_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    return row


@router.get("/proposals", response_model=list[ProposalOut])
def list_proposals(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
    status: str | None = None,
) -> list[ProposalOut]:
    """Admins see every proposal. Anyone else sees only their own."""
    if status is not None and status not in _STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Status must be pending, official, or rejected.",
        )
    query = db.query(Vocabulary)
    if not is_admin(db, user):
        query = query.filter(Vocabulary.proposed_by_id == user.id)
    if status is not None:
        query = query.filter(Vocabulary.status == status)
    rows = query.order_by(Vocabulary.created_at.desc(), Vocabulary.id.desc()).all()
    return [_out(row, user) for row in rows]


@router.post("/proposals", response_model=ProposalOut)
def propose(
    body: ProposalIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
    response: Response,
) -> ProposalOut:
    try:
        name, name_key = normalize(body.kind, body.name)
    except BadName as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    word = _word(body.kind)
    admin = is_admin(db, user)
    existing = find_vocabulary(db, body.kind, name_key)
    if existing is None:
        row = Vocabulary(
            kind=body.kind,
            name=name,
            name_key=name_key,
            status=STATUS_OFFICIAL if admin else STATUS_PENDING,
            proposed_by_id=user.id,
        )
        db.add(row)
        response.status_code = 201
    elif existing.status == STATUS_OFFICIAL:
        raise HTTPException(
            status_code=409,
            detail=f"That {word} is already on the official list.",
        )
    elif existing.status == STATUS_PENDING and not admin:
        raise HTTPException(
            status_code=409,
            detail=f"That {word} is already waiting for approval.",
        )
    else:
        # An admin adding a pending or rejected name puts it on the list.
        # The person who proposed a rejected name can ask again.
        existing.name = name
        existing.status = STATUS_OFFICIAL if admin else STATUS_PENDING
        existing.proposed_by_id = user.id
        row = existing
        response.status_code = 200

    db.commit()
    db.refresh(row)
    return _out(row, user)


@router.post("/proposals/{proposal_id}/approve", response_model=ProposalOut)
def approve_proposal(
    proposal_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> ProposalOut:
    _require_admin(db, user)
    row = _get_row(db, proposal_id)
    row.status = STATUS_OFFICIAL
    db.commit()
    db.refresh(row)
    return _out(row, user)


@router.post("/proposals/{proposal_id}/reject", response_model=ProposalOut)
def reject_proposal(
    proposal_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> ProposalOut:
    """Reject a proposal that is still pending.

    An official name stays. Posts already store that text, and taking it
    off the list would make those posts fail the next time they are edited.
    """
    _require_admin(db, user)
    row = _get_row(db, proposal_id)
    if row.status == STATUS_OFFICIAL:
        raise HTTPException(
            status_code=400,
            detail="That name is already official, so it stays on the list.",
        )
    row.status = STATUS_REJECTED
    db.commit()
    db.refresh(row)
    return _out(row, user)

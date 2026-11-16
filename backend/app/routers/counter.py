"""A tiny endpoint whose only job is to prove the API talks to the database.

GET returns the current number. POST adds one and returns the new number.
Nothing else in the app depends on it. It is public on purpose, so it can be
tried from the /docs page without logging in, and from the button in the header.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.models import Counter
from app.schemas import CounterOut

router = APIRouter(prefix="/api", tags=["counter"])


def _row(db: DbSession) -> Counter:
    row = db.get(Counter, 1)
    if row is None:
        row = Counter(id=1, value=0)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/counter", response_model=CounterOut)
def read_counter(db: Annotated[DbSession, Depends(get_db)]) -> CounterOut:
    return CounterOut(count=_row(db).value)


@router.post("/counter", response_model=CounterOut)
def increment_counter(db: Annotated[DbSession, Depends(get_db)]) -> CounterOut:
    row = _row(db)
    row.value += 1
    db.commit()
    db.refresh(row)
    return CounterOut(count=row.value)

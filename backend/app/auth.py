"""Passwords and login tokens.

Passwords are hashed with PBKDF2 (from the Python standard library) so the
database never stores the plain password. The login token is a random string
saved in the sessions table. The browser sends it back as:

    Authorization: Bearer <token>

Email verification is not really implemented. Register marks the user as
verified immediately, and login still checks the flag so the spot where a
real check would go is obvious.
"""

import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.models import Session as SessionRow
from app.models import User, utcnow

# 20,000 rounds is enough to not store plain text and still keep the demo
# snappy. A deployed site would turn this number up.
PBKDF2_ROUNDS = 20_000
SESSION_DAYS = 7

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Token from POST /api/auth/login or /api/auth/register.",
)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ROUNDS
    )
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest_hex = stored.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ROUNDS
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_session(db: DbSession, user: User) -> str:
    token = secrets.token_urlsafe(32)
    row = SessionRow(
        token=token,
        user_id=user.id,
        created_at=utcnow(),
        expires_at=utcnow() + timedelta(days=SESSION_DAYS),
    )
    db.add(row)
    db.commit()
    return token


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[DbSession, Depends(get_db)],
) -> User:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=401,
            detail="You need to log in first.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    row = db.query(SessionRow).filter(SessionRow.token == creds.credentials).one_or_none()
    if row is None:
        raise HTTPException(status_code=401, detail="That login token is not valid. Please log in again.")
    expires = row.expires_at
    # SQLite gives back a naive datetime even if we stored one with a timezone.
    if expires.tzinfo is None:
        from datetime import timezone

        expires = expires.replace(tzinfo=timezone.utc)
    if expires < utcnow():
        db.delete(row)
        db.commit()
        raise HTTPException(status_code=401, detail="Your session expired. Please log in again.")
    user = db.get(User, row.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="That login token is not valid. Please log in again.")
    return user

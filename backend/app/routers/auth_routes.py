from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session as DbSession

from app.auth import (
    bearer_scheme,
    create_session,
    get_current_user,
    hash_password,
    is_admin,
    verify_password,
)
from app.database import get_db
from app.models import Session as SessionRow
from app.models import User
from app.schemas import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])

REGISTER_NOTE = (
    "Email verification is stubbed in this prototype. "
    "The account is marked verified straight away, so you can log in now."
)


def _user_out(user: User, db: DbSession) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_admin=is_admin(db, user),
    )


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Annotated[DbSession, Depends(get_db)]) -> TokenOut:
    email = str(body.email).lower()
    existing = db.query(User).filter(User.email == email).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account with that email already exists.")
    user = User(
        email=email,
        display_name=body.display_name.strip(),
        password_hash=hash_password(body.password),
        # Stub: see docs/adr/003-auth.md. There is no verification email.
        email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_session(db, user)
    return TokenOut(token=token, user=_user_out(user, db), note=REGISTER_NOTE)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Annotated[DbSession, Depends(get_db)]) -> TokenOut:
    email = str(body.email).lower()
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is wrong.")
    if not user.email_verified:
        raise HTTPException(
            status_code=403, detail="Please verify your email before logging in."
        )
    token = create_session(db, user)
    return TokenOut(token=token, user=_user_out(user, db))


@router.get("/me", response_model=UserOut)
def me(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> UserOut:
    # Email is included here because this is the logged-in person's own account.
    # Craft responses never include it.
    return _user_out(user, db)


@router.post("/logout", status_code=204)
def logout(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    _user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> Response:
    if creds is not None:
        db.query(SessionRow).filter(SessionRow.token == creds.credentials).delete()
        db.commit()
    return Response(status_code=204)

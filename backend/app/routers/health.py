from fastapi import APIRouter

from app.schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    """Used by Docker and by a person checking that the server is up."""
    return HealthOut(status="ok")

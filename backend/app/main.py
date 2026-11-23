"""The FastAPI app.

Startup creates the tables, makes sure the counter row exists, and loads
the sample crafts the first time. The pages in /frontend are served by
this same process, so the browser and the API share one origin.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import database
from app.models import Counter
from app.routers import auth_routes, counter, crafts, health
from app.seed import demo_email, seed

logger = logging.getLogger("crafts")

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    database.init_db()
    db = database.SessionLocal()
    try:
        if db.get(Counter, 1) is None:
            db.add(Counter(id=1, value=0))
            db.commit()
        if os.environ.get("SEED_DEMO_DATA", "1").strip() != "0" and seed(db):
            # The password is not logged. It is the README default, or
            # whatever DEMO_PASSWORD was set to on this machine.
            logger.info(
                "Test login created for %s. Later startups leave that account as it is.",
                demo_email(),
            )
        logger.info("Indigenous Crafts prototype is up. API docs: /docs")
    finally:
        db.close()
    yield


app = FastAPI(
    title="Indigenous Crafts & Arts API",
    version="0.1.0",
    description=(
        "Prototype API for the SWE 573 Indigenous Crafts & Arts site. "
        "Craft routes need a login token (Authorize button, top right). "
        "A draft is a craft with status \"draft\". It only needs a title, "
        "only its author can read it, and it is left out of the feed and of "
        "search. Publish it later with PUT, once the required fields are set. "
        "Health and the counter are open on purpose, so you can try them "
        "here without logging in. The counter is only there to show that a "
        "request reaches the database and comes back."
    ),
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(counter.router)
app.include_router(auth_routes.router)
app.include_router(crafts.router)

if FRONTEND_DIR.is_dir():
    # Mounted last so /docs, /openapi.json and /api stay with FastAPI.
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

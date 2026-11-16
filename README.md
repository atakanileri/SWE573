This repo is the assignment for the class with the code SWE573 (Software Development Practice).

The site is a small prototype of the Indigenous Crafts & Arts website. People log in, browse a masonry feed of crafts, open a post, and publish a new one. There is a FastAPI backend, a SQLite database, and a plain HTML page that calls the API. It is not the finished product. A lot of the requirements (admin tools, real email, photo upload, a real map) are still missing on purpose. `docs/prototype-guide.md` explains what is here and what is not, and `docs/adr/` is where I wrote down why I picked this stack.

## Run it with Docker

Docker is the way the course wants the project to start.

```bash
docker compose up --build
```

Then open:

- the site: http://127.0.0.1:8000
- the API docs: http://127.0.0.1:8000/docs

The demo account is `atakan@example.com` / `password`. The feed is already filled with sample crafts. The orange **API counter** button in the header (and on the login card) calls `POST /api/counter`. The number should go up by one each click. The same call can be tried from the `/docs` page without logging in.

Stop it with Ctrl+C. The database file lives in a Docker volume named `craft-data`, so the posts are still there the next time you start.

## Run it without Docker

From the repo root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Same URLs as above. The SQLite file is created at `backend/data/crafts.db` (gitignored). Delete that file if you want the sample crafts to be loaded again from scratch.

## Tests

With the virtualenv activated, from `backend/`:

```bash
pytest
```

The tests use a temporary database. They do not touch `crafts.db`.

## Where to read next

- `docs/prototype-guide.md` — folder layout, every endpoint, and how a click gets to the database
- `docs/adr/` — short decision notes (stack, database, auth, frontend, API, Docker)
- `docs/requirements.md`, `docs/userstories.md`, `docs/stakeholders.md` — the course documents this prototype is aiming at

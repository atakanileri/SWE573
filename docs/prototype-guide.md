# Prototype guide

This is the first working cut of the Indigenous Crafts & Arts site for SWE 573. It is meant to be small enough that I can explain every part of it. The requirements, user stories and stakeholder notes in this same `docs/` folder are still the full project. This prototype only covers a slice of them.

## What you can do in it

Log in, see the sample crafts in a masonry grid, open one, search, filter by category or tag, favorite, report, and publish a new craft or save a draft. You can also propose a tag or category. It stays pending until an admin approves it. A draft only needs a title. It shows under **My drafts** for the author, and it is left out of Browse and Search until it is published with the required fields filled in. The orange **API counter** is a separate toy endpoint so I can show that a click reaches the database. It has nothing to do with crafts.

## What is deliberately not here

I left these out so the prototype stayed a prototype.

- No following, no notifications, no "regions" feature. The requirements don't ask for those.
- Email verification is a stub. Register marks the account verified immediately. See `docs/adr/003-auth.md`.
- No password reset email.
- No photo upload. A post stores an image URL, or nothing, and the page shows the grey placeholder.
- The map on a post is a grid with a pin, not a real map. The location text (and optional lat/lng) is what is stored.
- Reports are saved, and you can list your own, but there is no admin screen to hide or delete someone else's post.
- No analytics. The demo account is an admin for tags and categories only. There is still no screen to hide or delete someone else's post, and no screen to appoint another admin.
- The database is not backed up on a schedule. The deployed site is HTTPS because Render terminates TLS. The free Render database expires; see `docs/adr/007-deploy.md`.

## Folder layout

```
Dockerfile              image build
docker-compose.yml      how "docker compose up" starts the app
render.yaml             Render web service + Postgres (ADR 007)
README.md               how to run it, and how to deploy it
backend/
  requirements.txt      Python packages, with versions
  pytest.ini            so pytest can import the app
  app/
    main.py             creates the FastAPI app, starts the database, serves the page
    database.py         SQLite or Postgres, from DATABASE_URL
    models.py           the tables
    schemas.py          the JSON shapes (what /docs shows)
    auth.py             password hash and the login token
    constants.py        starter categories and tags
    vocabulary.py       official list, proposals, name cleanup
    seed.py             sample users and crafts, and the demo admin
    routers/            the actual endpoints, split by topic
  tests/                API tests
frontend/
  index.html            the page structure
  styles.css            the mockup look
  app.js                calls the API
docs/                   requirements, this guide, and the ADR notes
```

`backend/data/` appears when you run without Docker. It is gitignored. Don't commit the `.db` file.

## The endpoints

Interactive docs, with a "Try it out" button on each route: http://127.0.0.1:8000/docs

The raw list is http://127.0.0.1:8000/openapi.json

### Open to everyone

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | `{ "status": "ok" }` if the process is up. Docker's healthcheck uses this. |
| GET | `/api/counter` | The current counter value. Starts at 0. |
| POST | `/api/counter` | Adds 1 and returns the new value. |
| POST | `/api/auth/register` | Creates a user and returns a token. Body: `email`, `password` (at least 6 characters), `display_name`. The `note` field says that email verification was skipped. |
| POST | `/api/auth/login` | Checks the password and returns a token. Body: `email`, `password`. Wrong password is 401 with a vague message, so you can't tell whether the email exists. |

### Need a login token

In `/docs`, click **Authorize** and paste the token from login (without the word Bearer; Swagger adds that). The page does this by itself after you log in.

| Method | Path | What it does |
|---|---|---|
| GET | `/api/auth/me` | The logged-in user, including their own email and `is_admin`. |
| POST | `/api/auth/logout` | Deletes the session. The token stops working. |
| GET | `/api/categories` | Official categories. Pending proposals are not included. |
| GET | `/api/tags` | Official tags. Pending proposals are not included. |
| GET | `/api/crafts` | Published posts, newest first. Drafts are not in this list. |
| GET | `/api/crafts?q=wool` | Search published posts (title, description, location, backstory, category, tags, author name). A draft never matches, including when you also pass `mine=true`. |
| GET | `/api/crafts?category=Pottery` | Published posts in that category. Unknown names are a 400. |
| GET | `/api/crafts?tag=silver` | Published posts that include that tag. |
| GET | `/api/crafts?mine=true` | My published posts and my drafts. |
| GET | `/api/crafts?mine=true&status=published` | Only my published posts. This is what **My posts** calls. |
| GET | `/api/crafts?mine=true&status=draft` | Only my drafts. This is what **My drafts** calls. Another user gets an empty list. |
| GET | `/api/crafts?mine=true&status=draft&q=bowl` | My drafts narrowed by the same search. Still only mine. |
| GET | `/api/crafts?favorites=true` | Published posts I have favorited. |
| GET | `/api/crafts/{id}` | One post. A draft that isn't mine is a 404. |
| POST | `/api/crafts` | Create a post. `status` is `published` or `draft`. A draft only needs a title. |
| PUT | `/api/crafts/{id}` | Replace my post with a new copy of the fields. This is how a draft becomes published. If the required fields are missing, the response is 422 and the saved draft is left as it was. |
| DELETE | `/api/crafts/{id}` | Delete my post, and its favorites and reports. |
| POST | `/api/crafts/{id}/favorite` | Favorite, or un-favorite if it was already on. |
| POST | `/api/crafts/{id}/reports` | Body: `reason`, `details`. Both are required. |
| GET | `/api/reports` | Reports I have sent. Not an admin inbox. |
| GET | `/api/proposals` | My proposals. An admin sees everyone's. `?status=pending` is the review queue. |
| POST | `/api/proposals` | Body: `kind` (`tag` or `category`) and `name`. A normal user creates a pending row. An admin adds the name to the official list. A name that is already official is 409. |
| POST | `/api/proposals/{id}/approve` | Admin only. The name becomes official and can be picked on a post. Anyone else gets 403. |
| POST | `/api/proposals/{id}/reject` | Admin only. A pending name stays off the list. Rejecting an official name is 400, because posts already store that text. |

Publishing without a location (or without the other required fields) is a 422, and `detail` is a list of sentences. A draft can omit them. Search, category and tag never return a draft unless the request is the author's draft list (`mine=true` and `status=draft`).

A pending tag or category is not official, so it cannot be saved on a post and it cannot be used as a filter. After approve, `GET /api/tags` or `GET /api/categories` includes it, and the form's chips reload from those routes.

## How a request gets to the database

Example: I am logged in and I click **Publish** on a new kilim.

1. `app.js` reads the form and sends `POST /api/crafts` with a JSON body. The header is `Authorization: Bearer <token from localStorage>`.
2. Uvicorn, which is the Python web server, hands the request to FastAPI.
3. FastAPI matches the path to `create_craft` in `backend/app/routers/crafts.py`. It parses the JSON into a `CraftIn` object (`schemas.py`). If the types are wrong (a latitude of 999, a weird image URL), it stops here with 422.
4. `get_current_user` in `auth.py` reads the token, loads the row in `sessions`, checks it hasn't expired, and loads the user. If that fails, the route never runs and the response is 401.
5. `check_rules` makes sure a published post has a location, a real category, and so on.
6. The route builds a `Craft` row, `db.add` + `db.commit` writes it to SQLite, and the response JSON goes back. The new id is in that JSON.
7. The page shows the toast "Your craft is published!" and calls `GET /api/crafts` again, so the new card is at the top of the grid.

Saving a draft is the same path with `"status": "draft"`. `check_rules` then only requires a title (and a real category or tag, if you sent one). The row is written with status draft. `GET /api/crafts` leaves it out, including when `q` is set. `GET /api/crafts?mine=true&status=draft` returns it to the author. Publishing later is a PUT of that same id. The check runs before the write, so a 422 does not change the draft.

The counter is the same path with fewer steps. `POST /api/counter` doesn't look at the token. It loads row 1 of the `counter` table, adds one, commits, and returns the number. The button just puts that number on the screen.

The database is opened in `database.py`. The URL comes from the environment variable `DATABASE_URL`. If it isn't set, the file is `backend/data/crafts.db` (SQLite). Docker Compose points it at a SQLite file on a volume. Render points it at Postgres; `postgres://` and `postgresql://` are rewritten so SQLAlchemy uses the psycopg driver. Tables are created on startup if they don't exist (`create_all`). Nothing here migrates old tables; if I change a column during development I delete the file (or the Render database) and let it recreate. That is fine while the data is sample data. Drafts did not need that: a draft is the existing `status` column set to `draft`.

`seed.py` runs on startup only when the users table is empty. Restarting does not duplicate the sample crafts.

## What the Docker files do

`Dockerfile`

- Starts from the small official Python 3.12 image.
- Copies `requirements.txt` and installs it.
- Copies the backend and the frontend into `/app`.
- Sets `PYTHONPATH` so `import app` works, and points `DATABASE_URL` at `/data/crafts.db`. Render overrides that URL.
- Runs `uvicorn app.main:app` on `0.0.0.0` and on `$PORT` (8000 when `PORT` is unset) so it is reachable from outside the container.

`docker-compose.yml`

- Builds that image as the service `web`.
- Publishes port 8000.
- Mounts a volume called `craft-data` at `/data`, which is where the database file sits.
- Checks `/health` every few seconds so you can see whether the container is actually serving.

`docker compose up --build` is the whole start sequence. The first time, the image builds and the sample crafts are inserted. After that, new posts stay in the volume.

## Tests

From the repo root, inside Docker:

```bash
docker compose run --rm --build web pytest -v
```

Or from `backend/`, with the dependencies installed:

```bash
pytest -v
```

`tests/conftest.py` points `DATABASE_URL` at a temporary file for each test and starts the app with FastAPI's TestClient, so the tests hit the real routes. They cover health, the counter, the docs page, login, the seeded feed, creating a post, the location rule, drafts (save an unfinished one, hide it from the feed and from search, edit it, reject a publish that is still incomplete, then publish it), edit/delete permissions, search, favorites, reports, logout, and tag approval (propose, the 403 for a non-admin, approve, reject). `tests/test_drafts.py` is the draft file. `tests/test_tag_approval.py` is the tag file. The draft file also calls `check_rules` directly, which is the same check the routes use.

## Demo account

`atakan@example.com` / `password`

That user owns the "Hand-woven Yörük kilim" sample post, and that user is the admin for tag and category proposals. Startup writes a row in `admins` for this email every time, including when the sample crafts are not inserted again. The other names on the cards are sample authors. I generated passwords for them and did not write them down, so they can't be used to log in.

To try a proposal: register a second account, open **New Craft**, type a tag under the official chips, and click **Propose**. It will not appear in the chips. Log out, log in as `atakan@example.com`, open **Proposals** in the account menu, and click **Approve**. The tag can then be picked on a post.

`DEMO_EMAIL` and `DEMO_PASSWORD` replace that login the first time the sample data is inserted. They do not change a database that already has users. The deployed site sets them in `render.yaml` to the same public values.

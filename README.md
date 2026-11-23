This repo is the assignment for the class with the code SWE573 (Software Development Practice).

The site is a small prototype of the Indigenous Crafts & Arts website. People log in, browse a masonry feed of crafts, open a post, and publish a new one. There is a FastAPI backend, a database (SQLite on your machine, Postgres when it is deployed), and a plain HTML page that calls the API. It is not the finished product. A lot of the requirements (admin tools, real email, photo upload, a real map) are still missing on purpose. `docs/prototype-guide.md` explains what is here and what is not, and `docs/adr/` is where I wrote down why I picked this stack.

## System requirements

To run it the way the course expects:

- Git
- Docker Engine and the Docker Compose v2 plugin (the command is `docker compose`, with a space)
- A web browser

To run it without Docker: Python 3.12 and `pip`. The packages are pinned in `backend/requirements.txt`.

To put it on the public internet: a [Render](https://render.com) account and access to this GitHub repo. Render builds the same `Dockerfile`. You do not install Python or Postgres on Render yourself. The steps are at the bottom of this file.

## Run it with Docker

From the repo root:

```bash
docker compose up --build
```

The first time, Docker downloads the Python image and installs the packages. Later starts are quicker.

Then open:

- the site: http://127.0.0.1:8000
- the API docs (Swagger): http://127.0.0.1:8000/docs

The test account is `atakan@example.com` / `password`. The feed is already filled with sample crafts. The orange **API counter** button in the header (and on the login card) calls `POST /api/counter`. The number should go up by one each click. The same call can be tried from the `/docs` page without logging in.

Stop it with Ctrl+C. The database file lives in a Docker volume named `craft-data`, so the posts are still there the next time you start.

`docker compose down` stops the container and keeps the volume. `docker compose down -v` deletes the volume too. The next start loads the sample crafts again.

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

## Environment variables

None of these are required on your own machine. The defaults are what `docker compose up` and the local `uvicorn` command use. On Render, `render.yaml` sets them. Do not commit a `.env` file, and do not commit a real database password.

| Variable | Required? | Default | What it does |
|---|---|---|---|
| `PORT` | Set by Render | `8000` | The port uvicorn listens on. Render sends traffic to this port (their default is `10000`). Compose publishes `8000`. |
| `DATABASE_URL` | On Render, yes | SQLite file `backend/data/crafts.db` | SQLAlchemy URL. Compose sets `sqlite:////data/crafts.db`. Render sets a Postgres URL from the database in `render.yaml`. `postgres://` and `postgresql://` are rewritten to `postgresql+psycopg://` in `database.py`. |
| `SEED_DEMO_DATA` | No | `1` | `1` loads the sample users and crafts when the users table is empty. `0` skips that. Restarting does not insert them again. |
| `DEMO_EMAIL` | No | `atakan@example.com` | Test account email, used only when the sample data is first inserted. |
| `DEMO_PASSWORD` | No | `password` | Test account password. This is a public class login, also written in `render.yaml`. It is not a private secret. If you pick a different one, set it in the environment of the machine that runs the app. Do not commit it. Changing it after the first boot does nothing, because the seed skips a database that already has users. |

`PORT` is read by the process command in the `Dockerfile`, not by Python. The others are read when the app starts.

## Tests

The tests use a temporary SQLite file. They do not touch `crafts.db` or the Docker volume.

With Docker, from the repo root (this is the command to trust):

```bash
docker compose run --rm --build web pytest -v
```

`--build` picks up code changes. `--rm` deletes the test container afterwards. Pytest's working directory inside the image is `/app/backend`.

Without Docker, from `backend/` with the virtualenv activated:

```bash
pytest -v
```

## Where to read next

- `docs/prototype-guide.md` — folder layout, every endpoint, and how a click gets to the database
- `docs/adr/` — short decision notes (stack, database, auth, frontend, API, Docker, deploy)
- `docs/requirements.md`, `docs/userstories.md`, `docs/stakeholders.md` — the course documents this prototype is aiming at

## Deploy it on Render

The public site is a free Render web service running this Docker image, plus a free Render Postgres database. SQLite is not used there: the free web service's disk is wiped on every restart, and a free service sleeps after 15 minutes of no visitors. Postgres keeps the posts. The trade-off is written up in `docs/adr/007-deploy.md`. The short version: the free database expires 30 days after you create it, it is not backed up, and there can be only one free Postgres database in your Render account.

Render gives the site an `https://….onrender.com` address, so you do not configure TLS yourself. Swagger stays at `/docs`.

These are the steps. A person who only has this README and the repo should be able to follow them.

1. Push the branch that contains `render.yaml` to GitHub. Until that branch is merged, it is `cursor/crafts-prototype-3cd1`. After it is merged, `main` is enough.
2. Create a Render account at https://render.com. Signing up with GitHub is the least confusing, because the next step connects the same account.
3. In the Render Dashboard, click **New** and choose **Blueprint**.
4. Connect GitHub if Render asks. Grant it this repo (`atakanileri/SWE573`). You do not need to grant it every repository you have.
5. Select this repo. If Render asks which branch, choose the branch from step 1. Render reads `render.yaml` from that branch.
6. Read the plan it is about to create. It should be two resources, both **Free**:
   - a web service named `indigenous-crafts` (Docker)
   - a Postgres database named `indigenous-crafts-db`
7. You should not have to type any environment variable. The blueprint sets `DATABASE_URL` from the database (the password stays in Render), `SEED_DEMO_DATA=1`, `DEMO_EMAIL=atakan@example.com`, and `DEMO_PASSWORD=password`. If the screen asks you to confirm those, accept them. Do not paste the database URL into the repo.
8. Confirm both plans still say **Free**, then apply the blueprint. Render's own default for a new web service is a paid size if `plan` is left out; `render.yaml` sets `free` on purpose. If a name is already taken in your account, change the name in `render.yaml`, push, and sync the blueprint again. The web service and the database must keep the same `region`.
9. Wait until the web service says it is live. The first Docker build takes a few minutes. The logs should include a line about the test login email. A failure that says the database is not ready is worth one redeploy: startup tries five times, but a brand-new database can be slower than that.
10. Open the URL on the web service page (it looks like `https://indigenous-crafts.onrender.com`). Log in with `atakan@example.com` / `password`. Open `/docs` on that same host and try `GET /health`.

After this, a push to the branch Render is watching builds and deploys again. Posts stored in Postgres survive that. Posts would not survive it if the app were using a SQLite file on the web service's disk.

The free web service sleeps after about 15 minutes with no visitors. The next visit can take about a minute while Render starts it. That is normal for the free plan. The free database stops working 30 days after it was created unless you upgrade it to a paid plan. Render emails you before that. There is no automatic backup.

If you want a different test password, set `DEMO_PASSWORD` on the web service's **Environment** page and deploy **before the first successful boot**, or delete the database rows and redeploy. The seed does not overwrite a user that is already there.

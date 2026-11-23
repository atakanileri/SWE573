# ADR 006 — Docker

Status: accepted (November 2026). The course expects the project to start with Docker.

## What I had to decide

Someone else (or me, on another machine) should be able to run the prototype with one command, including the Python dependencies. The database file should not disappear every time the container is recreated.

## What I picked

One image, described in `Dockerfile`, and one service in `docker-compose.yml` named `web`.

The image is `python:3.12-slim`. It installs `backend/requirements.txt`, copies `backend/` and `frontend/`, and starts uvicorn. The port is `PORT` if that variable is set, and 8000 if it is not. Compose does not set `PORT`, and it maps 8000 on the machine to 8000 in the container. Render does set `PORT` (ADR 007). `DATABASE_URL` in Compose is `sqlite:////data/crafts.db`, and `/data` is the named volume `craft-data`.

There is also a healthcheck that calls `GET /health`.

I can still run it without Docker. That is written in the README: a venv, `pip install`, and `uvicorn`. Same app, database file under `backend/data/` instead of the volume.

## Why one container

The page and the API are the same process (see ADR 001), and SQLite is a file, not a server. A second container would only be there to look more like a "real" deployment. I would be explaining nginx or a Postgres container instead of the craft routes.

The volume is the part I didn't want to skip. Without it, the SQLite file would live inside the container filesystem and a rebuild would wipe the posts I created during a demo.

`requirements.txt` is copied and installed before the rest of the code. Docker caches that step, so a small Python change doesn't download the packages again.

## What else I thought about

Postgres as a second Compose service. That's the setup I expect later (ADR 002). Not now.

Two images, one for a static frontend and one for the API. Rejected for the same reason as a frontend framework: more parts, same demo.

Putting the database file in a bind mount to a folder in the repo (for example `./data`). Easier to inspect with a SQLite browser, but it is also easy to commit the file by mistake, and on some machines the permissions get annoying. A named volume keeps it out of git. If I need to look inside it I can `docker compose exec` and open the file.

## What I might regret

The image runs uvicorn as root, with one worker, and with no HTTPS. That is normal for a local prototype and not how I would put it on a server. HTTPS is a requirement for the real site (NFR-01). It belongs in front of this container, not inside the prototype's Python code. I also don't take database backups. The requirement mentions backups. A volume is not a backup. I haven't automated one yet.

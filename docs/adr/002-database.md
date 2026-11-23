# ADR 002 — SQLite for the prototype

Status: accepted for the first prototype (November 2026). Local runs and Docker Compose still use SQLite. The deployed site uses Postgres; that decision is ADR 007.

## What I had to decide

The posts, users and the little counter have to live in a real database, not in a JavaScript array that disappears on refresh. Issue #6 mentions MySQL, PostgreSQL or MongoDB as options to look at.

## What I picked

SQLite, through SQLAlchemy. The whole database is one file.

- Locally that file is `backend/data/crafts.db`.
- In Docker it is `/data/crafts.db`, on a named volume, so it survives `docker compose down` and a new container.

## Why

I wanted a database I can open and explain, without running a second service. SQLite is a real database (tables, queries, constraints) and it starts with the app. For a prototype with one user at a time and a handful of sample posts, that is enough.

SQLAlchemy is the layer between the Python objects and the SQL. If I later switch to PostgreSQL, the models stay similar and I mostly change the URL. That is the "good reason" I would give for not starting on Postgres today: I can move, and I didn't want a database container in the first demo.

The counter is a row in a table (`counter`, always id 1). GET reads it, POST adds one and commits. If that number changes and stays changed after a refresh, the request really reached the database.

## What else I thought about

PostgreSQL. This is what I would pick for a deployed version. More than one person can write at the same time, and it matches what issue #6 is thinking about. It needs its own container, a password, and a wait-until-ready step in Compose. That is worth it later, not for the first cut.

MySQL. Same idea as Postgres for this project. I don't have a reason to prefer it over Postgres, so I didn't add it.

MongoDB. The posts are a fixed shape (title, tags, location, status). That fits tables better than a document store, and the course requirements talk about drafts and "only the author can see this", which is a normal query. I would be fighting the tool.

## What I might regret

SQLite locks the whole file on a write. Two people hitting "publish" at the same moment is not a case I tested. The foreign-key checks are off unless the connection turns them on, so `database.py` runs `PRAGMA foreign_keys=ON` on every connection. I still delete favorites and reports in the delete route myself, so a post doesn't leave junk behind even if that pragma were forgotten.

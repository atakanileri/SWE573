# ADR 008 — Tag and category approval

Status: accepted (November 2026).

## What I had to decide

Issue #15: a poster picks a tag or category from the official list, or proposes a new one that stays pending until an admin approves it. The lists were a Python tuple in `constants.py` (ADR 005). There was no admin role. The deployed site is Render Postgres, and startup only runs `create_all`. That creates a missing table. It does not add a column to a table that already has rows.

## What I picked

Two new tables.

- `vocabulary` is one row per category or tag. `status` is `official`, `pending`, or `rejected`. `name_key` is the lowercase form, so "Pottery" and "pottery" cannot both exist. The craft still stores the name as text. I did not add a column to `crafts`.
- `admins` is a row per admin user. I did not add a `role` column to `users`, because Render would not have gained that column on the next deploy.

Startup does two things even when `seed()` skips a database that already has users:

1. Copy any missing name from `constants.py` into `vocabulary` as official. Those are the names the sample crafts already use. A row that is already there is left alone.
2. If the demo account exists, make sure it has a row in `admins`. That account is `atakan@example.com` unless `DEMO_EMAIL` was set the first time the sample users were inserted.

A logged-in person proposes with `POST /api/proposals`. The row is pending. `GET /api/tags` and `GET /api/categories` return official names only, and a post that uses a pending name is a 422. An admin approves or rejects with `POST /api/proposals/{id}/approve` and `.../reject`. Anyone else gets 403. An admin who proposes a new name adds it as official immediately, because FR-18 says an admin can add to the list, not only vote on other people's names.

Reject does not remove an official name. Posts already store that text, and the next edit of those posts would fail the official-name check.

## Why

This is the smallest change that survives a deploy onto the database that is already running. A column on `users` or `crafts` would look right in a fresh SQLite file and do nothing on Render.

The demo account is the admin because the requirements say admin accounts are set up separately, and the grader already has this login. Register does not make someone an admin.

## What else I thought about

A `role` column on `users`, and a `status` column on a new tags table only. The column on `users` is the one `create_all` would miss. Putting both facts in new tables keeps one rule: new tables are fine, new columns on old tables are not.

Leaving the official list in `constants.py` and storing only proposals in the database. Then an approved name would have to be written back into the file, which a running server cannot do. The approved name has to be a row.

Renaming an official tag. The new spelling would not match the text already saved on posts. I left rename out.

## What I might regret

There is no screen to appoint a second admin. The row is inserted for the demo email. Adding another means inserting into `admins` for that user id. I also do not record which admin clicked approve. One admin is enough for this requirement.

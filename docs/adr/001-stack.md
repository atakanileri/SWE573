# ADR 001 — What the prototype is built with

Status: accepted for the first prototype (November 2026).

## What I had to decide

Issue #5 is still "explore the tech stack". I needed something I can actually run and explain in a demo, with a backend, a database, and a page that looks like the mockup. I also need to be able to show the API itself, not only the website.

## What I picked

Python and FastAPI for the server. The page is plain HTML, CSS and JavaScript, served by that same server. SQLite is the database; the reason for that one is in the next note.

## Why

FastAPI builds the `/docs` page on its own. For this course that is a big deal, because I have to point at the endpoints and try them. I didn't want to spend the prototype writing a documentation site by hand.

One process serves both the page and the API. The browser just calls `/api/...` on the same origin, so I don't have a CORS problem and I don't have two servers to start.

I already know enough Python to read these route functions later and defend them. That mattered more than picking the most popular framework.

## What else I thought about

Django. A lot of the examples in class-style projects use it, and the admin site would be useful later for reports and tags. I didn't use it here because the API would be an add-on (Django REST framework) instead of the thing the prototype is about, and I would get a lot of machinery I don't need yet.

Express, or another Node server. Perfectly fine, but then the interactive docs are something I have to add myself.

A React or Vue app with its own dev server. The mockup is one feed, a popup and a form. A framework would mean a build step and, in Docker, probably a second container. I would be learning the framework instead of getting a post saved in the database.

## What I might regret

If the pages get much more complicated, a frontend framework will be less painful than a growing `app.js`. The API can stay. I am not promising I will never move to Django either, but that would be a rewrite of the routes, so I only want to do it with a real reason.

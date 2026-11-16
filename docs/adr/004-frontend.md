# ADR 004 — A plain page that follows the mockup

Status: accepted for the prototype (November 2026).

## What I had to decide

The interactive mockup is a Pinterest-style grid, a detail popup, and a "new craft" form, plus a login gate. The prototype has to look like that and it has to call the API. I didn't want a frontend framework just to copy one layout.

## What I picked

Three files in `frontend/`:

- `index.html` is the structure (header, feed, form, login card, popups).
- `styles.css` is the look. The colours, the rounded search box, the chips and the masonry columns are taken from the mockup (`column-count` for the grid, the orange `#c0582b` for buttons).
- `app.js` talks to the API and draws the cards.

FastAPI serves those files. There is no npm build.

The grey diagonal box is the placeholder from the mockup. If a post has an image URL, the page shows that image and falls back to the placeholder when the link is broken. Sample posts have no image URL, so the feed looks like the mockup screenshots.

The "API counter" pill is not in the mockup. I added it on the header and on the login card so a click is visible proof that the API works, including before anyone logs in.

## Why

I can open `app.js` and follow one click (for example "Publish") down to a `fetch` call. That is the level I want for the first prototype. The mockup was already written as one HTML file with a similar layout, so matching it in CSS was straightforward.

Search and the category/tag chips call `GET /api/crafts` with query parameters, instead of filtering a big list in the browser only. The detail popup calls `GET /api/crafts/{id}`. Favorite, report, create, update and delete each hit their own route. The preview button does not. It only opens the popup with what is currently typed, which matches the mockup and doesn't need an endpoint.

## What else I thought about

React. Components would split the card, the modal and the form nicely. I would then need Node in the Docker image and a build, and the demo would depend on that build succeeding. Not worth it yet.

Server-rendered templates (Jinja). The page would work without `app.js`, but the mockup is very interactive (chips, popup, draft, counter) and I would still end up writing JavaScript. Calling the JSON API from the page also makes the API a real part of the demo, not only something that exists at `/docs`.

Copying the mockup's sample data into the browser and not calling the API. That would look right and prove nothing. I didn't do it.

## What I might regret

`app.js` is one file and it will get messy if I add an admin page. Splitting it can wait until that happens. The little map is not a map library. It is a grey grid with a pin, same as the mockup. Latitude and longitude are stored when you type them (or when you click the sample pin, which drops Toros, Mersin). A real map is a later change, and the fields for it are already on the post.

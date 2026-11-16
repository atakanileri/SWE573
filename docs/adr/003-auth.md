# ADR 003 — Login, and the email check I did not build

Status: accepted for the prototype, with a stub I need to be honest about (November 2026).

## What I had to decide

The requirements say a visitor who is not logged in only sees a landing page, and that registration needs a verified email. Passwords must be hashed. I do not have an email server, and building a real verification flow would have eaten the prototype.

## What I picked

A small, real login, plus a clearly marked stub for email.

- Register and login take an email and a password.
- The password is hashed with PBKDF2-HMAC-SHA256 (Python's `hashlib`), 20,000 rounds, and a random salt. The database stores `salt$hash`, never the password.
- A successful login creates a random token in the `sessions` table, valid for 7 days. The browser keeps it in `localStorage` and sends `Authorization: Bearer <token>` after that.
- Logout deletes that row, so the token stops working.
- Craft routes refuse the request with 401 if the token is missing, unknown, or expired.
- On register, `email_verified` is set to true immediately. Login still checks the flag. The register response says, in the `note` field, that verification is stubbed. The login card on the site says the same thing in plain language.

There is no "forgot password" flow. The login page says so, instead of showing a button that does nothing.

The demo account loaded with the sample posts is `atakan@example.com` / `password`. That password is fine for a class demo and must not be reused anywhere real.

## Why this and not a fake login

A totally fake login (any password works, no database) would make the "you have to be logged in" rule a lie, and I couldn't show a hashed password if someone asked. This version is small enough to read in one file (`backend/app/auth.py`) and still does the thing the requirement is about: the feed is behind an account, and the password is not stored in the clear.

20,000 rounds is lower than I would use on a public site. I turned it down so the tests and the first startup stay quick. Raising the number later does not change the shape of the hash.

## What else I thought about

JWT (a signed token with no database row). Nice because the server doesn't store sessions. I didn't use it because then logout can't really kill a token, and I wanted a row I can point at in the database.

Flask-Login or Django's auth. Both are good, and both belong to a different stack than the one in ADR 001.

Sending real verification email. That needs SMTP credentials I don't have in this repo. I left the column and the check so the missing piece has an obvious place to go.

## What I might regret

`localStorage` means a script on the page can read the token. That is acceptable on a prototype served as static files by the same app. A later version can move the token to an HttpOnly cookie. I also store the token itself in the sessions table, not a hash of it. Hashing it would be safer if the database file leaked. I left it readable so I can match "the string the browser sends" to "the row in the table" while debugging.

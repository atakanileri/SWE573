# Stakeholders

## Viewers

A visitor or logged-in user who consumes content.

### Must
- Register with an email address, including email verification.
- Log in with their registered email address and password.
- Stay logged in across sessions.
- View other users' posts.

### Could
- Like or favorite posts.
- Add or propose new tags and categories.

---

## Posters

A logged-in user who publishes craft posts. Inherits Viewer capabilities.

### Must
- Post a craft.
- Add details to a craft post, such as:
  - tags
  - categories
  - dimensions
  - colors
  - tools
  - backstory
  - geolocation
  - any specific custom text

### Should
- View their own posts.

### Could
- Create a draft post before publishing.

---

## Developers

Administrative/technical stakeholders responsible for platform health and moderation.

### Must
- View traffic/analytics.
- Administrate posts.
- Receive reports.
- Add new categories and tags.

---

## Priority Key

- **Must** = required for MVP / core functionality
- **Should** = important but not strictly blocking
- **Could** = nice-to-have / future enhancement

---

## Assumptions

- Posters inherit all Viewer capabilities.
- Developers likely need admin-level permissions beyond normal users.
- “Administrate posts” may include hiding, editing, deleting, restoring, or flagging posts.
- Reports likely need a review queue or notification flow.
- Tags and categories created by Developers are official; user-proposed tags/categories may need approval.

---

## Open Questions

1. Can anonymous visitors view posts, or must Viewers always log in?
- No, every person on the website should be logged in with a registered account.
2. How are reports submitted, reviewed, resolved, and audited?
- Reports will be created by Viewers or Posters, through a "Report" button. They will write in detail what is wrong with the posts.
3. Are drafts private only, or can they be shared?
- Yes, only the Poster can see their draft, to visualize how it would be seen on the website.
4. Is geolocation required, optional, or privacy-sensitive?
- Required for every craft.

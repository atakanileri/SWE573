# Requirements — Indigenous Crafts & Arts Website

## 1. Introduction

This project is a website where people share and browse indigenous crafts and arts. Each craft post carries its own details: tags, categories, dimensions, colors, tools, a backstory, a location, and any extra text the author wants to add.

The requirements below come from `stakeholders.md`, `userstories.md` and the project issues. Features like following users, notifications or selling crafts are not part of this project.

### Roles

- Viewer: a registered, logged-in user who browses posts.
- Poster: a logged-in user who publishes craft posts. A Poster can do everything a Viewer can. In practice, every registered user can both view and post.
- Admin (called "Developers" in `stakeholders.md`): manages posts, reports, tags and categories, and looks at site traffic.

Priorities use MoSCoW (Must, Should, Could), as in `stakeholders.md`.

## 2. Guest access

Users need an account to see content on the site. This was decided in `stakeholders.md`. Without logging in, a visitor can only see a short landing page and the register, login and password reset pages. Posts, images and locations are only shown to logged-in users. This keeps the craftspeople's content and locations away from anonymous visitors and makes every report traceable to an account.

## 3. Functional requirements

### Account

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Users can register with an email address and must verify it before logging in. | Must |
| FR-02 | Users can log in with their email and password and stay logged in across sessions. | Must |
| FR-03 | Users can log out and reset a forgotten password by email. | Should |
| FR-04 | Pages with content are only available to logged-in users. | Must |

### Craft posts

| ID | Requirement | Priority |
|---|---|---|
| FR-05 | Posters can create a craft post using a "New Craft" button. | Must |
| FR-06 | A post includes a title, description, tags, categories, dimensions, colors, tools, backstory and location. Custom text is optional. | Must |
| FR-07 | A post can't be published without a location. | Must |
| FR-08 | Posters can preview a post before publishing it. | Should |
| FR-09 | Posters can see a list of their own posts and drafts. | Should |
| FR-10 | Posters can edit or delete their own posts. | Should |
| FR-23 | Posters must add at least one photo of the craft before publishing. | Must |

### Drafts

| ID | Requirement | Priority |
|---|---|---|
| FR-11 | Posters can save a post as a draft and publish it later. | Could |
| FR-12 | Only the author can see a draft. Drafts can't be shared. | Must (if drafts are built) |

### Browsing and search

| ID | Requirement | Priority |
|---|---|---|
| FR-13 | Logged-in users can browse a list of published posts and open a post to see all its details. | Must |
| FR-14 | Users can search posts and filter them by tag or category. | Should |
| FR-15 | A post's location is shown on a map on its page. | Should |

### Tags and categories

| ID | Requirement | Priority |
|---|---|---|
| FR-16 | Posters can pick tags and categories from the official list. | Must |
| FR-17 | Users can propose new tags and categories. These stay pending until an admin approves them. | Could |
| FR-18 | Admins can add and manage official tags and categories, and approve or reject proposals. | Must |

### Social

| ID | Requirement | Priority |
|---|---|---|
| FR-19 | Users can like or favorite posts. | Could |

### Reporting and moderation

| ID | Requirement | Priority |
|---|---|---|
| FR-20 | Users can report a post with a "Report" button and explain the problem in writing. | Must |
| FR-21 | Admins can review reports and hide, restore, edit or delete any post. | Must |

### Admin

| ID | Requirement | Priority |
|---|---|---|
| FR-22 | Admins can see basic traffic numbers, such as visits, new users and new posts. | Must |

## 4. Non-functional requirements

| ID | Requirement | Priority |
|---|---|---|
| NFR-01 | Passwords are stored hashed, the site runs over HTTPS, and user input is validated on the server. | Must |
| NFR-02 | Every action checks the user's role and ownership. For example, only admins can open the admin pages, and only the author can edit their own post. | Must |
| NFR-03 | Email addresses are not shown to other users, and drafts are never visible to anyone but their author. | Must |
| NFR-04 | The site works on both phones and desktop browsers. | Must |
| NFR-05 | The site follows basic accessibility practices: images have alt text, colors have readable contrast, form fields have labels, and the site can be used with a keyboard. | Should |
| NFR-06 | Pages load quickly under normal use, and large images are resized before they are shown. | Should |
| NFR-07 | The code has automated tests and a README that explains how to set up, run and test the project. | Must |
| NFR-08 | The project can be run with Docker, and the database is backed up regularly. | Should |

## 5. Assumptions

- Every registered user is both a Viewer and a Poster. Admin accounts are set up separately.
- "Administrate posts" means hiding, restoring, editing and deleting posts.

## 6. Open questions

- The tech stack isn't decided yet (issue #5). The database could be MySQL, PostgreSQL or MongoDB (issue #6).
- Is a specific framework, such as Django, allowed or expected for the course?
- What exactly should "traffic/analytics" include?
- Should the exact location be shown on the map, or a rough area?
- Do user-proposed tags and categories always need approval? The notes say they "may" need it.

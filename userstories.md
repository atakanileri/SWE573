# User Story 1 — Poster Creates and Drafts a Craft Post

## User Story
As a logged-in Poster, who inherits all Viewer capabilities, I want to create a craft post with details such as tags, categories, dimensions, colors, tools, backstory, geolocation, and custom text, and save it as a private draft before publishing, so that I can prepare rich content and preview how it will appear on the website.

## Priority
- **Must:** Create a craft post and add required details, including geolocation.
- **Should:** View my own posts.
- **Could:** Save a draft post before publishing.

## Preconditions
- The user is registered, email-verified, and logged in.
- The user has Poster capabilities and inherits all Viewer capabilities.
- Official categories and tags may already exist.
- User-proposed tags/categories may require approval.
- Geolocation is required for every craft before publishing.

## Acceptance Criteria
- Poster can create a craft post.
- Poster is required to add tags, categories, dimensions, colors, tools, backstory, geolocation, and optionally custom text.
- Geolocation is required before publishing.
- Poster can save a draft, and only the Poster can see it.
- Poster can view and preview their own posts and drafts.
- Published posts are visible to other logged-in users.
- User-proposed tags/categories may require approval.

## Postconditions
- A craft post is either saved as a private draft or published.
- Drafts remain visible only to the Poster.
- Published posts contain all provided details, including required geolocation.
- User-proposed tags/categories are stored and may enter an approval workflow.
- The Poster can view their own published posts and drafts.
- Other logged-in users can view the published post according to platform rules.

## Assumptions
- Posters inherit all Viewer capabilities.
- Drafts are private only and cannot be shared.
- Geolocation is required for every craft.
- Developers manage official categories and tags; user-proposed ones require approval.

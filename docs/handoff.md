# Pulse — Developer Handoff Notes

## MVP v0.1 Status

All core features are implemented and runnable locally.

## What's Built

- User registration, login, logout (session-based auth)
- Password hashing (werkzeug pbkdf2:sha256)
- CSRF protection on all POST forms
- Topic feed filtered by user interests
- Topic detail with source links
- Reactions (one per user per topic, toggle off by re-clicking)
- Profile view and edit
- Interests selection
- Civic Units placeholder page
- Admin seed route (development only)
- Mobile-first responsive CSS

## What's Not Built (out of scope for v0.1)

- Email verification
- Password reset flow
- Admin moderation dashboard
- Real-time topic ingestion / AI generation
- Civic Units create/join functionality
- OAuth / social login
- Direct messaging or comments

## Known Limitations

- No database migration tool — schema changes require manual SQL or drop/recreate
- `/admin/seed` is gated by FLASK_ENV only — add IP or token auth before any public deploy
- `%-d` in strftime (day without leading zero) works on Linux/macOS but not Windows — replace with `%d` if developing on Windows

## Next Steps (suggested v0.2)

1. Add `gunicorn` to requirements.txt and deploy to Render
2. Add Flask-Migrate for schema migrations
3. Build topic ingestion pipeline (AI summarization from RSS/news sources)
4. Add email verification on registration
5. Implement Civic Units create/join

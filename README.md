# Pulse

Pulse is a civic topic discovery web application. It surfaces AI-curated civic and political topics filtered to each user's interests, with light reaction tools and a calm, editorial design. No free-form posting, no comments, no algorithmic outrage.

**Production target:** https://pulse.core3.com  
**Stack:** Python · Flask · PostgreSQL · HTML/CSS

---

## Local Development Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd pulse

# 2. Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env file
cp .env.example .env
# Edit .env with your local PostgreSQL credentials and a secret key

# 5. Create the PostgreSQL database
createdb pulse

# 6. Run the app (tables are created automatically on first run)
python app.py

# 7. Seed interests and sample topics (development only)
# Visit: http://localhost:5000/admin/seed
```

The app will be running at **http://localhost:5000**.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Flask session secret — use a long random string in production |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `FLASK_ENV` | No | `development` or `production` (default: `development`) |

---

## Database

Tables are created automatically via `db.create_all()` on startup. No migration tool is required for the MVP.

To seed the database with interests and sample topics:
```
GET /admin/seed
```
This route is only available when `FLASK_ENV=development`.

---

## Deployment (Render)

1. Push the repo to GitHub
2. Create a new **Web Service** on [Render](https://render.com)
3. Connect the GitHub repo
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `gunicorn app:app`
6. Add environment variables: `SECRET_KEY`, `DATABASE_URL`, `FLASK_ENV=production`
7. Add a **PostgreSQL** database on Render and copy the connection string to `DATABASE_URL`

Add `gunicorn` to `requirements.txt` before deploying.

---

## Folder Structure

```
pulse/
  app.py               # Application entry point
  config.py            # DevelopmentConfig / ProductionConfig
  utils.py             # CSRF helpers, login_required decorator
  requirements.txt
  .env.example
  models/              # SQLAlchemy models
    user.py            # User, Interest, user_interests table
    topic.py           # Topic, TopicSource
    reaction.py        # TopicReaction
    civic_unit.py      # CivicUnit (placeholder)
  routes/              # Flask blueprints
    auth.py            # /, /register, /login, /logout
    topics.py          # /feed, /topic/<id>, /topic/<id>/react
    profile.py         # /profile, /profile/edit, /interests
    civic_units.py     # /civic-units
  services/
    topic_service.py   # Seed data helpers
  templates/           # Jinja2 HTML templates
  static/
    css/main.css
    js/main.js
```

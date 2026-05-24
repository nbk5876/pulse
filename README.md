# Pulse

A civic news discovery and community discussion app for staying informed on the issues that matter.

**Live app:** https://pulse.core3.com

![Pulse Architecture](static/img/pulse-splash.png)

---

## What It Does

Pulse automatically collects civic and political news from trusted RSS sources, uses GPT-4o-mini to filter out sports/entertainment noise and assign categories, then delivers a personalized feed based on each user's selected interests. Users can react, comment, get AI summaries, and discuss in a shared community Thread.

## Architecture

```
RSS Feeds (AP, NPR, PBS, Politico, The Hill, ABC, CBS, Axios...)
        │
        ▼
  GPT-4o-mini  ←── single batch call per run
  (filters noise, assigns civic category)
        │
        ▼
   PostgreSQL  (topics, reactions, comments, thread posts)
        │
        ▼
   Flask Web App ──► Users
```

News is fetched every 12 hours via a Render cron job. Each run makes one request per RSS feed and one GPT batch call — no per-article API costs.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Flask (Python) |
| Database | PostgreSQL via SQLAlchemy |
| AI filtering & summaries | OpenAI gpt-4o-mini |
| News sources | 10 free RSS feeds (no API key required) |
| Image uploads | Cloudinary |
| Hosting | Render (web service + cron job + PostgreSQL) |

## Features

- **Personalized feed** — users select interests; feed shows matching topics only
- **AI Summary** — one-click GPT summary for any topic (browser-only, not stored)
- **Hide topics** — per-user ✕ removes a topic from their feed permanently
- **Reactions & comments** — engage directly on topic detail pages
- **Pulse Thread** — shared community board with text, links, and photo uploads
- **Auto-polling** — Thread updates live every 12 seconds without page reload
- **500-post retention** — oldest Thread posts drop automatically when full
- **Category filter** — filter feed by Economy, Climate, Healthcare, Housing, and more

## Local Development

```bash
# 1. Clone and install
git clone https://github.com/nbk5876/pulse.git
cd pulse
pip install -r requirements.txt

# 2. Create .env
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://postgres:password@localhost:5432/pulse
FLASK_ENV=development
SEED_SECRET=your-admin-secret
OPENAI_API_KEY=your-openai-key
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# 3. Create database and run
createdb pulse
python app.py
```

Visit `http://localhost:5000` and seed the database at `/admin/seed?secret=<SEED_SECRET>`.

## Deployment (Render)

1. Create a **PostgreSQL** database on Render
2. Create a **Web Service** connected to this repo
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
3. Create a **Cron Job** on a 12-hour schedule (`0 */12 * * *`):
   ```
   python -c "from app import app; from services.news_service import fetch_and_store_news; app.app_context().push(); fetch_and_store_news()"
   ```
4. Set environment variables on both the web service and cron job (see below)

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Flask session signing |
| `DATABASE_URL` | PostgreSQL connection string |
| `SEED_SECRET` | Protects admin endpoints |
| `OPENAI_API_KEY` | GPT news filtering + AI summaries |
| `CLOUDINARY_CLOUD_NAME` | Thread photo uploads |
| `CLOUDINARY_API_KEY` | Thread photo uploads |
| `CLOUDINARY_API_SECRET` | Thread photo uploads |

## Admin Endpoints

All require `?secret=<SEED_SECRET>`:

| URL | Purpose |
|-----|---------|
| `/admin/seed` | Seed interests and sample topics |
| `/admin/fetch-news` | Manually trigger a news fetch |
| `/admin/topics` | Review and delete topics |

## Folder Structure

```
pulse/
  app.py                  # App factory, admin routes
  config.py               # Dev/prod config
  utils.py                # CSRF, login_required, linkify
  requirements.txt
  models/
    user.py               # User, Interest, user_interests
    topic.py              # Topic, TopicSource, UserHiddenTopic
    reaction.py           # TopicReaction
    comment.py            # Comment
    thread.py             # ThreadPost
  routes/
    auth.py               # Register, login, logout
    topics.py             # Feed, topic detail, react, comment, hide, summarize
    profile.py            # Profile, edit profile, interests
    thread.py             # Pulse Thread, poll, image upload
  services/
    news_service.py       # RSS fetch + GPT classification pipeline
  templates/
  static/
    css/main.css
    js/main.js
    img/
```

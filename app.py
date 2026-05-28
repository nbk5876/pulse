import os
from flask import Flask, redirect, url_for, jsonify, session
from dotenv import load_dotenv
from models import db
from config import config
from utils import generate_csrf_token, linkify, format_summary

load_dotenv()


ADMIN_TOPICS_HTML = """
<!doctype html>
<html>
<head>
  <title>Admin: Topics</title>
  <style>
    body { font-family: sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }
    h1 { font-size: 1.4rem; margin-bottom: 20px; }
    table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    th { text-align: left; border-bottom: 2px solid #ccc; padding: 6px 8px; }
    td { border-bottom: 1px solid #eee; padding: 6px 8px; vertical-align: top; }
    .cat { font-size: 0.75rem; color: #666; }
    .del { background: #c0392b; color: white; border: none; padding: 4px 10px; cursor: pointer; border-radius: 3px; }
    .del:hover { background: #a93226; }
  </style>
</head>
<body>
  <h1>Topics ({{ topics|length }})</h1>
  {% if msg %}<div style="background:#d1fae5;border:1px solid #6ee7b7;color:#065f46;padding:8px 14px;border-radius:5px;margin-bottom:14px;font-size:0.9rem;">{{ msg }}</div>{% endif %}
  {% if err %}<div style="background:#fee2e2;border:1px solid #fca5a5;color:#991b1b;padding:8px 14px;border-radius:5px;margin-bottom:14px;font-size:0.9rem;">{{ err }}</div>{% endif %}
  <form method="GET" action="/admin/fetch-topic" style="display:flex;gap:8px;margin-bottom:12px;">
    <input type="hidden" name="secret" value="{{ secret }}">
    <input type="text" name="q" placeholder="Search topic — e.g. Pope AI encyclical"
           style="flex:1;padding:7px 10px;border:1px solid #ccc;border-radius:4px;font-size:0.9rem;">
    <button type="submit" style="background:#2563eb;color:white;border:none;padding:7px 16px;border-radius:4px;cursor:pointer;font-size:0.9rem;">Fetch Topic</button>
  </form>
  <form method="POST" action="/admin/submit-url" style="display:flex;gap:8px;margin-bottom:20px;">
    <input type="hidden" name="secret" value="{{ secret }}">
    <input type="url" name="url" placeholder="Paste article URL to add directly…"
           style="flex:1;padding:7px 10px;border:1px solid #ccc;border-radius:4px;font-size:0.9rem;" required>
    <button type="submit" style="background:#16a34a;color:white;border:none;padding:7px 16px;border-radius:4px;cursor:pointer;font-size:0.9rem;">Add Article</button>
  </form>
  <table>
    <tr><th>#</th><th>Category</th><th>Title</th><th>Date</th><th></th></tr>
    {% for t in topics %}
    <tr>
      <td><a href="/topic/{{ t.id }}" target="_blank" style="color:#2563eb;">{{ t.id }}</a></td>
      <td class="cat">
        <form method="POST" action="/admin/topics/{{ t.id }}/category?secret={{ secret }}" style="margin:0">
          <select name="category" onchange="this.form.submit()" style="font-size:0.75rem;border:1px solid #ccc;border-radius:3px;padding:2px 4px;color:#666;">
            {% for cat in ['Economy','Immigration','Climate','Healthcare','Housing','Foreign Policy','Education','Technology','Local Government','National Politics'] %}
              <option value="{{ cat }}" {% if cat == t.category %}selected{% endif %}>{{ cat }}</option>
            {% endfor %}
          </select>
        </form>
      </td>
      <td>{{ t.title }}</td>
      <td>{{ t.created_at.strftime('%m/%d') }}</td>
      <td>
        <form method="POST" action="/admin/topics/{{ t.id }}/delete?secret={{ secret }}">
          <button class="del" type="submit">Delete</button>
        </form>
      </td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>
"""


def create_app():
    app = Flask(__name__)
    env = os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config.get(env, config['default']))

    db.init_app(app)

    # Make CSRF token available in all templates
    app.jinja_env.globals['csrf_token'] = generate_csrf_token
    app.jinja_env.filters['linkify'] = linkify
    app.jinja_env.filters['format_summary'] = format_summary

    @app.context_processor
    def inject_current_user():
        from models.user import User
        user_id = session.get('user_id')
        current_user = User.query.get(user_id) if user_id else None
        return {'current_user': current_user}

    # Register blueprints
    from routes.auth import auth_bp
    from routes.topics import topics_bp
    from routes.profile import profile_bp
    from routes.civic_units import civic_units_bp
    from routes.thread import thread_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(topics_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(civic_units_bp)
    app.register_blueprint(thread_bp)

    # Admin topics page — list and delete topics
    @app.route('/admin/topics')
    def admin_topics():
        from flask import request as flask_req, render_template_string
        seed_secret = os.environ.get('SEED_SECRET')
        if not seed_secret or flask_req.args.get('secret') != seed_secret:
            return 'Not available.', 403
        from models.topic import Topic
        topics = Topic.query.order_by(Topic.created_at.desc()).all()
        secret = flask_req.args.get('secret')
        msg = flask_req.args.get('msg', '')
        err = flask_req.args.get('err', '')
        return render_template_string(ADMIN_TOPICS_HTML, topics=topics, secret=secret, msg=msg, err=err)

    @app.route('/admin/topics/<int:topic_id>/delete', methods=['POST'])
    def admin_delete_topic(topic_id):
        from flask import request as flask_req
        seed_secret = os.environ.get('SEED_SECRET')
        if not seed_secret or flask_req.args.get('secret') != seed_secret:
            return 'Not available.', 403
        from models.topic import Topic, TopicSource, UserHiddenTopic
        from models.reaction import TopicReaction
        from models.comment import Comment
        Comment.query.filter_by(topic_id=topic_id).delete()
        TopicReaction.query.filter_by(topic_id=topic_id).delete()
        UserHiddenTopic.query.filter_by(topic_id=topic_id).delete()
        TopicSource.query.filter_by(topic_id=topic_id).delete()
        Topic.query.filter_by(id=topic_id).delete()
        db.session.commit()
        return redirect(f'/admin/topics?secret={flask_req.args.get("secret")}')

    @app.route('/admin/topics/<int:topic_id>/category', methods=['POST'])
    def admin_update_category(topic_id):
        from flask import request as flask_req
        seed_secret = os.environ.get('SEED_SECRET')
        if not seed_secret or flask_req.args.get('secret') != seed_secret:
            return 'Not available.', 403
        from models.topic import Topic
        topic = Topic.query.get_or_404(topic_id)
        new_cat = flask_req.form.get('category', '').strip()
        valid = ['Economy','Immigration','Climate','Healthcare','Housing',
                 'Foreign Policy','Education','Technology','Local Government','National Politics']
        if new_cat in valid:
            topic.category = new_cat
            db.session.commit()
        return redirect(f'/admin/topics?secret={flask_req.args.get("secret")}')

    @app.route('/admin/fetch-topic')
    def admin_fetch_topic():
        from flask import request as flask_req
        seed_secret = os.environ.get('SEED_SECRET')
        if not seed_secret or flask_req.args.get('secret') != seed_secret:
            return 'Not available.', 403
        query = flask_req.args.get('q', '').strip()
        if not query:
            return jsonify({'error': 'No query provided — add ?q=your+topic'}), 400
        try:
            from services.news_service import fetch_topic
            result = fetch_topic(query)
        except Exception as e:
            import traceback
            result = {'error': str(e), 'traceback': traceback.format_exc()}
        return jsonify(result)

    @app.route('/admin/submit-url', methods=['POST'])
    def admin_submit_url():
        from flask import request as flask_req
        import re, json
        import requests as req_lib
        from bs4 import BeautifulSoup
        import openai
        from urllib.parse import urlparse
        from models.topic import Topic, TopicSource

        seed_secret = os.environ.get('SEED_SECRET')
        secret = flask_req.form.get('secret', '')
        if not seed_secret or secret != seed_secret:
            return 'Not available.', 403

        url = flask_req.form.get('url', '').strip()
        if not url:
            return redirect(f'/admin/topics?secret={secret}&err=No+URL+provided')

        # Fetch the page
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; PulseBot/1.0)'}
            page = req_lib.get(url, headers=headers, timeout=12)
            page.raise_for_status()
        except Exception as e:
            return redirect(f'/admin/topics?secret={secret}&err=Could+not+fetch+URL:+{str(e)[:80]}')

        # Extract text
        soup = BeautifulSoup(page.text, 'html.parser')
        page_title = soup.title.string.strip() if soup.title else ''
        paragraphs = [p.get_text(' ', strip=True) for p in soup.find_all('p')
                      if len(p.get_text(strip=True)) > 50]
        body_text = ' '.join(paragraphs)[:4000] or soup.get_text(' ', strip=True)[:4000]

        # GPT
        valid_cats = ['Economy', 'Immigration', 'Climate', 'Healthcare', 'Housing',
                      'Foreign Policy', 'Education', 'Technology', 'Local Government', 'National Politics']
        client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        prompt = (
            f'You are processing a news article for a civic news app.\n\n'
            f'Page title: {page_title}\nURL: {url}\n'
            f'Article text: {body_text}\n\n'
            f'Return ONLY valid JSON with keys:\n'
            f'- "title": clear concise headline (max 120 chars)\n'
            f'- "summary": 2-3 sentence neutral summary\n'
            f'- "category": exactly one of: {", ".join(valid_cats)}\n'
            f'JSON only, no markdown.'
        )
        try:
            resp_gpt = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=500,
                temperature=0.3,
            )
            raw = resp_gpt.choices[0].message.content.strip()
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            data = json.loads(raw)
        except Exception as e:
            return redirect(f'/admin/topics?secret={secret}&err=GPT+error:+{str(e)[:80]}')

        title    = str(data.get('title', page_title))[:255]
        summary  = str(data.get('summary', ''))
        category = data.get('category', 'Technology')
        if category not in valid_cats:
            category = 'Technology'

        source_name = urlparse(url).netloc.replace('www.', '')
        topic = Topic(title=title, summary=summary, category=category)
        db.session.add(topic)
        db.session.flush()
        db.session.add(TopicSource(topic_id=topic.id, source_name=source_name, source_url=url))
        db.session.commit()

        return redirect(f'/admin/topics?secret={secret}&msg=Added:+{topic.id}+—+{title[:60]}')

    @app.route('/admin/cleanup-topics')
    def admin_cleanup_topics():
        from flask import request as flask_req
        from datetime import datetime, timezone, timedelta
        from models.topic import Topic, TopicSource, UserHiddenTopic
        from models.reaction import TopicReaction
        from models.comment import Comment

        seed_secret = os.environ.get('SEED_SECRET')
        if not seed_secret or flask_req.args.get('secret') != seed_secret:
            return 'Not available.', 403

        cutoff = datetime.now(timezone.utc) - timedelta(days=2)

        has_reaction = {r[0] for r in db.session.query(TopicReaction.topic_id).distinct()}
        has_comment  = {r[0] for r in db.session.query(Comment.topic_id).distinct()}
        engaged_ids  = has_reaction | has_comment

        old_topics = Topic.query.filter(Topic.created_at < cutoff).all()
        delete_ids = [t.id for t in old_topics if t.id not in engaged_ids]

        if not delete_ids:
            return jsonify({'deleted': 0, 'message': 'Nothing to clean up.'})

        Comment.query.filter(Comment.topic_id.in_(delete_ids)).delete(synchronize_session=False)
        TopicReaction.query.filter(TopicReaction.topic_id.in_(delete_ids)).delete(synchronize_session=False)
        UserHiddenTopic.query.filter(UserHiddenTopic.topic_id.in_(delete_ids)).delete(synchronize_session=False)
        TopicSource.query.filter(TopicSource.topic_id.in_(delete_ids)).delete(synchronize_session=False)
        Topic.query.filter(Topic.id.in_(delete_ids)).delete(synchronize_session=False)
        db.session.commit()

        from models.user import User
        from models.thread import ThreadPost
        bot = User.query.filter_by(username='Pulse Bot').first()
        if bot:
            total = Topic.query.count()
            db.session.add(ThreadPost(
                user_id=bot.id,
                body=f'🧹 Topic cleanup · removed {len(delete_ids)} old unengaged topics · {total} remaining'
            ))
            db.session.commit()

        return jsonify({'deleted': len(delete_ids), 'message': f'Removed {len(delete_ids)} old unengaged topics.'})

    # Fetch news route — requires SEED_SECRET param
    @app.route('/admin/fetch-news')
    def admin_fetch_news():
        from flask import request as flask_req
        seed_secret = os.environ.get('SEED_SECRET')
        if not seed_secret or flask_req.args.get('secret') != seed_secret:
            return 'Not available.', 403
        try:
            from services.news_service import fetch_and_store_news
            result = fetch_and_store_news()
        except Exception as e:
            import traceback
            result = {'error': str(e), 'traceback': traceback.format_exc()}
        return jsonify(result)

    @app.route('/admin/create-bot-user')
    def admin_create_bot_user():
        from flask import request as flask_req
        from werkzeug.security import generate_password_hash
        from models.user import User
        seed_secret = os.environ.get('SEED_SECRET')
        if not seed_secret or flask_req.args.get('secret') != seed_secret:
            return 'Not available.', 403
        existing = User.query.filter_by(username='Pulse Bot').first()
        if existing:
            return jsonify({'ok': True, 'message': f'Pulse Bot already exists (id={existing.id})'})
        bot = User(
            username='Pulse Bot',
            email='pulsebot@pulse.internal',
            password_hash=generate_password_hash(os.urandom(32).hex()),
        )
        db.session.add(bot)
        db.session.commit()
        return jsonify({'ok': True, 'message': f'Pulse Bot created (id={bot.id})'})

    # Seed route — requires SEED_SECRET param
    @app.route('/admin/seed')
    def admin_seed():
        from flask import request as flask_req
        seed_secret = os.environ.get('SEED_SECRET')
        if not seed_secret or flask_req.args.get('secret') != seed_secret:
            return 'Not available.', 403
        from services.topic_service import seed_interests, seed_topics
        seed_interests()
        seed_topics()
        return jsonify({'status': 'ok', 'message': 'Interests and sample topics seeded.'})

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)

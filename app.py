import os
from flask import Flask, redirect, url_for, jsonify, session
from dotenv import load_dotenv
from models import db
from config import config
from utils import generate_csrf_token, linkify

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
        return render_template_string(ADMIN_TOPICS_HTML, topics=topics, secret=secret)

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
